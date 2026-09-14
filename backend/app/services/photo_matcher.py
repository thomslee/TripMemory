# -*- coding: utf-8 -*-
"""照片与行程节点匹配服务：先按地点（GPS）匹配，其次按拍摄时间匹配。"""
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


def _time_score(photo_time: datetime | None, node) -> float:
    """时间评分：2小时内满分，2-4小时线性衰减，超4小时0分。"""
    if not photo_time or not node.start_time:
        return 0.0
    node_time_str = f"{photo_time.strftime('%Y-%m-%d')} {node.start_time}"
    node_time = parse_time(node_time_str)
    if not node_time:
        return 0.0
    time_diff = abs((photo_time - node_time).total_seconds()) / 60  # 分钟
    if time_diff <= 120:
        return 100.0
    if time_diff <= 240:
        return 100.0 - (time_diff - 120) / 120 * 100
    return 0.0


def match_photos_to_nodes(trip_id: int) -> dict:
    """
    将照片自动匹配到行程节点。

    匹配策略（先地点后时间）：
    1. 地点优先：照片含 GPS 且节点有坐标时，取距离最近的节点；
       距离 ≤2km 直接命中（地点决定），2-5km 用距离+时间混合评分。
    2. 时间兜底：照片无 GPS、节点无坐标或地点未命中时，按拍摄时间匹配。
    仅处理 unmatched 照片；综合分 ≥40 才匹配。
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

        nodes_with_coords = [n for n in nodes if n.lat and n.lng]
        matched_count = 0

        for photo in photos:
            best_node = None
            best_score = 0.0

            photo_time = photo.taken_time
            photo_lat = float(photo.taken_lat) if photo.taken_lat else None
            photo_lng = float(photo.taken_lng) if photo.taken_lng else None

            # ── 第一优先：地点匹配 ──
            if photo_lat is not None and photo_lng is not None and nodes_with_coords:
                closest = None
                best_dist = float("inf")
                for node in nodes_with_coords:
                    try:
                        d = haversine(photo_lat, photo_lng, float(node.lat), float(node.lng))
                    except (ValueError, TypeError):
                        continue
                    if d < best_dist:
                        best_dist = d
                        closest = node
                if closest is not None:
                    if best_dist <= 2:  # 2km 内：地点直接命中
                        best_node = closest
                        best_score = 100.0
                    elif best_dist <= 5:  # 2-5km：距离为主、时间辅助
                        dist_score = 100.0 - (best_dist - 2) / 3 * 100
                        time_score = _time_score(photo_time, closest)
                        best_score = dist_score * 0.6 + time_score * 0.4
                        best_node = closest

            # ── 第二优先：时间兜底（无 GPS / 无坐标节点 / 地点未命中） ──
            if best_node is None:
                for node in nodes:
                    ts = _time_score(photo_time, node)
                    if ts > best_score:
                        best_score = ts
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
