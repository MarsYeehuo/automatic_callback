from __future__ import annotations

"""
Agent Tools — 供 Claude API function calling 使用的工具集。
每个工具对应一个可以被 LLM 调用的函数。
"""

from typing import Any

from anthropic.types import ToolParam

# ─── Tool 定义（返回给 Anthropic API 的 schema） ─────────────

TOOLS: list[ToolParam] = [
    {
        "name": "get_patient_info",
        "description": "获取患者的基本信息，如姓名、年龄、联系方式等",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "integer", "description": "患者ID"}
            },
            "required": ["patient_id"],
        },
    },
    {
        "name": "get_patient_medical_records",
        "description": "获取患者的病历记录",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "integer", "description": "患者ID"},
                "limit": {
                    "type": "integer",
                    "description": "返回记录数量上限",
                    "default": 5,
                },
            },
            "required": ["patient_id"],
        },
    },
    {
        "name": "get_patient_treatments",
        "description": "获取患者的近期治疗事件（手术、用药、治疗等）",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "integer", "description": "患者ID"},
                "limit": {
                    "type": "integer",
                    "description": "返回记录数量上限",
                    "default": 10,
                },
            },
            "required": ["patient_id"],
        },
    },
    {
        "name": "assess_symptom",
        "description": "记录患者的某个症状评估（在通话过程中调用）",
        "input_schema": {
            "type": "object",
            "properties": {
                "callback_id": {"type": "integer", "description": "回访记录ID"},
                "dimension": {
                    "type": "string",
                    "description": "评估维度: pain/fever/mobility/mood/medication/appetite/sleep/other",
                },
                "score": {
                    "type": "number",
                    "description": "评分 0-10, 0=无症状/很好, 10=极严重/极差",
                },
                "description": {
                    "type": "string",
                    "description": "患者描述的具体情况",
                },
            },
            "required": ["callback_id", "dimension", "score", "description"],
        },
    },
    {
        "name": "flag_urgent_care",
        "description": "标记患者需要紧急医疗处理。当患者报告严重症状（如胸痛、严重呼吸困难、大出血、意识模糊等）时调用此工具",
        "input_schema": {
            "type": "object",
            "properties": {
                "callback_id": {"type": "integer", "description": "回访记录ID"},
                "reason": {"type": "string", "description": "紧急原因详细说明"},
            },
            "required": ["callback_id", "reason"],
        },
    },
    {
        "name": "finalize_callback",
        "description": "通话结束时，记录回访的最终结果",
        "input_schema": {
            "type": "object",
            "properties": {
                "callback_id": {"type": "integer", "description": "回访记录ID"},
                "recovery_level": {
                    "type": "string",
                    "description": "康复等级: excellent/good/fair/poor/critical",
                    "enum": ["excellent", "good", "fair", "poor", "critical"],
                },
                "result_summary": {
                    "type": "string",
                    "description": "回访结果摘要（100字以内）",
                },
                "followup_actions": {
                    "type": "string",
                    "description": "建议后续行动",
                },
                "conversation_log": {
                    "type": "string",
                    "description": "完整的对话记录",
                },
                "call_duration": {
                    "type": "integer",
                    "description": "通话时长（秒）",
                },
            },
            "required": ["callback_id", "recovery_level", "result_summary"],
        },
    },
]


# ─── Tool Handler 接口 ──────────────────────────────────────

class ToolHandler:
    """工具处理器：执行 LLM 请求的工具调用，与数据库交互。"""

    def __init__(self, db_session):
        self.db = db_session

    async def execute(self, tool_name: str, params: dict[str, Any]) -> str:
        handler = getattr(self, tool_name, None)
        if handler is None:
            return f"错误：未知工具 {tool_name}"
        return await handler(**params)

    async def get_patient_info(self, patient_id: int) -> str:
        from app.models.patient import Patient

        patient = await self.db.get(Patient, patient_id)
        if not patient:
            return f"未找到患者 (ID={patient_id})"
        return (
            f"患者ID: {patient.id}\n"
            f"姓名: {patient.name}\n"
            f"性别: {patient.gender or '未知'}\n"
            f"年龄: {patient.age or '未知'}\n"
            f"电话: {patient.phone}\n"
            f"主要诊断: {patient.primary_diagnosis or '未知'}\n"
            f"过敏史: {patient.allergies or '无记录'}\n"
            f"地址: {patient.address or '未知'}"
        )

    async def get_patient_medical_records(self, patient_id: int, limit: int = 5) -> str:
        from sqlalchemy import select

        from app.models.patient import MedicalRecord

        stmt = (
            select(MedicalRecord)
            .where(MedicalRecord.patient_id == patient_id)
            .order_by(MedicalRecord.record_date.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        records = result.scalars().all()
        if not records:
            return "该患者暂无病历记录"
        lines = ["--- 病历记录 ---"]
        for r in records:
            lines.append(
                f"[{r.record_date.strftime('%Y-%m-%d')}] {r.diagnosis} | "
                f"医生: {r.doctor or '未知'} | "
                f"科室: {r.department or '未知'}"
            )
        return "\n".join(lines)

    async def get_patient_treatments(self, patient_id: int, limit: int = 10) -> str:
        from sqlalchemy import select

        from app.models.patient import TreatmentEvent

        stmt = (
            select(TreatmentEvent)
            .where(TreatmentEvent.patient_id == patient_id)
            .order_by(TreatmentEvent.event_date.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        events = result.scalars().all()
        if not events:
            return "该患者暂无治疗记录"
        lines = ["--- 近期治疗记录 ---"]
        for e in events:
            fb = f" (建议{e.follow_up_days}天后回访)" if e.follow_up_days else ""
            lines.append(
                f"[{e.event_date.strftime('%Y-%m-%d')}] {e.event_name} "
                f"[{e.event_type}] | 医生: {e.doctor or '未知'}{fb}"
            )
        return "\n".join(lines)

    async def assess_symptom(
        self,
        callback_id: int,
        dimension: str,
        score: float,
        description: str,
    ) -> str:
        from app.models.callback import Assessment

        assessment = Assessment(
            callback_id=callback_id,
            dimension=dimension,
            score=score,
            description=description,
        )
        self.db.add(assessment)
        await self.db.flush()
        return f"已记录 {dimension} 评估: 评分={score}, 描述={description}"

    async def flag_urgent_care(self, callback_id: int, reason: str) -> str:
        from app.models.callback import CallbackRecord

        cb = await self.db.get(CallbackRecord, callback_id)
        if cb:
            cb.needs_urgent_care = True
            cb.followup_actions = f"【紧急】{reason}"
            await self.db.flush()
        return f"⚠️ 已标记为紧急: {reason}"

    async def finalize_callback(
        self,
        callback_id: int,
        recovery_level: str,
        result_summary: str,
        followup_actions: str | None = None,
        conversation_log: str | None = None,
        call_duration: int | None = None,
    ) -> str:
        from datetime import datetime, timezone

        from app.models.callback import CallbackRecord

        cb = await self.db.get(CallbackRecord, callback_id)
        if not cb:
            return f"错误：未找到回访记录 (ID={callback_id})"
        cb.status = "completed"
        cb.recovery_level = recovery_level
        cb.result_summary = result_summary
        cb.call_duration = call_duration
        cb.conversation_log = conversation_log
        if followup_actions:
            cb.followup_actions = followup_actions
        cb.called_at = datetime.now(timezone.utc)
        await self.db.flush()
        return f"✅ 回访记录(ID={callback_id})已完结，康复等级: {recovery_level}"
