from __future__ import annotations

"""
REST API 路由
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import CallbackOrchestrator
from app.core.database import get_db
from app.models.callback import CallbackRecord
from app.models.patient import Patient, TreatmentEvent
from app.scheduler.scheduler import CallbackScheduler
from app.scheduler.strategies import CallbackType
from app.services.analysis import AnalysisService

router = APIRouter(prefix="/api/v1")


# ─── 患者管理 ──────────────────────────────────────────────

@router.get("/patients")
async def list_patients(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Patient).order_by(Patient.id))
    patients = result.scalars().all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "phone": p.phone,
            "gender": p.gender,
            "age": p.age,
            "primary_diagnosis": p.primary_diagnosis,
        }
        for p in patients
    ]


@router.get("/patients/{patient_id}")
async def get_patient(patient_id: int, db: AsyncSession = Depends(get_db)):
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(404, "患者不存在")
    return {
        "id": patient.id,
        "name": patient.name,
        "phone": patient.phone,
        "gender": patient.gender,
        "age": patient.age,
        "primary_diagnosis": patient.primary_diagnosis,
        "allergies": patient.allergies,
        "address": patient.address,
    }


# ─── 治疗事件 ──────────────────────────────────────────────

@router.get("/patients/{patient_id}/treatments")
async def list_treatments(patient_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TreatmentEvent)
        .where(TreatmentEvent.patient_id == patient_id)
        .order_by(TreatmentEvent.event_date.desc())
    )
    events = result.scalars().all()
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "event_name": e.event_name,
            "event_date": e.event_date.isoformat(),
            "doctor": e.doctor,
            "follow_up_days": e.follow_up_days,
        }
        for e in events
    ]


# ─── 回访管理 ──────────────────────────────────────────────

@router.post("/callbacks")
async def create_callback(
    patient_id: int,
    callback_type: str = "post_surgery",
    event_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """手动创建回访任务"""
    scheduler = CallbackScheduler(db)
    try:
        cb_type = CallbackType(callback_type)
    except ValueError:
        raise HTTPException(400, f"无效的回访类型: {callback_type}")
    record = await scheduler.create_callback_task(patient_id, cb_type)
    if not record:
        raise HTTPException(400, "创建回访任务失败")
    return {"id": record.id, "status": record.status, "scheduled_at": str(record.scheduled_at)}


@router.get("/callbacks")
async def list_callbacks(
    status: Optional[str] = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CallbackRecord).order_by(CallbackRecord.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(CallbackRecord.status == status)
    result = await db.execute(stmt)
    records = result.scalars().all()
    return [
        {
            "id": r.id,
            "patient_id": r.patient_id,
            "callback_type": r.callback_type,
            "status": r.status,
            "priority": r.priority,
            "recovery_level": r.recovery_level,
            "needs_urgent_care": r.needs_urgent_care,
            "scheduled_at": str(r.scheduled_at) if r.scheduled_at else None,
            "called_at": str(r.called_at) if r.called_at else None,
        }
        for r in records
    ]


@router.post("/callbacks/{callback_id}/execute")
async def execute_callback(
    callback_id: int,
    simulate: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """执行一次回访通话"""
    callback = await db.get(CallbackRecord, callback_id)
    if not callback:
        raise HTTPException(404, "回访记录不存在")

    orchestrator = CallbackOrchestrator(db)
    try:
        result = await orchestrator.run_call(
            callback_id=callback_id,
            patient_id=callback.patient_id,
            simulate=simulate,
        )
        return result
    except Exception as e:
        callback.status = "failed"
        callback.error_message = str(e)
        await db.flush()
        raise HTTPException(500, f"回访执行失败: {e}")


# ─── 分析统计 ──────────────────────────────────────────────

@router.get("/stats/overview")
async def get_stats_overview(db: AsyncSession = Depends(get_db)):
    service = AnalysisService(db)
    stats = await service.get_stats_overview()
    return {
        "total_patients": stats.total_patients,
        "today_pending": stats.today_pending,
        "week_completed": stats.week_completed,
        "urgent_cases": stats.urgent_cases,
        "recovery_distribution": stats.recovery_distribution,
    }


@router.get("/patients/{patient_id}/recovery")
async def get_patient_recovery(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
):
    service = AnalysisService(db)
    try:
        summary = await service.get_recovery_summary(patient_id)
        return {
            "patient_id": summary.patient_id,
            "patient_name": summary.patient_name,
            "total_callbacks": summary.total_callbacks,
            "last_callback_date": str(summary.last_callback_date) if summary.last_callback_date else None,
            "latest_recovery_level": summary.latest_recovery_level,
            "avg_scores": summary.avg_scores,
            "needs_attention": summary.needs_attention,
        }
    except ValueError as e:
        raise HTTPException(404, str(e))


# ─── 调度管理 ──────────────────────────────────────────────

@router.post("/scheduler/process")
async def process_due_tasks(limit: int = 5, db: AsyncSession = Depends(get_db)):
    """处理到期的排期任务"""
    scheduler = CallbackScheduler(db)
    tasks = await scheduler.get_due_callbacks(limit=limit)
    return {
        "processed": len(tasks),
        "tasks": [
            {
                "id": t.id,
                "patient_id": t.patient_id,
                "callback_type": t.callback_type,
                "priority": t.priority,
            }
            for t in tasks
        ],
    }
