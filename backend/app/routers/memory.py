# -*- coding: utf-8 -*-
"""记忆行程路由：行程列表、详情、从TripCanvas同步、照片管理、AI生成游记、配音。"""
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, MemoryTrip, MemoryNode, MemoryPhoto
from ..routers.auth import get_current_user
from ..services.tripcanvas_client import tripcanvas_client
from ..services.photo_matcher import match_photos_to_nodes
from ..services.ai_service import ai_service
from ..services.tts_service import generate_tts_sync

router = APIRouter(prefix="/api/memory", tags=["memory"])

STATIC_ROOT = Path(__file__).resolve().parent.parent.parent / "static"


def _photo_display_url(photo: MemoryPhoto) -> str:
    """照片展示URL：静态/本地文件直接用，百度网盘照片走代理。"""
    if photo.thumbnail_url and (photo.thumbnail_url.startswith("/static/") or photo.thumbnail_url.startswith("http")):
        return photo.thumbnail_url
    return f"/api/baidunet/photo/{photo.id}/image"


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
        "baidunet_folder": trip.baidunet_folder,
        "nodes": nodes,
        "unmatched_photos": unmatched_photos,
    }


@router.post("/sync-from-tripcanvas/{tripcanvas_trip_id}")
def sync_from_tripcanvas(tripcanvas_trip_id: int, current_user: User = Depends(get_current_user)):
    """从TripCanvas同步行程定稿。"""
    try:
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


@router.post("/trips/{trip_id}/nodes/{node_id}/generate-article")
def generate_article(trip_id: int, node_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """AI生成单个节点的游记。"""
    node = db.query(MemoryNode).filter(MemoryNode.id == node_id, MemoryNode.trip_id == trip_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")
    photo_count = len(node.photos)
    article = ai_service.generate_article(
        node_name=node.name,
        node_type=node.node_type or "attraction",
        city=node.city or "",
        weather=node.weather or "",
        user_note=node.note or "",
        photo_count=photo_count,
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
