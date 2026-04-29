from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.patient import Base


class CallbackRecord(Base):
    """回访记录"""

    __tablename__ = "callback_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("patients.id"), nullable=False, index=True
    )
    agent_id: Mapped[Optional[str]] = mapped_column(
        String(64), comment="Agent 实例标识"
    )
    # 通话状态: pending / in_progress / completed / failed / no_answer
    status: Mapped[str] = mapped_column(
        String(20), default="pending", comment="状态"
    )
    # 回访类型: post_surgery / post_discharge / chronic_followup / checkup_reminder
    callback_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="回访类型"
    )
    priority: Mapped[int] = mapped_column(
        Integer, default=0, comment="优先级 0-100, 越高越紧急"
    )
    # 通话相关
    call_duration: Mapped[Optional[int]] = mapped_column(
        Integer, comment="通话时长(秒)"
    )
    conversation_log: Mapped[Optional[str]] = mapped_column(
        Text, comment="对话日志(JSON格式)"
    )
    # 结果
    result_summary: Mapped[Optional[str]] = mapped_column(
        Text, comment="回访结果摘要"
    )
    recovery_level: Mapped[Optional[str]] = mapped_column(
        String(16), comment="康复等级: excellent/good/fair/poor/critical"
    )
    followup_actions: Mapped[Optional[str]] = mapped_column(
        Text, comment="建议后续行动"
    )
    # 异常标记
    needs_urgent_care: Mapped[bool] = mapped_column(
        default=False, comment="是否需要紧急处理"
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, comment="错误信息")
    # 时间
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), comment="计划回访时间"
    )
    called_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), comment="实际通话时间"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    patient: Mapped["Patient"] = relationship(back_populates="callbacks")  # type: ignore[name-defined]
    assessments: Mapped[list[Assessment]] = relationship(
        back_populates="callback", cascade="all, delete-orphan"
    )


class Assessment(Base):
    """回访评估详情"""

    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    callback_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("callback_records.id"), nullable=False, index=True
    )
    dimension: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="评估维度: pain/fever/mobility/mood/medication/appetite/sleep"
    )
    score: Mapped[Optional[float]] = mapped_column(
        Float, comment="评分 (0-10)"
    )
    description: Mapped[Optional[str]] = mapped_column(Text, comment="描述")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    callback: Mapped[CallbackRecord] = relationship(back_populates="assessments")


class ScheduleTask(Base):
    """排期任务"""

    __tablename__ = "schedule_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("patients.id"), nullable=False, index=True
    )
    callback_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="回访类型"
    )
    priority: Mapped[int] = mapped_column(Integer, default=0, comment="优先级")
    status: Mapped[str] = mapped_column(
        String(20), default="pending", comment="pending/completed/cancelled"
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), comment="计划执行时间"
    )
    callback_record_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("callback_records.id"), comment="关联的回访记录"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
