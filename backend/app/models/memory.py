# -*- coding: utf-8 -*-
"""记忆行程模型：从TripCanvas同步的定稿行程。"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, DateTime, Date, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from ..database import Base


class MemoryTrip(Base):
    """一次旅行的记忆，关联TripCanvas的定稿行程。"""
    __tablename__ = "memory_trips"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tripcanvas_trip_id = Column(Integer, nullable=True, index=True)  # 关联TripCanvas的行程ID
    title = Column(String(128), nullable=False)
    dest_city = Column(String(64), nullable=True)
    total_days = Column(Integer, default=1)
    depart_date = Column(Date, nullable=True)
    return_date = Column(Date, nullable=True)
    cover_image = Column(String(512), nullable=True)  # 封面图URL
    status = Column(String(16), default="draft")  # draft / syncing / completed
    baidunet_folder = Column(String(256), nullable=True)  # 遗留字段（百度网盘已移除，保留兼容）
    travel_preferences = Column(JSON, nullable=True)  # 出行偏好（来自TripCanvas）：{pace,budget,travelers,travel_type,requirements}
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    nodes = relationship("MemoryNode", back_populates="trip", cascade="all, delete-orphan", order_by="MemoryNode.sort_order")
    photos = relationship("MemoryPhoto", back_populates="trip", cascade="all, delete-orphan")


class MemoryNode(Base):
    """行程节点：从TripCanvas同步的地点节点。"""
    __tablename__ = "memory_nodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trip_id = Column(Integer, ForeignKey("memory_trips.id"), nullable=False, index=True)
    day_no = Column(Integer, nullable=False)
    sort_order = Column(Integer, nullable=False)
    city = Column(String(64), nullable=True)
    name = Column(String(128), nullable=False)
    node_type = Column(String(16), nullable=True)  # hotel / attraction / restaurant / station
    address = Column(String(256), nullable=True)
    lat = Column(String(32), nullable=True)
    lng = Column(String(32), nullable=True)
    start_time = Column(String(8), nullable=True)
    end_time = Column(String(8), nullable=True)
    duration_minutes = Column(Integer, default=0)
    weather = Column(String(64), nullable=True)  # 当天天气
    temperature = Column(String(32), nullable=True)  # 温度
    article = Column(Text, nullable=True)  # AI生成的游记文字
    audio_url = Column(String(512), nullable=True)  # 配音音频URL
    bgm_url = Column(String(512), nullable=True)  # 背景音乐URL
    note = Column(Text, nullable=True)  # 用户备注
    created_at = Column(DateTime, default=datetime.now)

    trip = relationship("MemoryTrip", back_populates="nodes")
    photos = relationship("MemoryPhoto", back_populates="node", cascade="all, delete-orphan")
