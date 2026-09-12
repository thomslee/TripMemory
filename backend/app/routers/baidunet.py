# -*- coding: utf-8 -*-
"""百度网盘路由：授权、文件列表、照片同步、照片代理展示。"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, MemoryPhoto, BaiduNetAuth
from ..routers.auth import get_current_user
from ..services.baidunet_client import baidunet_client

router = APIRouter(prefix="/api/baidunet", tags=["baidunet"])


def _get_stored_auth(db: Session, user_id: int) -> BaiduNetAuth | None:
    """获取用户持久化的百度网盘授权。"""
    return db.query(BaiduNetAuth).filter(BaiduNetAuth.user_id == user_id).first()


@router.get("/auth-url")
def get_auth_url(current_user: User = Depends(get_current_user)):
    """获取百度网盘授权URL。"""
    url = baidunet_client.get_auth_url(state=str(current_user.id))
    return {"auth_url": url}


@router.post("/callback")
def auth_callback(code: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """授权回调，用code换取access_token并持久化。"""
    result = baidunet_client.get_access_token(code)
    if not result or "access_token" not in result:
        raise HTTPException(status_code=400, detail="授权失败，请重试")

    # 持久化授权信息，供照片代理展示使用
    auth = db.query(BaiduNetAuth).filter(BaiduNetAuth.user_id == current_user.id).first()
    if not auth:
        auth = BaiduNetAuth(user_id=current_user.id)
        db.add(auth)
    auth.access_token = result["access_token"]
    auth.refresh_token = result.get("refresh_token")
    auth.expires_in = result.get("expires_in")
    try:
        info = baidunet_client.get_user_info(result["access_token"])
        auth.baidu_name = info.get("baidu_name") if info else None
    except Exception:
        pass
    db.commit()

    return {
        "access_token": result["access_token"],
        "refresh_token": result.get("refresh_token"),
        "expires_in": result.get("expires_in"),
        "scope": result.get("scope"),
    }


@router.get("/photo/{photo_id}/image")
def photo_image(photo_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """照片代理：使用持久化的百度网盘token拉取照片原图并流式返回。

    优先返回本地/静态图片URL指向的文件（如示例照片）；否则走百度网盘dlink代理。
    """
    photo = db.query(MemoryPhoto).filter(MemoryPhoto.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")

    # 本地静态文件（示例照片或已缓存的图片）
    if photo.thumbnail_url and photo.thumbnail_url.startswith("/static/"):
        from pathlib import Path
        local_path = Path(__file__).resolve().parent.parent.parent / photo.thumbnail_url.lstrip("/")
        if local_path.exists():
            media_type = "image/jpeg"
            if photo.thumbnail_url.lower().endswith(".png"):
                media_type = "image/png"
            return StreamingResponse(local_path.open("rb"), media_type=media_type)

    # 百度网盘代理：获取新鲜dlink并转发
    auth = _get_stored_auth(db, current_user.id)
    if not auth or not auth.access_token:
        raise HTTPException(status_code=400, detail="未授权百度网盘，请先完成授权")

    image_bytes, content_type = baidunet_client.fetch_photo_bytes(
        auth.access_token, photo.baidunet_file_id, photo.file_path,
    )
    if not image_bytes:
        raise HTTPException(status_code=502, detail="照片拉取失败")

    return StreamingResponse(iter([image_bytes]), media_type=content_type or "image/jpeg")


@router.get("/user-info")
def get_user_info(access_token: str, current_user: User = Depends(get_current_user)):
    """获取百度网盘用户信息。"""
    info = baidunet_client.get_user_info(access_token)
    if not info:
        raise HTTPException(status_code=400, detail="获取用户信息失败")
    return info


@router.get("/folders")
def list_folders(access_token: str, dir: str = "/", current_user: User = Depends(get_current_user)):
    """获取指定目录下的文件夹列表。"""
    files = baidunet_client.list_files(access_token, dir)
    folders = [
        {
            "fs_id": f.get("fs_id"),
            "name": f.get("server_filename"),
            "path": f.get("path"),
            "isdir": f.get("isdir"),
        }
        for f in files if f.get("isdir") == 1
    ]
    return {"folders": folders, "dir": dir}


@router.get("/photos")
def list_photos(access_token: str, folder_path: str, current_user: User = Depends(get_current_user)):
    """获取指定文件夹中的照片列表（含元数据）。"""
    photos = baidunet_client.get_photos_in_folder(access_token, folder_path)
    return {
        "total": len(photos),
        "photos": [
            {
                "fs_id": p["fs_id"],
                "filename": p["filename"],
                "path": p["path"],
                "size": p["size"],
                "width": p["width"],
                "height": p["height"],
                "date_taken": p["date_taken"],
            }
            for p in photos[:50]  # 最多返回50张预览
        ],
    }


@router.post("/sync/{trip_id}")
def sync_photos(
    trip_id: int,
    access_token: str,
    folder_path: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """将百度网盘文件夹中的照片同步到指定记忆行程。"""
    from ..models import MemoryTrip
    trip = db.query(MemoryTrip).filter(
        MemoryTrip.id == trip_id,
        MemoryTrip.user_id == current_user.id,
    ).first()
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在")

    result = baidunet_client.sync_photos_to_trip(access_token, trip_id, folder_path)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
