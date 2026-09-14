# -*- coding: utf-8 -*-
"""认证路由：登录、注册、获取用户信息。"""
import base64
import json
import time
import hashlib
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..config import settings
from ..models import User
from ..services.tripcanvas_client import tripcanvas_client
from ..services.credential_crypto import encrypt_password

router = APIRouter(prefix="/api/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _hash_password(password: str) -> str:
    """简单密码哈希（SHA256 + salt）。"""
    salt = "trip_memory_salt_2024"
    return hashlib.sha256((password + salt).encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    return _hash_password(plain) == hashed


def hash_password(password: str) -> str:
    return _hash_password(password)


def create_access_token(data: dict) -> str:
    """生成简单的access token（base64编码）。"""
    to_encode = data.copy()
    expire = time.time() + settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    to_encode.update({"exp": expire})
    token_str = json.dumps(to_encode)
    return base64.b64encode(token_str.encode()).decode()


def decode_access_token(token: str) -> dict | None:
    """解码token。"""
    try:
        token_str = base64.b64decode(token.encode()).decode()
        data = json.loads(token_str)
        if data.get("exp", 0) < time.time():
            return None
        return data
    except Exception:
        return None


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    data = decode_access_token(token)
    if not data or "user_id" not in data:
        raise HTTPException(status_code=401, detail="无效的认证凭证")
    user = db.query(User).filter(User.id == data["user_id"]).first()
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """管理员权限依赖（设置、用户管理等管理功能使用）。"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


@router.post("/register")
def register(username: str, password: str, nickname: str = None, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        username=username,
        password_hash=hash_password(password),
        nickname=nickname or username,
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"user_id": user.id, "username": user.username})
    return {"token": token, "user": {"id": user.id, "username": user.username, "nickname": user.nickname, "role": user.role}}


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token({"user_id": user.id, "username": user.username})
    return {"token": token, "user": {"id": user.id, "username": user.username, "nickname": user.nickname, "role": user.role}}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username, "nickname": current_user.nickname, "role": current_user.role}


class TripCanvasBindingIn(BaseModel):
    """绑定 TripCanvas 账号请求。"""
    tripcanvas_username: str
    tripcanvas_password: str


@router.get("/tripcanvas-binding")
def get_tripcanvas_binding(current_user: User = Depends(get_current_user)):
    """查询当前用户是否绑定 TripCanvas 账号（用户名掩码返回）。"""
    bound = bool(current_user.tripcanvas_username and current_user.tripcanvas_password)
    raw = current_user.tripcanvas_username or ""
    masked = (raw[:2] + "***") if bound else ""
    return {"bound": bound, "tripcanvas_username": masked}


@router.put("/tripcanvas-binding")
def set_tripcanvas_binding(data: TripCanvasBindingIn,
                           current_user: User = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    """绑定 TripCanvas 账号：先登录验证凭据有效，密码加密存储。"""
    token = tripcanvas_client.login_user(data.tripcanvas_username, data.tripcanvas_password)
    if not token:
        raise HTTPException(status_code=400, detail="TripCanvas 账号或密码错误，无法绑定")
    current_user.tripcanvas_username = data.tripcanvas_username
    current_user.tripcanvas_password = encrypt_password(data.tripcanvas_password)
    db.commit()
    return {"ok": True, "message": "绑定成功", "tripcanvas_username": data.tripcanvas_username}


@router.delete("/tripcanvas-binding")
def delete_tripcanvas_binding(current_user: User = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    """解绑 TripCanvas 账号。"""
    current_user.tripcanvas_username = None
    current_user.tripcanvas_password = None
    db.commit()
    return {"ok": True, "message": "已解绑"}


class ChangePasswordIn(BaseModel):
    """修改密码请求。"""
    old_password: str
    new_password: str


@router.post("/change-password")
def change_password(data: ChangePasswordIn,
                    current_user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    """修改当前用户密码。"""
    if not verify_password(data.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    if len(data.new_password) < 4:
        raise HTTPException(status_code=400, detail="新密码至少 4 位")
    current_user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"ok": True, "message": "密码已修改"}
