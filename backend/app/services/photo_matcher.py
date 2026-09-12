# -*- coding: utf-8 -*-
"""照片与行程节点匹配服务：基于拍摄时间和地点自动匹配。"""
import math
from datetime import datetime
from ..models import MemoryPhoto, MemoryNode
from ..database import SessionLocal


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """计算两点间的距离（公里）。"""
    R = 6371.0
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def parse_time(time_str: str | None) -> datetime | None:
    """解析时间字符串。"""
    if not time_str:
        return None
    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"]:
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    return None


def match_photos_to_nodes(trip_id: int) -> dict:
    """
    将照片自动匹配到行程节点。
    匹配策略：时间权重60% + 距离权重40%
    """
    db = SessionLocal()
    try:
        photos = db.query(MemoryPhoto).filter(
            MemoryPhoto.trip_id == trip_id,
            MemoryPhoto.match_status == "unmatched",
        ).all()
        nodes = db.query(MemoryNode).filter(MemoryNode.trip_id == trip_id).all()

        if not photos or not nodes:
            return {"matched": 0, "unmatched": len(photos)}

        matched_count = 0
        for photo in photos:
            best_node = None
            best_score = 0

            photo_time = photo.taken_time
            photo_lat = float(photo.taken_lat) if photo.taken_lat else None
            photo_lng = float(photo.taken_lng) if photo.taken_lng else None

            for node in nodes:
                score = 0

                # 时间匹配（权重60%）
                if photo_time and node.start_time:
                    node_time_str = f"{photo_time.strftime('%Y-%m-%d')} {node.start_time}"
                    node_time = parse_time(node_time_str)
                    if node_time:
                        time_diff = abs((photo_time - node_time).total_seconds()) / 60  # 分钟
                        # 2小时内满分，超过4小时0分
                        if time_diff <= 120:
                            time_score = 100
                        elif time_diff <= 240:
                            time_score = 100 - (time_diff - 120) / 120 * 100
                        else:
                            time_score = 0
                        score += time_score * 0.6

                # 距离匹配（权重40%）
                if photo_lat and photo_lng and node.lat and node.lng:
                    try:
                        distance = haversine(photo_lat, photo_lng, float(node.lat), float(node.lng))
                        # 1公里内满分，超过5公里0分
                        if distance <= 1:
                            dist_score = 100
                        elif distance <= 5:
                            dist_score = 100 - (distance - 1) / 4 * 100
                        else:
                            dist_score = 0
                        score += dist_score * 0.4
                    except (ValueError, TypeError):
                        pass

                if score > best_score:
                    best_score = score
                    best_node = node

            # 阈值：综合得分大于40才匹配
            if best_node and best_score >= 40:
                photo.node_id = best_node.id
                photo.match_status = "matched"
                photo.match_score = int(best_score)
                matched_count += 1

        db.commit()
        return {
            "matched": matched_count,
            "unmatched": len(photos) - matched_count,
            "total": len(photos),
        }
    except Exception as e:
        db.rollback()
        print(f"[PhotoMatch] 匹配失败: {e}")
        return {"matched": 0, "unmatched": 0, "error": str(e)}
    finally:
        db.close()
