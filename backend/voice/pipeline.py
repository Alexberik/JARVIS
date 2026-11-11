"""Voice pipeline scaffold: sherpa-onnx STT + piper TTS."""
from __future__ import annotations
from pathlib import Path
from typing import Any

class VoicePipeline:
    def __init__(self, config: dict, handle_text):
        self.cfg = config or {}
        self.enabled = bool(self.cfg.get("enabled"))
        self.wake = (self.cfg.get("wake_word") or "джарвис").lower()
        self.handle_text = handle_text

    def status(self) -> dict[str, Any]:
        stt_dir = Path(self.cfg.get("stt", {}).get("model_dir") or "models/stt")
        tts_path = Path(self.cfg.get("tts", {}).get("model_path") or "")
        return {
            "enabled": self.enabled,
            "wake_word": self.wake,
            "stt_ready": stt_dir.is_dir() and any(stt_dir.glob("*")),
            "tts_ready": tts_path.is_file() if tts_path.parts else False,
        }

    def process_utterance(self, text: str) -> dict[str, Any]:
        return self.handle_text((text or "").strip())

    def speak(self, text: str) -> dict[str, Any]:
        if not self.enabled:
            return {"ok": False, "error": "voice.enabled=false"}
        return {"ok": False, "error": "Piper model not configured — see docs/VOICE.md", "text": text}
