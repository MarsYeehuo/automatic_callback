from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="患者姓名")
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True, comment="联系电话")
    gender: Mapped[Optional[str]] = mapped_column(String(8), comment="性别")
    age: Mapped[Optional[int]] = mapped_column(Integer, comment="年龄")
    id_card: Mapped[Optional[str]] = mapped_column(String(32), unique=True, comment="身份证号")
    address: Mapped[Optional[str]] = mapped_column(String(256), comment="住址")
    primary_diagnosis: Mapped[Optional[str]] = mapped_column(Text, comment="主要诊断")
    allergies: Mapped[Optional[str]] = mapped_column(Text, comment="过敏史")
    notes: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    medical_records: Mapped[list[MedicalRecord]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    treatment_events: Mapped[list[TreatmentEvent]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    callbacks: Mapped[list[CallbackRecord]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )


class MedicalRecord(Base):
    """病历记录"""

    __tablename__ = "medical_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("patients.id"), nullable=False, index=True
    )
    diagnosis: Mapped[str] = mapped_column(Text, nullable=False, comment="诊断内容")
    doctor: Mapped[str] = mapped_column(String(64), comment="主治医生")
    department: Mapped[Optional[str]] = mapped_column(String(64), comment="科室")
    record_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), comment="记录日期")
    details: Mapped[Optional[str]] = mapped_column(Text, comment="详细病历")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    patient: Mapped[Patient] = relationship(back_populates="medical_records")


class TreatmentEvent(Base):
    """治疗事件（手术、用药、治疗等）"""

    __tablename__ = "treatment_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("patients.id"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="事件类型: surgery/medication/therapy/exam"
    )
    event_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="事件名称")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="描述")
    doctor: Mapped[Optional[str]] = mapped_column(String(64), comment="执行医生")
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), comment="事件日期")
    follow_up_days: Mapped[Optional[int]] = mapped_column(
        Integer, comment="建议回访天数(术后/治疗后)"
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    patient: Mapped[Patient] = relationship(back_populates="treatment_events")
