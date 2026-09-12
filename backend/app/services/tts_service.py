# -*- coding: utf-8 -*-
"""游记配音服务：基于 edge-tts（微软在线语音）将游记文字转为MP3。

- 无需API密钥，免费可用
- 中文女声 zh-CN-XiaoxiaoNeural（温暖、适合游记朗读）
- 音频文件保存到 backend/static/audio/ 下，通过 /static 路径对外提供
"""
import asyncio
import hashlib
import os
from pathlib import Path

AUDIO_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "audio"
DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"

# 可选音色（可扩展）
VOICES = {
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",  # 女声·温暖
    "xiaoyi": "zh-CN-XiaoyiNeural",      # 女声·活泼
    "yunjian": "zh-CN-YunjianNeural",    # 男声·激情
    "yunxi": "zh-CN-YunxiNeural",        # 男声·阳光
}


def _slug(text: str, max_len: int = 24) -> str:
    """从文本生成安全的文件名字段。"""
    keep = "".join(ch for ch in text if ch.isalnum() or ch in "-_")
    return keep[:max_len] or "narration"


def audio_exists(node_name: str, article: str) -> Path | None:
    """检查是否已生成对应音频，返回文件路径。"""
    digest = hashlib.md5(article.encode("utf-8")).hexdigest()[:10]
    fname = f"node_{_slug(node_name)}_{digest}.mp3"
    path = AUDIO_DIR / fname
    return path if path.exists() else None


def generate_tts_sync(text: str, node_name: str = "node", voice: str = DEFAULT_VOICE) -> str | None:
    """同步包装：生成TTS音频，返回 /static/audio/xxx.mp3 相对路径。"""
    try:
        return asyncio.run(generate_tts(text, node_name, voice))
    except Exception as e:
        print(f"[TTS] 生成失败: {e}")
        return None


async def generate_tts(text: str, node_name: str = "node", voice: str = DEFAULT_VOICE) -> str | None:
    """生成TTS音频，返回 /static/audio/xxx.mp3 相对路径。"""
    import edge_tts

    if not text or not text.strip():
        return None

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    # 相同文本不重复生成
    digest = hashlib.md5(text.encode("utf-8")).hexdigest()[:10]
    fname = f"node_{_slug(node_name)}_{digest}.mp3"
    out_path = AUDIO_DIR / fname
    if out_path.exists():
        return f"/static/audio/{fname}"

    communicator = edge_tts.Communicate(text, voice=voice, rate="-5%")
    await communicator.save(str(out_path))

    if out_path.exists() and out_path.stat().st_size > 0:
        return f"/static/audio/{fname}"
    return None
