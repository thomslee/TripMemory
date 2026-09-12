# -*- coding: utf-8 -*-
"""百度网盘API对接服务：获取照片列表、EXIF信息、同步照片到记忆行程。"""
import urllib.parse
import urllib.request
import json
from datetime import datetime
from ..config import settings
from ..models import MemoryPhoto, MemoryTrip
from ..database import SessionLocal


class BaiduNetClient:
    """百度网盘开放平台API客户端。"""

    def __init__(self):
        self.app_key = settings.BAIDUNET_APP_KEY
        self.secret_key = settings.BAIDUNET_SECRET_KEY
        self.redirect_uri = settings.BAIDUNET_REDIRECT_URI or "oob"
        self.base_url = "https://pan.baidu.com/rest/2.0"
        self.open_url = "https://openapi.baidu.com"

    def _http_get(self, url, params=None):
        """发送GET请求。"""
        if params:
            url = url + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)

    def get_auth_url(self, state: str = "") -> str:
        """获取授权URL。"""
        params = {
            "response_type": "code",
            "client_id": self.app_key,
            "redirect_uri": self.redirect_uri,
            "scope": "basic,netdisk",
            "display": "page",
            "state": state,
        }
        return f"{self.open_url}/oauth/2.0/authorize?{urllib.parse.urlencode(params)}"

    def get_access_token(self, code: str) -> dict | None:
        """用授权码换取access_token。"""
        try:
            params = {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self.app_key,
                "client_secret": self.secret_key,
                "redirect_uri": self.redirect_uri,
            }
            return self._http_get(f"{self.open_url}/oauth/2.0/token", params)
        except Exception as e:
            print(f"[BaiduNet] 获取token失败: {e}")
            return None

    def refresh_token(self, refresh_token: str) -> dict | None:
        """刷新access_token。"""
        try:
            params = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.app_key,
                "client_secret": self.secret_key,
            }
            return self._http_get(f"{self.open_url}/oauth/2.0/token", params)
        except Exception as e:
            print(f"[BaiduNet] 刷新token失败: {e}")
            return None

    def get_user_info(self, access_token: str) -> dict | None:
        """获取用户信息。"""
        try:
            params = {
                "method": "uinfo",
                "access_token": access_token,
            }
            return self._http_get(f"{self.base_url}/xpan/nas", params)
        except Exception as e:
            print(f"[BaiduNet] 获取用户信息失败: {e}")
            return None

    def list_files(self, access_token: str, dir: str = "/", start: int = 0, limit: int = 100) -> list[dict]:
        """获取指定目录下的文件列表。"""
        try:
            params = {
                "method": "list",
                "access_token": access_token,
                "dir": dir,
                "web": "web",
                "start": start,
                "limit": limit,
            }
            result = self._http_get(f"{self.base_url}/xpan/file", params)
            return result.get("list", [])
        except Exception as e:
            print(f"[BaiduNet] 获取文件列表失败: {e}")
            return []

    def list_all_files(self, access_token: str, dir: str = "/") -> list[dict]:
        """获取目录下所有文件（分页）。"""
        all_files = []
        start = 0
        limit = 100
        while True:
            files = self.list_files(access_token, dir, start, limit)
            if not files:
                break
            all_files.extend(files)
            if len(files) < limit:
                break
            start += limit
        return all_files

    def get_file_metadata(self, access_token: str, fs_ids: list[int]) -> list[dict]:
        """批量获取文件元数据（含拍摄时间date_taken）。"""
        try:
            if not fs_ids:
                return []
            # 百度网盘一次最多支持多少个fs_id，分批处理
            batch_size = 50
            all_metas = []
            for i in range(0, len(fs_ids), batch_size):
                batch = fs_ids[i:i + batch_size]
                fs_ids_str = ",".join(str(fid) for fid in batch)
                params = {
                    "method": "filemetas",
                    "access_token": access_token,
                    "fsids": f"[{fs_ids_str}]",
                    "dlink": 1,
                    "extra": 1,
                }
                result = self._http_get(f"{self.base_url}/xpan/multimedia", params)
                all_metas.extend(result.get("list", []))
            return all_metas
        except Exception as e:
            print(f"[BaiduNet] 获取文件元数据失败: {e}")
            return []

    def search_files(self, access_token: str, key: str, dir: str = "/", num: int = 50) -> list[dict]:
        """搜索文件。"""
        try:
            params = {
                "method": "search",
                "access_token": access_token,
                "key": key,
                "dir": dir,
                "web": "web",
                "num": num,
                "page": 1,
            }
            result = self._http_get(f"{self.base_url}/xpan/file", params)
            return result.get("list", [])
        except Exception as e:
            print(f"[BaiduNet] 搜索文件失败: {e}")
            return []

    def fetch_photo_bytes(self, access_token: str, fs_id: str | None, file_path: str | None) -> tuple[bytes | None, str | None]:
        """拉取单张照片原始字节（代理展示用）。

        通过 filemetas 获取最新 dlink，追加 access_token 后下载。
        返回 (bytes, content_type)；失败返回 (None, None)。
        """
        try:
            if not fs_id:
                return None, None
            metas = self.get_file_metadata(access_token, [int(fs_id)])
            if not metas:
                return None, None
            dlink = metas[0].get("dlink")
            if not dlink:
                return None, None
            sep = "&" if "?" in dlink else "?"
            url = f"{dlink}{sep}access_token={access_token}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
                content_type = resp.headers.get("Content-Type")
            return data, content_type
        except Exception as e:
            print(f"[BaiduNet] 拉取照片失败: {e}")
            return None, None

    def get_photos_in_folder(self, access_token: str, folder_path: str) -> list[dict]:
        """
        获取指定文件夹中的所有照片（含元数据）。
        递归获取子文件夹中的照片。
        """
        photos = []
        image_exts = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic")

        def _scan_dir(dir_path):
            files = self.list_all_files(access_token, dir_path)
            fs_ids = []
            file_map = {}
            for f in files:
                if f.get("isdir") == 1:
                    # 递归子目录
                    _scan_dir(f.get("path", ""))
                else:
                    filename = f.get("server_filename", "").lower()
                    if filename.endswith(image_exts):
                        fs_ids.append(f["fs_id"])
                        file_map[f["fs_id"]] = f
            # 批量获取元数据
            if fs_ids:
                metas = self.get_file_metadata(access_token, fs_ids)
                for meta in metas:
                    fs_id = meta.get("fs_id")
                    if fs_id in file_map:
                        f = file_map[fs_id]
                        photo = {
                            "fs_id": fs_id,
                            "filename": meta.get("filename") or f.get("server_filename"),
                            "path": meta.get("path") or f.get("path"),
                            "size": meta.get("size", f.get("size", 0)),
                            "width": meta.get("width"),
                            "height": meta.get("height"),
                            "date_taken": meta.get("date_taken"),
                            "orientation": meta.get("orientation"),
                            "category": meta.get("category"),
                            "dlink": meta.get("dlink"),
                            "md5": meta.get("md5"),
                        }
                        photos.append(photo)

        _scan_dir(folder_path)
        # 按拍摄时间排序
        photos.sort(key=lambda p: p.get("date_taken") or "")
        return photos

    def sync_photos_to_trip(self, access_token: str, trip_id: int, folder_path: str) -> dict:
        """
        将百度网盘文件夹中的照片同步到指定记忆行程。
        """
        db = SessionLocal()
        try:
            trip = db.query(MemoryTrip).filter(MemoryTrip.id == trip_id).first()
            if not trip:
                return {"error": "行程不存在"}

            # 获取照片
            photos = self.get_photos_in_folder(access_token, folder_path)
            if not photos:
                return {"synced": 0, "message": "文件夹中没有照片"}

            # 记录已存在的fs_id，避免重复
            existing = db.query(MemoryPhoto).filter(
                MemoryPhoto.trip_id == trip_id,
                MemoryPhoto.baidunet_file_id.isnot(None),
            ).all()
            existing_ids = {p.baidunet_file_id for p in existing}

            synced = 0
            for photo in photos:
                fs_id_str = str(photo["fs_id"])
                if fs_id_str in existing_ids:
                    continue

                # 解析拍摄时间
                taken_time = None
                if photo.get("date_taken"):
                    try:
                        # date_taken格式可能是时间戳或日期字符串
                        if isinstance(photo["date_taken"], (int, float)):
                            taken_time = datetime.fromtimestamp(photo["date_taken"])
                        else:
                            taken_time = datetime.strptime(str(photo["date_taken"]), "%Y-%m-%d %H:%M:%S")
                    except (ValueError, TypeError):
                        pass

                memory_photo = MemoryPhoto(
                    trip_id=trip_id,
                    baidunet_file_id=fs_id_str,
                    filename=photo["filename"],
                    file_path=photo["path"],
                    file_size=photo["size"],
                    file_type="photo",
                    taken_time=taken_time,
                    match_status="unmatched",
                )
                db.add(memory_photo)
                synced += 1

            # 更新行程的百度网盘文件夹路径
            trip.baidunet_folder = folder_path
            db.commit()

            return {
                "synced": synced,
                "total": len(photos),
                "skipped": len(photos) - synced,
                "message": f"同步完成：新增{synced}张，跳过{len(photos) - synced}张已存在的照片",
            }
        except Exception as e:
            db.rollback()
            print(f"[BaiduNet] 同步照片失败: {e}")
            return {"error": str(e)}
        finally:
            db.close()


baidunet_client = BaiduNetClient()
