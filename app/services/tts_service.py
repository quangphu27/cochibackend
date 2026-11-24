"""Text-to-speech: generate MP3, upload Cloudinary, keep history."""
import io
import os
import re
import tempfile
from datetime import datetime

from app.models.collections import COLLECTIONS
from app.repositories.base import BaseRepository
from app.utils.cloudinary_utils import get_folder_map, upload_audio

MAX_CHARS = 4500

VOICE_PRESETS = {
    "en-US": {"lang": "en", "tld": "com", "label": "English (US)"},
    "en-GB": {"lang": "en", "tld": "co.uk", "label": "English (UK)"},
    "en-AU": {"lang": "en", "tld": "com.au", "label": "English (AU)"},
    "en-IN": {"lang": "en", "tld": "co.in", "label": "English (IN)"},
}


class TtsHistoryRepo(BaseRepository):
    collection_name = COLLECTIONS["tts_history"]


tts_repo = TtsHistoryRepo()


def _slug_title(text: str) -> str:
    first = re.sub(r"\s+", " ", (text or "").strip())[:60]
    return first or "tts-audio"


def synthesize_mp3(text: str, voice: str = "en-US", slow: bool = False) -> bytes:
    from gtts import gTTS

    preset = VOICE_PRESETS.get(voice) or VOICE_PRESETS["en-US"]
    buf = io.BytesIO()
    tts = gTTS(text=text, lang=preset["lang"], tld=preset["tld"], slow=bool(slow))
    tts.write_to_fp(buf)
    return buf.getvalue()


class TtsService:
    def voices(self):
        return [
            {"value": k, "label": v["label"]}
            for k, v in VOICE_PRESETS.items()
        ]

    def generate(self, user_id: str, text: str, voice: str = "en-US", slow: bool = False):
        content = (text or "").strip()
        if len(content) < 2:
            return {"error": "Nhập ít nhất vài ký tự"}, 400
        if len(content) > MAX_CHARS:
            return {"error": f"Tối đa {MAX_CHARS} ký tự"}, 400
        if voice not in VOICE_PRESETS:
            voice = "en-US"

        try:
            mp3_bytes = synthesize_mp3(content, voice=voice, slow=slow)
        except Exception as e:
            return {"error": f"Không tạo được giọng nói: {e}"}, 502

        if not mp3_bytes:
            return {"error": "File âm thanh rỗng"}, 502

        title = _slug_title(content)
        filename = f"tts_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp3"
        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)
            with open(tmp_path, "wb") as f:
                f.write(mp3_bytes)
            upload = upload_audio(tmp_path, folder=get_folder_map().get("audio"))
        except Exception as e:
            return {"error": f"Upload Cloudinary thất bại: {e}"}, 502
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

        audio_url = upload.get("secure_url") or upload.get("url")
        record = tts_repo.create({
            "user_id": user_id,
            "text": content,
            "preview": content[:120],
            "voice": voice,
            "voice_label": VOICE_PRESETS[voice]["label"],
            "slow": bool(slow),
            "audio_url": audio_url,
            "public_id": upload.get("public_id"),
            "bytes": upload.get("bytes") or len(mp3_bytes),
            "duration": upload.get("duration"),
            "filename": filename,
            "title": title,
            "provider": "gtts",
        })
        return {"item": record}, 201

    def history(self, user_id: str, page: int = 1, limit: int = 20):
        return tts_repo.find_all(
            {"user_id": user_id},
            page=page,
            limit=limit,
            sort=[("created_at", -1)],
        ), 200

    def delete(self, user_id: str, item_id: str):
        item = tts_repo.find_by_id(item_id)
        if not item or item.get("user_id") != user_id:
            return {"error": "Không tìm thấy bản ghi"}, 404
        public_id = item.get("public_id")
        if public_id:
            try:
                from app.utils.cloudinary_utils import delete_file
                delete_file(public_id, resource_type="video")
            except Exception:
                pass
        tts_repo.delete(item_id)
        return {"ok": True}, 200
