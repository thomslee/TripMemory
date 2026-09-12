# -*- coding: utf-8 -*-
"""照片模型：从百度网盘同步的照片元数据。"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from ..database import Base


class MemoryPhoto(Base):
    """照片元数据，大文件存在百度网盘，系统只存元数据和关联关系。"""
    __tablename__ = "memory_photos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trip_id = Column(Integer, ForeignKey("memory_trips.id"), nullable=False, index=True)
    node_id = Column(Integer, ForeignKey("memory_nodes.id"), nullable=True, index=True)  # 匹配到的行程节点
    baidunet_file_id = Column(String(128), nullable=True, index=True)  # 百度网盘文件ID
    filename = Column(String(256), nullable=False)
    file_path = Column(String(512), nullable=True)  # 百度网盘文件路径
    file_size = Column(Integer, default=0)
    file_type = Column(String(16), default="photo")  # photo / video
    thumbnail_url = Column(String(512), nullable=True)  # 缩略图URL
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
