# -*- coding: utf-8 -*-
"""TripCanvas API对接服务：从途迹行程规划系统同步定稿行程数据。"""
import urllib.parse
import urllib.request
import json
import time
from ..config import settings
from ..models import MemoryTrip, MemoryNode, MemoryPhoto
from ..database import SessionLocal


def _http_get(url, params=None, headers=None, timeout=30):
    """发送GET请求。"""
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read().decode("utf-8")
        return json.loads(data)


def _http_post(url, data, headers=None, timeout=30):
    """发送POST请求（JSON）。"""
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), method="POST")
    req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


class TripCanvasClient:
    """TripCanvas API客户端。

    token 支持两种来源：
    1. 配置的静态 token（TRIPCANVAS_API_TOKEN）
    2. 服务账号自动登录（TRIPCANVAS_SERVICE_USERNAME/PASSWORD），token 7天过期后自动续期
    """

    def __init__(self):
        self.base_url = settings.TRIPCANVAS_API_URL.rstrip("/")
        self.token = settings.TRIPCANVAS_API_TOKEN
        self._dynamic_token = None
        self._token_expire_at = 0.0
        self._service_user = getattr(settings, "TRIPCANVAS_SERVICE_USERNAME", "") or ""
        self._service_pass = getattr(settings, "TRIPCANVAS_SERVICE_PASSWORD", "") or ""
        # 按绑定账号缓存的动态 token：{"username": {"token": str, "expire_at": float}}
        self._user_tokens: dict[str, dict] = {}

    def _headers(self, token: str | None = None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        else:
            t = self._get_valid_token()
            if t:
                headers["Authorization"] = f"Bearer {t}"
        return headers

    def _get_valid_token(self) -> str | None:
        """获取可用token：优先静态token，否则自动登录服务账号并缓存。"""
        if self.token:
            return self.token
        # 动态token仍在有效期内
        if self._dynamic_token and time.time() < self._token_expire_at - 60:
            return self._dynamic_token
        if not self._service_user or not self._service_pass:
            return None
        try:
            resp = _http_post(
                f"{self.base_url}/auth/login",
                {"username": self._service_user, "password": self._service_pass},
                timeout=15,
            )
            token = resp.get("token")
            if token:
                self._dynamic_token = token
                # 默认按7天有效期，提前60秒续期
                self._token_expire_at = time.time() + 7 * 24 * 3600
                print("[TripCanvas] 服务账号自动登录成功")
                return token
        except Exception as e:
            print(f"[TripCanvas] 自动登录失败: {e}")
        return None

    def login_user(self, username: str, password: str) -> str | None:
        """用指定 TripCanvas 账号登录，返回 token（按账号缓存，7天续期）。"""
        cached = self._user_tokens.get(username)
        if cached and time.time() < cached["expire_at"] - 60:
            return cached["token"]
        try:
            resp = _http_post(
                f"{self.base_url}/auth/login",
                {"username": username, "password": password},
                timeout=15,
            )
            token = resp.get("token")
            if token:
                self._user_tokens[username] = {
                    "token": token,
                    "expire_at": time.time() + 7 * 24 * 3600,
                }
                return token
        except Exception as e:
            print(f"[TripCanvas] 账号 {username} 登录失败: {e}")
        return None

    def get_trip(self, trip_id: int, token: str | None = None) -> dict | None:
        """获取TripCanvas的行程详情。"""
        try:
            return _http_get(f"{self.base_url}/trips/{trip_id}", headers=self._headers(token))
        except Exception as e:
            print(f"[TripCanvas] 获取行程失败: {e}")
            return None

    def get_timeline(self, trip_id: int, token: str | None = None) -> dict | None:
        """获取行程时间线（含节点、边、天气）。"""
        try:
            return _http_get(f"{self.base_url}/trips/{trip_id}/timeline", headers=self._headers(token))
        except Exception as e:
            print(f"[TripCanvas] 获取时间线失败: {e}")
            return None

    def sync_trip(self, trip_id: int, user_id: int,
                  username: str | None = None, password: str | None = None) -> MemoryTrip | None:
        """从TripCanvas同步行程到记忆系统（仅限已定稿行程）。

        username/password 提供时，使用绑定账号访问 TripCanvas（优先于服务账号）。
        """
        token = None
        if username and password:
            token = self.login_user(username, password)
            if not token:
                raise ValueError("TripCanvas 账号登录失败，请检查绑定的账号和密码")
        elif username:
            raise ValueError("TripCanvas 账号未配置密码，请在个人中心重新绑定")

        trip_data = self.get_trip(trip_id, token)
        timeline_data = self.get_timeline(trip_id, token)

        if trip_data is None or timeline_data is None:
            if username:
                raise ValueError(
                    f"无法读取该行程：请确认行程已定稿，且归属于你绑定的 TripCanvas 账号「{username}」"
                )
            raise ValueError(
                "无法读取该行程：服务账号无权访问该行程。"
                "请在「个人中心 → TripCanvas 账号绑定」中绑定行程所属的 TripCanvas 账号"
            )

        # 仅允许同步已定稿的行程
        if trip_data.get("status") != "finalized":
            raise ValueError("该行程尚未定稿，请先在途迹（TripCanvas）中完成「行程定稿」后再同步")

        db = SessionLocal()
        try:
            memory_trip = db.query(MemoryTrip).filter(
                MemoryTrip.tripcanvas_trip_id == trip_id,
                MemoryTrip.user_id == user_id,
            ).first()

            if not memory_trip:
                memory_trip = MemoryTrip(
                    user_id=user_id,
                    tripcanvas_trip_id=trip_id,
                )
                db.add(memory_trip)

            memory_trip.title = trip_data.get("title", "")
            memory_trip.dest_city = trip_data.get("dest_city")
            memory_trip.total_days = trip_data.get("total_days", 1)
            memory_trip.depart_date = trip_data.get("depart_date")
            memory_trip.return_date = trip_data.get("return_date")
            memory_trip.status = "completed"

            db.flush()  # 分配自增ID并校验必填字段，供后续节点引用

            # 重新同步：先解除照片与旧节点的关联（保留照片记录），再删除旧节点重建
            db.query(MemoryPhoto).filter(MemoryPhoto.trip_id == memory_trip.id).update({
                "node_id": None,
                "match_status": "unmatched",
                "is_cover": 0,
                "match_score": 0,
            })
            db.query(MemoryNode).filter(MemoryNode.trip_id == memory_trip.id).delete()

            sort_order = 0
            for day in timeline_data.get("days", []):
                day_no = day.get("day_no", 1)
                city = day.get("city")
                weather = day.get("weather", {})
                for node in day.get("nodes", []):
                    # TripCanvas timeline 的节点坐标在关联 poi 对象中（NodeOut 无 lat/lng 字段）
                    poi = node.get("poi") or {}
                    memory_node = MemoryNode(
                        trip_id=memory_trip.id,
                        day_no=day_no,
                        sort_order=sort_order,
                        city=city or node.get("city"),
                        name=node.get("name", ""),
                        node_type=node.get("node_type"),
                        address=node.get("address") or poi.get("address"),
                        lat=node.get("lat") or poi.get("lat"),
                        lng=node.get("lng") or poi.get("lng"),
                        start_time=node.get("start_time"),
                        end_time=node.get("end_time"),
                        duration_minutes=node.get("duration_minutes", 0),
                        weather=weather.get("description") if isinstance(weather, dict) else None,
                        temperature=weather.get("temperature") if isinstance(weather, dict) else None,
                    )
                    db.add(memory_node)
                    sort_order += 1

            db.commit()
            db.refresh(memory_trip)
            return memory_trip
        except Exception as e:
            db.rollback()
            print(f"[TripCanvas] 同步行程失败: {e}")
            return None
        finally:
            db.close()


tripcanvas_client = TripCanvasClient()
