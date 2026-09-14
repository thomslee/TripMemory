# -*- coding: utf-8 -*-
"""记忆行程路由：行程列表、详情、从TripCanvas同步、照片管理、AI生成游记、配音。"""
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, MemoryTrip, MemoryNode, MemoryPhoto
from ..routers.auth import get_current_user
from ..services.tripcanvas_client import tripcanvas_client
from ..services.credential_crypto import decrypt_password
from ..services.photo_matcher import match_photos_to_nodes
from ..services.photo_service import save_uploaded_photos
from ..services.ai_service import ai_service
from ..services.tts_service import generate_tts_sync

router = APIRouter(prefix="/api/memory", tags=["memory"])

STATIC_ROOT = Path(__file__).resolve().parent.parent.parent / "static"


def _photo_display_url(photo: MemoryPhoto) -> str:
    """照片展示URL：上传的照片直接走本地静态文件。"""
    return photo.thumbnail_url or f"/static/{photo.file_path}"


@router.get("/trips")
def list_trips(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取用户的记忆行程列表。"""
    trips = db.query(MemoryTrip).filter(MemoryTrip.user_id == current_user.id).order_by(MemoryTrip.created_at.desc()).all()
    return [
        {
            "id": t.id,
            "title": t.title,
            "dest_city": t.dest_city,
            "total_days": t.total_days,
            "depart_date": t.depart_date.isoformat() if t.depart_date else None,
            "return_date": t.return_date.isoformat() if t.return_date else None,
            "status": t.status,
            "cover_image": t.cover_image,
            "photo_count": len(t.photos),
            "created_at": t.created_at.isoformat(),
        }
        for t in trips
    ]


@router.get("/trips/{trip_id}")
def get_trip(trip_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取记忆行程详情（含节点和照片）。"""
    trip = db.query(MemoryTrip).filter(MemoryTrip.id == trip_id, MemoryTrip.user_id == current_user.id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在")

    nodes = []
    for node in trip.nodes:
        photos = [
            {
                "id": p.id,
                "filename": p.filename,
                "thumbnail_url": p.thumbnail_url,
                "display_url": _photo_display_url(p),
                "taken_time": p.taken_time.isoformat() if p.taken_time else None,
                "is_cover": p.is_cover,
            }
            for p in node.photos
        ]
        nodes.append({
            "id": node.id,
            "day_no": node.day_no,
            "sort_order": node.sort_order,
            "city": node.city,
            "name": node.name,
            "node_type": node.node_type,
            "address": node.address,
            "lat": node.lat,
            "lng": node.lng,
            "start_time": node.start_time,
            "end_time": node.end_time,
            "weather": node.weather,
            "temperature": node.temperature,
            "article": node.article,
            "audio_url": node.audio_url,
            "bgm_url": node.bgm_url,
            "note": node.note,
            "photos": photos,
        })

    unmatched_photos = [
        {
            "id": p.id,
            "filename": p.filename,
            "thumbnail_url": p.thumbnail_url,
            "display_url": _photo_display_url(p),
            "taken_time": p.taken_time.isoformat() if p.taken_time else None,
        }
        for p in trip.photos if not p.node_id
    ]

    return {
        "id": trip.id,
        "title": trip.title,
        "dest_city": trip.dest_city,
        "total_days": trip.total_days,
        "depart_date": trip.depart_date.isoformat() if trip.depart_date else None,
        "return_date": trip.return_date.isoformat() if trip.return_date else None,
        "status": trip.status,
        "cover_image": trip.cover_image,
        "nodes": nodes,
        "unmatched_photos": unmatched_photos,
    }


@router.post("/sync-from-tripcanvas/{tripcanvas_trip_id}")
def sync_from_tripcanvas(tripcanvas_trip_id: int, current_user: User = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    """从TripCanvas同步行程定稿。

    若当前用户在「个人中心」绑定了 TripCanvas 账号，则使用该账号访问
    TripCanvas（可同步本人账号下的行程）；否则使用后端服务账号。
    同步时顺带拉取绑定账号的用户画像（gender/age/identity/preferences）缓存到本地，
    供 AI 生成游记等个性化功能使用。
    """
    try:
        bound_name = current_user.tripcanvas_username
        bound_pass = decrypt_password(current_user.tripcanvas_password)
        if bound_name and bound_pass:
            trip = tripcanvas_client.sync_trip(
                tripcanvas_trip_id, current_user.id,
                username=bound_name, password=bound_pass,
            )
            # 同步成功 → 拉取绑定账号的用户画像并缓存到本地用户
            if trip:
                profile = tripcanvas_client.get_user_profile(bound_name, bound_pass)
                if profile:
                    current_user.gender = profile.get("gender")
                    current_user.age = profile.get("age")
                    current_user.identity = profile.get("identity")
                    current_user.preferences = profile.get("preferences")
                    db.add(current_user)
                    db.commit()
                    print(f"[TripCanvas] 用户画像已缓存: {bound_name} -> {profile.get('preferences')}")
        else:
            trip = tripcanvas_client.sync_trip(tripcanvas_trip_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not trip:
        raise HTTPException(status_code=400, detail="同步失败，请检查TripCanvas连接配置")
    return {"id": trip.id, "title": trip.title, "message": "同步成功"}


@router.post("/trips/{trip_id}/match-photos")
def match_photos(trip_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """自动匹配照片到行程节点。"""
    trip = db.query(MemoryTrip).filter(MemoryTrip.id == trip_id, MemoryTrip.user_id == current_user.id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在")
    result = match_photos_to_nodes(trip_id)
    return result


@router.post("/trips/{trip_id}/photos/upload")
async def upload_photos(
    trip_id: int,
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传精选照片到记忆行程（支持多文件，自动提取EXIF拍摄时间并压缩存储）。"""
    trip = db.query(MemoryTrip).filter(MemoryTrip.id == trip_id, MemoryTrip.user_id == current_user.id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在")

    result = save_uploaded_photos(trip_id, files)

    # 上传成功后自动执行时间匹配
    match_result = {"matched": 0, "unmatched": 0, "total": 0}
    if result["saved"] > 0:
        match_result = match_photos_to_nodes(trip_id)

    return {
        **result,
        "match": match_result,
        "message": f"成功上传{result['saved']}张照片" if result["saved"] else "上传失败",
    }


@router.put("/trips/{trip_id}/photos/{photo_id}/assign")
def assign_photo_to_node(
    trip_id: int,
    photo_id: int,
    node_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """手动将未匹配照片关联到指定行程节点（或取消关联 node_id=0）。"""
    photo = db.query(MemoryPhoto).filter(
        MemoryPhoto.id == photo_id,
        MemoryPhoto.trip_id == trip_id,
    ).first()
    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")

    if node_id:
        node = db.query(MemoryNode).filter(MemoryNode.id == node_id, MemoryNode.trip_id == trip_id).first()
        if not node:
            raise HTTPException(status_code=404, detail="节点不存在")
        photo.node_id = node_id
        photo.match_status = "manual"
        photo.match_score = 100
    else:
        photo.node_id = None
        photo.match_status = "unmatched"
        photo.match_score = None
    db.commit()
    return {"message": "关联成功"}


@router.delete("/trips/{trip_id}/photos/{photo_id}")
def delete_photo(
    trip_id: int,
    photo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """从照片库删除照片（文件+记录；已关联节点自动解除关联）。"""
    photo = db.query(MemoryPhoto).filter(
        MemoryPhoto.id == photo_id,
        MemoryPhoto.trip_id == trip_id,
    ).first()
    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")

    # 删除磁盘文件（file_path 形如 photos/{trip_id}/{name}）
    try:
        from pathlib import Path as _Path
        photo_file = _Path(photo.file_path) if photo.file_path else None
        if photo_file and not photo_file.is_absolute():
            full = _Path(__file__).resolve().parent.parent.parent / "static" / photo_file
            if full.exists():
                full.unlink()
    except Exception as e:
        print(f"[PhotoDelete] 文件删除失败: {e}")

    db.delete(photo)
    db.commit()
    return {"message": "照片已删除"}


@router.post("/trips/{trip_id}/nodes/{node_id}/generate-article")
def generate_article(trip_id: int, node_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """AI生成单个节点的游记（结合用户画像与出行偏好，个性化写作）。"""
    node = db.query(MemoryNode).filter(MemoryNode.id == node_id, MemoryNode.trip_id == trip_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")
    trip = db.query(MemoryTrip).filter(MemoryTrip.id == trip_id).first()
    photo_count = len(node.photos)
    article = ai_service.generate_article(
        node_name=node.name,
        node_type=node.node_type or "attraction",
        city=node.city or "",
        weather=node.weather or "",
        user_note=node.note or "",
        photo_count=photo_count,
        profile={
            "gender": current_user.gender,
            "age": current_user.age,
            "identity": current_user.identity,
            "preferences": current_user.preferences,
        },
        travel_prefs=trip.travel_preferences if trip else None,
    )
    if article:
        node.article = article
        db.commit()
    return {"article": article}


@router.put("/trips/{trip_id}/nodes/{node_id}")
def update_node(trip_id: int, node_id: int, article: str = None, note: str = None, audio_url: str = None, bgm_url: str = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """更新节点信息（游记、备注、音频等）。"""
    node = db.query(MemoryNode).filter(MemoryNode.id == node_id, MemoryNode.trip_id == trip_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")
    if article is not None:
        node.article = article
    if note is not None:
        node.note = note
    if audio_url is not None:
        node.audio_url = audio_url
    if bgm_url is not None:
        node.bgm_url = bgm_url
    db.commit()
    return {"message": "更新成功"}


@router.post("/trips/{trip_id}/nodes/{node_id}/tts")
def generate_node_tts(trip_id: int, node_id: int, voice: str = "xiaoxiao", current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """生成单节点游记配音（edge-tts，无需API密钥）。"""
    node = db.query(MemoryNode).filter(MemoryNode.id == node_id, MemoryNode.trip_id == trip_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")
    if not node.article:
        raise HTTPException(status_code=400, detail="该节点还没有游记文字，请先生成游记")

    from ..services.tts_service import VOICES
    voice_name = VOICES.get(voice, "zh-CN-XiaoxiaoNeural")
    audio_path = generate_tts_sync(node.article, node.name, voice_name)
    if not audio_path:
        raise HTTPException(status_code=500, detail="配音生成失败，请稍后重试")

    node.audio_url = audio_path
    db.commit()
    return {"audio_url": audio_path, "message": "配音生成成功"}


@router.post("/trips/{trip_id}/tts-all")
def generate_trip_tts(trip_id: int, voice: str = "xiaoxiao", current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """批量生成行程所有节点的游记配音。"""
    trip = db.query(MemoryTrip).filter(MemoryTrip.id == trip_id, MemoryTrip.user_id == current_user.id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在")

    from ..services.tts_service import VOICES
    voice_name = VOICES.get(voice, "zh-CN-XiaoxiaoNeural")

    generated, skipped, failed = 0, 0, 0
    for node in trip.nodes:
        if not node.article:
            skipped += 1
            continue
        audio_path = generate_tts_sync(node.article, node.name, voice_name)
        if audio_path:
            node.audio_url = audio_path
            generated += 1
        else:
            failed += 1
    db.commit()
    return {
        "generated": generated,
        "skipped": skipped,
        "failed": failed,
        "total": len(trip.nodes),
        "message": f"配音完成：生成{generated}个，跳过{skipped}个无游记节点" + (f"，{failed}个失败" if failed else ""),
    }


@router.get("/bgm-list")
def list_bgm(current_user: User = Depends(get_current_user)):
    """获取内置背景音乐列表。"""
    bgm_dir = STATIC_ROOT / "bgm"
    tracks = []
    if bgm_dir.exists():
        for f in sorted(bgm_dir.glob("*.mp3")):
            name = f.stem
            # 从文件名提取展示名（如 01_温柔钢琴 → 温柔钢琴）
            display = name.split("_", 1)[-1] if "_" in name else name
            tracks.append({"id": name, "name": display, "url": f"/static/bgm/{f.name}"})
    return {"tracks": tracks}


@router.delete("/trips/{trip_id}")
def delete_trip(trip_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """删除记忆行程。"""
    trip = db.query(MemoryTrip).filter(MemoryTrip.id == trip_id, MemoryTrip.user_id == current_user.id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在")
    db.delete(trip)
    db.commit()
    return {"message": "删除成功"}
