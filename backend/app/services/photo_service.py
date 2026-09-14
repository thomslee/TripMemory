# -*- coding: utf-8 -*-
"""照片上传服务：EXIF 提取、压缩、保存到本地 static/photos/{trip_id}/。

- 支持 jpg/png/webp（手机图库、电脑本地均可）
- 自动读取 EXIF 拍摄时间与相机型号（无 EXIF 时回退文件修改时间）
- 自动压缩：最长边 1920、JPEG 质量 85，控制存储占用
- 文件以 uuid 命名，杜绝路径穿越与重名覆盖
"""
import uuid
from datetime import datetime
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from ..database import SessionLocal
from ..models import MemoryPhoto

PHOTO_ROOT = Path(__file__).resolve().parent.parent.parent / "static" / "photos"

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MAX_BYTES = 20 * 1024 * 1024  # 单张上限 20MB
MAX_EDGE = 1920  # 压缩后的最长边像素
JPEG_QUALITY = 85


def _allowed(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXT


def _extract_exif(img: Image.Image) -> dict:
    """提取 EXIF：拍摄时间（DateTimeOriginal 优先）、相机型号。"""
    result = {"taken_time": None, "camera_model": None}
    try:
        exif = img.getexif()
        if not exif:
            return result
        model = exif.get(0x0110)  # Model
        if model:
            result["camera_model"] = str(model).strip()[:128]
        dt_original = exif.get(0x9003)  # DateTimeOriginal
        raw = dt_original or exif.get(0x0132)  # 回退 DateTime
        if raw:
            text = str(raw).strip()
            for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y:%m:%d"):
                try:
                    result["taken_time"] = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue
    except Exception:
        pass
    return result


def _compress(img: Image.Image) -> bytes:
    """压缩图片：最长边限制、转 JPEG、控制体积。"""
    img = img.convert("RGB") if img.mode not in ("RGB", "L") else img
    if max(img.size) > MAX_EDGE:
        ratio = MAX_EDGE / max(img.size)
        img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buf.getvalue()


def save_uploaded_photos(trip_id: int, files: list) -> dict:
    """保存一批上传照片并写入记录。

    返回: {"saved": n, "failed": m, "errors": [{"filename": ..., "reason": ...}]}
    """
    trip_dir = PHOTO_ROOT / str(trip_id)
    trip_dir.mkdir(parents=True, exist_ok=True)

    saved = 0
    errors = []
    db = SessionLocal()
    try:
        for file in files:
            fname = file.filename or "photo.jpg"
            if not _allowed(fname):
                errors.append({"filename": fname, "reason": "不支持的格式（仅支持 jpg/png/webp）"})
                continue
            try:
                raw = file.file.read()
                if len(raw) > MAX_BYTES:
                    errors.append({"filename": fname, "reason": "文件超过 20MB 上限"})
                    continue
                img = Image.open(BytesIO(raw))
                exif = _extract_exif(img)
                compressed = _compress(img)
                img.close()
            except UnidentifiedImageError:
                errors.append({"filename": fname, "reason": "无法识别的图片文件"})
                continue
            except Exception:
                errors.append({"filename": fname, "reason": "图片解析失败"})
                continue

            fname_stem = Path(fname).stem[:60] or "photo"
            stored_name = f"{fname_stem}_{uuid.uuid4().hex[:8]}.jpg"
            stored_path = trip_dir / stored_name
            stored_path.write_bytes(compressed)

            # 无 EXIF 拍摄时间时以当前时间兜底（multipart 无法获取文件 mtime）
            taken_time = exif["taken_time"] or datetime.now()

            photo = MemoryPhoto(
                trip_id=trip_id,
                filename=fname,
                file_path=f"photos/{trip_id}/{stored_name}",
                thumbnail_url=f"/static/photos/{trip_id}/{stored_name}",
                file_size=len(compressed),
                file_type="photo",
                taken_time=taken_time,
                camera_model=exif["camera_model"],
                match_status="unmatched",
            )
            db.add(photo)
            saved += 1

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[PhotoUpload] 保存失败: {e}")
        return {"saved": 0, "failed": len(files), "errors": [{"filename": "*", "reason": str(e)}]}
    finally:
        db.close()
    return {"saved": saved, "failed": len(files) - saved, "errors": errors}
