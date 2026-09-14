# -*- coding: utf-8 -*-
"""用户模型。"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON
from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(64), nullable=True)
    role = Column(String(16), default="user")  # admin / user
    created_at = Column(DateTime, default=datetime.now)

    # TripCanvas 账号绑定（同步行程时使用该账号访问 TripCanvas，密码加密存储）
    tripcanvas_username = Column(String(64), nullable=True)
    tripcanvas_password = Column(String(255), nullable=True)

    # 用户画像（同步行程时从 TripCanvas 拉取缓存，用于 AI 个性化生成）
    gender = Column(String(8), nullable=True)  # 男/女/保密
    age = Column(Integer, nullable=True)
    identity = Column(String(16), nullable=True)  # 学生/职工/退休/其他
    preferences = Column(JSON, nullable=True)  # 兴趣标签，如["美食","购物","摄影"]
