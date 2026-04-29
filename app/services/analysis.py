from __future__ import annotations

"""
康复分析服务 — 对回访结果进行统计和分析。
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.callback import Assessment, CallbackRecord


@dataclass
class PatientRecoverySummary:
    """患者康复汇总"""
    patient_id: int
    patient_name: str
    total_callbacks: int = 0
    last_callback_date: Optional[datetime] = None
    latest_recovery_level: Optional[str] = None
    avg_scores: dict[str, float] = field(default_factory=dict)
    needs_attention: bool = False


@dataclass
class StatsOverview:
    """系统统计概览"""
    total_patients: int = 0
    total_callbacks: int = 0
    today_pending: int = 0
    week_completed: int = 0
    urgent_cases: int = 0
    recovery_distribution: dict[str, int] = field(default_factory=dict)


class AnalysisService:
    """回访数据分析服务"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_recovery_summary(self, patient_id: int) -> PatientRecoverySummary:
        """获取单个患者的康复汇总"""
        from app.models.patient import Patient

        patient = await self.db.get(Patient, patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")

        # 查询最近回访记录
        stmt = (
            select(CallbackRecord)
            .where(CallbackRecord.patient_id == patient_id)
            .where(CallbackRecord.status == "completed")
            .order_by(CallbackRecord.called_at.desc())
        )
        result = await self.db.execute(stmt)
        records = list(result.scalars().all())

        if not records:
            return PatientRecoverySummary(
                patient_id=patient_id,
                patient_name=patient.name,
                total_callbacks=0,
            )

        latest = records[0]

        # 统计各维度平均分
        assessments_stmt = (
            select(
                Assessment.dimension,
                func.avg(Assessment.score).label("avg_score"),
            )
            .where(Assessment.callback_id.in_([r.id for r in records]))
            .group_by(Assessment.dimension)
        )
        result = await self.db.execute(assessments_stmt)
        avg_scores = {row.dimension: round(float(row.avg_score), 1) for row in result}

        return PatientRecoverySummary(
            patient_id=patient_id,
            patient_name=patient.name,
            total_callbacks=len(records),
            last_callback_date=latest.called_at,
            latest_recovery_level=latest.recovery_level,
            avg_scores=avg_scores,
            needs_attention=latest.needs_urgent_care,
        )

    async def get_stats_overview(self) -> StatsOverview:
        """获取系统运行概览统计"""
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)

        # 待处理数量
        pending_count = await self.db.scalar(
            select(func.count(CallbackRecord.id))
            .where(CallbackRecord.status == "pending")
        )

        # 本周完成量
        week_completed = await self.db.scalar(
            select(func.count(CallbackRecord.id))
            .where(CallbackRecord.status == "completed")
            .where(CallbackRecord.called_at >= week_start)
        )

        # 紧急病例
        urgent_count = await self.db.scalar(
            select(func.count(CallbackRecord.id))
            .where(CallbackRecord.needs_urgent_care == True)
        )

        # 康复等级分布
        dist_stmt = (
            select(CallbackRecord.recovery_level, func.count(CallbackRecord.id))
            .where(CallbackRecord.status == "completed")
            .where(CallbackRecord.recovery_level.isnot(None))
            .group_by(CallbackRecord.recovery_level)
        )
        result = await self.db.execute(dist_stmt)
        distribution = {row.recovery_level: row[1] for row in result}

        # 患者总数
        from app.models.patient import Patient

        total_patients = await self.db.scalar(select(func.count(Patient.id)))

        return StatsOverview(
            total_patients=total_patients or 0,
            today_pending=pending_count or 0,
            week_completed=week_completed or 0,
            urgent_cases=urgent_count or 0,
            recovery_distribution=distribution,
        )
