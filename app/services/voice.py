from __future__ import annotations

"""
语音服务抽象层。

为 TTS（文本转语音）和 ASR（语音识别）定义抽象接口。
当前为桩实现，后续可对接 Azure Speech / Deepgram / ElevenLabs 等服务。
"""

from abc import ABC, abstractmethod
from typing import Optional


# ─── 抽象接口 ──────────────────────────────────────────────

class TTSEngine(ABC):
    """文字转语音引擎接口"""

    @abstractmethod
    async def synthesize(self, text: str, voice: Optional[str] = None) -> bytes:
        """将文本转换为语音音频"""
        ...


class ASREngine(ABC):
    """语音识别引擎接口"""

    @abstractmethod
    async def transcribe(self, audio: bytes, language: Optional[str] = None) -> str:
        """将语音音频转为文本"""
        ...


# ─── 桩实现（用于开发测试） ────────────────────────────────

class StubTTSEngine(TTSEngine):
    """桩实现：实际返回模拟数据"""

    async def synthesize(self, text: str, voice: Optional[str] = None) -> bytes:
        return f"[TTS STUB] voice={voice or 'default'} text='{text}'".encode("utf-8")


class StubASREngine(ASREngine):
    """桩实现：返回模拟识别结果"""

    def __init__(self, mock_responses: Optional[list[str]] = None):
        self.mock_responses = mock_responses or [
            "嗯，我现在感觉还好。",
            "伤口有点疼，但不严重。",
            "药都有按时吃。",
            "好的，谢谢医生。",
        ]
        self._index = 0

    async def transcribe(self, audio: bytes, language: Optional[str] = None) -> str:
        response = self.mock_responses[self._index % len(self.mock_responses)]
        self._index += 1
        return f"[ASR STUB] {response}"


# ─── 工厂 ──────────────────────────────────────────────────

class VoiceServiceFactory:

    @staticmethod
    def create_tts(engine_type: str = "stub") -> TTSEngine:
        engines = {
            "stub": StubTTSEngine,
            # "azure": AzureTTSEngine,  # 后续实现
            # "elevenlabs": ElevenLabsTTSEngine,  # 后续实现
        }
        cls = engines.get(engine_type)
        if not cls:
            raise ValueError(f"Unsupported TTS engine: {engine_type}")
        return cls()

    @staticmethod
    def create_asr(engine_type: str = "stub") -> ASREngine:
        engines = {
            "stub": StubASREngine,
            # "azure": AzureASREngine,
            # "deepgram": DeepgramASREngine,
        }
        cls = engines.get(engine_type)
        if not cls:
            raise ValueError(f"Unsupported ASR engine: {engine_type}")
        return cls()
