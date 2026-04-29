from __future__ import annotations

"""
对话编排器 — Agent 核心。
管理一次回访通话的完整生命周期：
1. 加载患者信息 → 2. 构建 conversation → 3. 驱动 LLM 对话 → 4. 处理 tool calls → 5. 完结回访
"""

import json
from datetime import datetime, timezone
from typing import Any

from anthropic import AsyncAnthropic

from app.agents.prompts import SYSTEM_PROMPT
from app.agents.tools import TOOLS, ToolHandler
from app.core.config import settings


class CallbackOrchestrator:
    """回访对话编排器"""

    def __init__(self, db_session):
        self.db = db_session
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.tool_handler = ToolHandler(db_session)
        self.model = settings.claude_model

    async def run_call(
        self,
        callback_id: int,
        patient_id: int,
        simulate: bool = False,
    ) -> dict[str, Any]:
        """
        执行一次回访通话。

        参数:
            callback_id: 回访记录ID
            patient_id: 患者ID
            simulate: 如果为 True，模拟对话过程而不实际调用 LLM（用于测试）

        返回:
            dict: 回访结果
        """
        from app.models.callback import CallbackRecord

        callback = await self.db.get(CallbackRecord, callback_id)
        if not callback:
            raise ValueError(f"Callback {callback_id} not found")

        # 加载患者信息到 system prompt 上下文
        patient_context = await self.tool_handler.get_patient_info(patient_id)
        treatment_context = await self.tool_handler.get_patient_treatments(patient_id)
        medical_context = await self.tool_handler.get_patient_medical_records(patient_id)

        enriched_system = (
            SYSTEM_PROMPT
            + "\n\n## 本次回访的患者信息\n\n"
            + patient_context
            + "\n\n"
            + treatment_context
            + "\n\n"
            + medical_context
        )

        if simulate:
            return await self._simulate_call(callback, enriched_system)

        return await self._real_call(callback, enriched_system)

    async def _real_call(
        self,
        callback: Any,
        system_prompt: str,
    ) -> dict[str, Any]:
        """真实调用 Claude API 驱动对话"""
        messages: list[dict] = [
            {
                "role": "user",
                "content": f"患者 {callback.patient.name if hasattr(callback.patient, 'name') else ''} 的回访通话已接通。请根据患者信息开始回访对话。",
            }
        ]

        max_turns = 20  # 防止无限循环
        turn_count = 0
        final_result: dict[str, Any] = {"status": "in_progress", "conversation": []}

        while turn_count < max_turns:
            turn_count += 1

            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=messages,
                tools=TOOLS,
            )

            # 处理回复
            for block in response.content:
                if block.type == "text":
                    text = block.text
                    messages.append({"role": "assistant", "content": text})
                    final_result.setdefault("conversation", []).append({
                        "role": "assistant",
                        "text": text,
                    })

                elif block.type == "tool_use":
                    tool_name = block.name
                    params = block.input if hasattr(block, "input") else {}
                    params = _ensure_dict(params)

                    messages.append({
                        "role": "assistant",
                        "content": [
                            {
                                "type": "tool_use",
                                "id": block.id,
                                "name": tool_name,
                                "input": params,
                            }
                        ],
                    })

                    # 执行工具
                    result = await self.tool_handler.execute(tool_name, params)
                    messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            }
                        ],
                    })

                    # 如果是 finalize_callback，结束对话
                    if tool_name == "finalize_callback":
                        final_result.update({
                            "status": "completed",
                            "recovery_level": params.get("recovery_level"),
                            "result_summary": params.get("result_summary"),
                            "followup_actions": params.get("followup_actions"),
                            "needs_urgent_care": callback.needs_urgent_care,
                        })
                        # 更新 callback 记录
                        callback.status = "completed"
                        callback.called_at = datetime.now(timezone.utc)
                        await self.db.flush()
                        return final_result

            # 检查是否自然结束（assistant 没发 tool_use 也没发 text 等情况）
            last_msg = messages[-1]
            if isinstance(last_msg.get("content"), str) and turn_count >= 3:
                # 如果最后几条都是纯文本且 Agent 没有再调用工具，判断是否结束
                pass

        # 超过最大轮次，强制结束
        callback.status = "completed"
        callback.result_summary = "对话超过最大轮次后自动结束"
        await self.db.flush()
        final_result["status"] = "max_turns_exceeded"
        return final_result

    async def _simulate_call(
        self,
        callback: Any,
        system_prompt: str,
    ) -> dict[str, Any]:
        """模拟通话，用于测试"""
        from app.agents.tools import ToolHandler

        handler = ToolHandler(self.db)

        # 模拟对话
        conversation = [
            {"role": "assistant", "text": "您好，请问是[患者姓名]吗？我是医院的回访医生，想了解一下您出院后的恢复情况。"},
            {"role": "patient", "text": "是的，我现在感觉还可以。"},
            {"role": "assistant", "text": "很好，请问您最近有没有哪里不舒服？伤口恢复得怎么样？"},
            {"role": "patient", "text": "伤口恢复得挺好的，就是有时候会有点疼。"},
            {"role": "assistant", "text": "疼痛的程度大概是多少分呢？0分是不疼，10分是最疼。"},
            {"role": "patient", "text": "大概3分吧，不太严重。"},
            {"role": "assistant", "text": "好的，那不影响日常活动吧？有没有按时吃药？"},
            {"role": "patient", "text": "不影响，药都有按时吃。"},
            {"role": "assistant", "text": "非常好。那饮食和睡眠怎么样？"},
            {"role": "patient", "text": "胃口不错，睡眠也挺好的。"},
            {"role": "assistant", "text": "太好了，看来恢复得不错。记得按时复诊，祝您早日康复！"},
        ]

        # 模拟评估记录
        await handler.assess_symptom(callback.id, "pain", 3, "轻微疼痛，不影响日常活动")
        await handler.assess_symptom(callback.id, "mobility", 1, "活动能力基本正常")
        await handler.assess_symptom(callback.id, "medication", 0, "按时用药，依从性好")
        await handler.assess_symptom(callback.id, "appetite", 1, "食欲良好")
        await handler.assess_symptom(callback.id, "sleep", 1, "睡眠质量好")

        # 完结
        result = await handler.finalize_callback(
            callback_id=callback.id,
            recovery_level="good",
            result_summary="患者术后恢复良好，轻微疼痛但可控，用药依从性好，饮食睡眠正常。",
            followup_actions="继续按时用药，注意伤口卫生，按预约时间复诊。",
            conversation_log=json.dumps(conversation, ensure_ascii=False),
            call_duration=180,
        )

        return {
            "status": "completed",
            "simulated": True,
            "recovery_level": "good",
            "result_summary": "患者术后恢复良好，轻微疼痛但可控，用药依从性好，饮食睡眠正常。",
            "followup_actions": "继续按时用药，注意伤口卫生，按预约时间复诊。",
            "conversation": conversation,
            "needs_urgent_care": False,
        }


def _ensure_dict(params: Any) -> dict[str, Any]:
    """确保参数是 dict 类型"""
    if isinstance(params, dict):
        return params
    if hasattr(params, "model_dump"):
        return params.model_dump()
    if hasattr(params, "dict"):
        return params.dict()
    return dict(params)
