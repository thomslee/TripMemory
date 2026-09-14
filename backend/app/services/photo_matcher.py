# -*- coding: utf-8 -*-
"""照片与行程节点匹配服务：先按地点（GPS）匹配，其次按拍摄时间匹配。"""
import math
from datetime import datetime, date
from ..models import MemoryPhoto, MemoryNode, MemoryTrip
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


def _node_datetime(photo_time: datetime, node) -> datetime | None:
    """把节点 start_time 与照片日期拼成完整时间（节点时间只存 HH:MM）。"""
    if not node.start_time:
        return None
    return parse_time(f"{photo_time.strftime('%Y-%m-%d')} {node.start_time}")


def _time_score(photo_time: datetime | None, node) -> float:
    """时间评分：2小时内满分，2-4小时线性衰减，超4小时0分。"""
    if not photo_time:
        return 0.0
    node_time = _node_datetime(photo_time, node)
    if not node_time:
        return 0.0
    time_diff = abs((photo_time - node_time).total_seconds()) / 60  # 分钟
    if time_diff <= 120:
        return 100.0
    if time_diff <= 240:
        return 100.0 - (time_diff - 120) / 120 * 100
    return 0.0


def _time_diff_minutes(photo_time: datetime | None, node) -> float:
    """照片与节点 start_time 的绝对时间差（分钟）；无法计算返回无穷大。"""
    if not photo_time:
        return float("inf")
    node_time = _node_datetime(photo_time, node)
    if not node_time:
        return float("inf")
    return abs((photo_time - node_time).total_seconds()) / 60


def _photo_day(photo_time: datetime | None, depart_date: date | None) -> int | None:
    """照片在行程中的第几天（1 起）；depart_date 缺失或照片不在行程内返回 None。"""
    if not photo_time or not depart_date:
        return None
    delta = (photo_time.date() - depart_date).days + 1
    return delta if 1 <= delta <= 365 else None


def match_photos_to_nodes(trip_id: int) -> dict:
    """
    将照片自动匹配到行程节点。

    匹配策略（先地点后时间）：
    1. 地点优先：照片含 GPS 且节点有坐标时，取距离最近的节点；
       距离 ≤2km 直接命中（地点决定），2-5km 用距离+时间混合评分。
    2. 时间兜底：照片无 GPS、节点无坐标或地点未命中时，按拍摄时间匹配。
       时间匹配带日期维度：照片属于行程第几天，就只在该天节点中匹配；
       分数并列时取时间差最小的节点。
    仅处理 unmatched 照片；综合分 ≥40 才匹配。
    """
    db = SessionLocal()
    try:
        photos = db.query(MemoryPhoto).filter(
            MemoryPhoto.trip_id == trip_id,
            MemoryPhoto.match_status == "unmatched",
        ).all()
        nodes = db.query(MemoryNode).filter(MemoryNode.trip_id == trip_id).all()
        trip = db.query(MemoryTrip).filter(MemoryTrip.id == trip_id).first()

        if not photos or not nodes:
            return {"matched": 0, "unmatched": len(photos)}

        depart_date = trip.depart_date if trip else None
        nodes_with_coords = [n for n in nodes if n.lat and n.lng]
        matched_count = 0

        for photo in photos:
            best_node = None
            best_score = 0.0

            photo_time = photo.taken_time
            try:
                photo_lat = float(photo.taken_lat) if photo.taken_lat else None
                photo_lng = float(photo.taken_lng) if photo.taken_lng else None
                if photo_lat is not None and (photo_lat != photo_lat):  # NaN 防御
                    photo_lat = None
                if photo_lng is not None and (photo_lng != photo_lng):
                    photo_lng = None
            except (TypeError, ValueError):
                photo_lat = photo_lng = None

            # 日期过滤：照片属于第几天，就只匹配该天的节点
            day = _photo_day(photo_time, depart_date)
            day_nodes = [n for n in nodes if n.day_no == day] if day is not None else []
            candidates = day_nodes if day_nodes else nodes

            # ── 第一优先：地点匹配（候选同一天节点，先按距离） ──
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
                ranked = []
                for node in candidates:
                    ts = _time_score(photo_time, node)
                    if ts <= 0:
                        continue
                    node_dt = _node_datetime(photo_time, node)
                    # 照片晚于节点开始时间 → 0（优先）；还没到该节点 → 1
                    after = 0 if node_dt and photo_time >= node_dt else 1
                    ranked.append((ts, after, -_time_diff_minutes(photo_time, node), node))
                # 分数高优先 → 已到该节点优先 → 时间差最小
                ranked.sort(key=lambda x: (-x[0], x[1], -x[2]))
                if ranked and ranked[0][0] > best_score:
                    best_node = ranked[0][3]
                    best_score = ranked[0][0]

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
