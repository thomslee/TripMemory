# -*- coding: utf-8 -*-
"""照片模型：本地/图库上传的精选照片元数据。"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from ..database import Base


class MemoryPhoto(Base):
    """照片元数据：文件存服务器磁盘 static/photos/，系统存元数据和关联关系。"""
    __tablename__ = "memory_photos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trip_id = Column(Integer, ForeignKey("memory_trips.id"), nullable=False, index=True)
    node_id = Column(Integer, ForeignKey("memory_nodes.id"), nullable=True, index=True)  # 匹配到的行程节点
    baidunet_file_id = Column(String(128), nullable=True, index=True)  # 遗留字段（百度网盘已移除，保留兼容）
    filename = Column(String(256), nullable=False)  # 原始文件名
    file_path = Column(String(512), nullable=True)  # 相对存储路径（photos/{trip_id}/{file}）
    file_size = Column(Integer, default=0)
    file_type = Column(String(16), default="photo")  # photo / video
    thumbnail_url = Column(String(512), nullable=True)  # 展示URL（/static/photos/...）
    download_url = Column(String(512), nullable=True)  # 下载URL（临时）
    taken_time = Column(DateTime, nullable=True, index=True)  # 拍摄时间（EXIF）
    taken_lat = Column(String(32), nullable=True)  # 拍摄纬度（EXIF）
    taken_lng = Column(String(32), nullable=True)  # 拍摄经度（EXIF）
    camera_model = Column(String(128), nullable=True)  # 相机型号
    match_status = Column(String(16), default="unmatched")  # unmatched / matched / manual
    match_score = Column(Integer, default=0)  # 匹配置信度
    is_cover = Column(Integer, default=0)  # 是否为封面
    sort_order = Column(Integer, default=0)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    trip = relationship("MemoryTrip", back_populates="photos")
    node = relationship("MemoryNode", back_populates="photos")
