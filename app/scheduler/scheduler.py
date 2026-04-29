from __future__ import annotations

"""
回访调度器 — 负责任务的创建、排队和分发。
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.callback import CallbackRecord, ScheduleTask
from app.models.patient import Patient, TreatmentEvent
from app.scheduler.strategies import (
    STRATEGY_MAP,
    CallbackType,
    ScheduleStrategy,
    get_strategy,
)

logger = logging.getLogger(__name__)


class CallbackScheduler:
    """回访调度器"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_callback_task(
        self,
        patient_id: int,
        callback_type: CallbackType,
        event_date: Optional[datetime] = None,
        doctor_notes: Optional[str] = None,
    ) -> Optional[CallbackRecord]:
        """
        为患者创建回访任务。

        参数:
            patient_id: 患者ID
            callback_type: 回访类型
            event_date: 触发事件的日期（默认为现在）
            doctor_notes: 医生备注

        返回:
            创建的 CallbackRecord 或 None
        """
        patient = await self.db.get(Patient, patient_id)
        if not patient:
            logger.error(f"Patient {patient_id} not found")
            return None

        strategy = get_strategy(callback_type)
        if not strategy:
            logger.error(f"No strategy for {callback_type}")
            return None

        event_date = event_date or datetime.now(timezone.utc)

        # 创建回访记录
        record = CallbackRecord(
            patient_id=patient_id,
            callback_type=callback_type.value,
            priority=strategy.priority,
            status="pending",
            scheduled_at=event_date,
        )
        self.db.add(record)
        await self.db.flush()

        # 创建排期任务
        task = ScheduleTask(
            patient_id=patient_id,
            callback_type=callback_type.value,
            priority=strategy.priority,
            status="pending",
            scheduled_at=event_date,
            callback_record_id=record.id,
        )
        self.db.add(task)
        await self.db.flush()

        logger.info(
            f"Created callback task: patient={patient_id}, "
            f"type={callback_type.value}, record_id={record.id}"
        )
        return record

    async def create_post_surgery_callbacks(
        self, treatment_event_id: int
    ) -> list[CallbackRecord]:
        """
        根据治疗事件（手术）创建术后回访任务。
        会根据策略中的 delay_days 多次排期。
        """
        event = await self.db.get(TreatmentEvent, treatment_event_id)
        if not event:
            return []

        strategy = get_strategy(CallbackType.POST_SURGERY)
        if not strategy:
            return []

        records = []
        for schedule_time in strategy.calculate_schedule_times(event.event_date):
            record = CallbackRecord(
                patient_id=event.patient_id,
                callback_type=CallbackType.POST_SURGERY.value,
                priority=strategy.priority,
                status="pending",
                scheduled_at=schedule_time,
            )
            self.db.add(record)
            await self.db.flush()

            task = ScheduleTask(
                patient_id=event.patient_id,
                callback_type=CallbackType.POST_SURGERY.value,
                priority=strategy.priority,
                status="pending",
                scheduled_at=schedule_time,
                callback_record_id=record.id,
            )
            self.db.add(task)
            records.append(record)

        await self.db.flush()
        return records

    async def get_pending_tasks(
        self, limit: int = 10, max_priority: Optional[int] = None
    ) -> list[ScheduleTask]:
        """获取待执行的排期任务"""
        now = datetime.now(timezone.utc)
        stmt = (
            select(ScheduleTask)
            .where(ScheduleTask.status == "pending")
            .where(ScheduleTask.scheduled_at <= now)
            .order_by(ScheduleTask.priority.desc(), ScheduleTask.scheduled_at.asc())
            .limit(limit)
        )
        if max_priority is not None:
            stmt = stmt.where(ScheduleTask.priority <= max_priority)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def mark_task_done(self, task_id: int, callback_record_id: int) -> None:
        """标记任务已完成"""
        task = await self.db.get(ScheduleTask, task_id)
        if task:
            task.status = "completed"
            task.callback_record_id = callback_record_id
            await self.db.flush()

    async def cancel_task(self, task_id: int) -> bool:
        """取消任务"""
        task = await self.db.get(ScheduleTask, task_id)
        if task and task.status == "pending":
            task.status = "cancelled"
            await self.db.flush()
            return True
        return False

    async def get_due_callbacks(
        self, limit: int = 10
    ) -> list[CallbackRecord]:
        """获取到期待处理的回访记录"""
        now = datetime.now(timezone.utc)
        stmt = (
            select(CallbackRecord)
            .where(CallbackRecord.status == "pending")
            .where(CallbackRecord.scheduled_at <= now)
            .order_by(CallbackRecord.priority.desc(), CallbackRecord.scheduled_at.asc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
