# -*- coding: utf-8 -*-
"""应用设置模型：key-value 存储大模型等外部接口配置。"""
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime
from ..database import Base


class AppSetting(Base):
    __tablename__ = "app_settings"

    skey = Column(String(64), primary_key=True)
    svalue = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
