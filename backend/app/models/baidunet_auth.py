# -*- coding: utf-8 -*-
"""百度网盘授权信息：持久化用户access_token，用于照片代理展示。"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from ..database import Base


class BaiduNetAuth(Base):
    """用户百度网盘授权信息（token持久化）。"""
    __tablename__ = "baidunet_auths"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    access_token = Column(String(512), nullable=False)
    refresh_token = Column(String(512), nullable=True)
    baidu_name = Column(String(128), nullable=True)
    expires_in = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
