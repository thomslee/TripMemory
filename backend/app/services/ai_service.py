# -*- coding: utf-8 -*-
"""AI大模型服务：生成游记文字、配音、背景音乐推荐。"""
import urllib.request
import json
from ..config import settings
from ..database import SessionLocal
from ..models import AppSetting


def _load_llm_config() -> dict:
    """读取大模型配置：数据库设置优先，环境变量兜底。"""
    rows = {}
    try:
        db = SessionLocal()
        try:
            result = db.query(AppSetting).filter(
                AppSetting.skey.in_(["llm_base_url", "llm_api_key", "llm_model"])
            ).all()
            rows = {r.skey: (r.svalue or "") for r in result}
        finally:
            db.close()
    except Exception:
        pass
    return {
        "base_url": (rows.get("llm_base_url") or settings.LLM_BASE_URL).rstrip("/"),
        "api_key": rows.get("llm_api_key") or settings.LLM_API_KEY,
        "model": rows.get("llm_model") or settings.LLM_MODEL,
    }


def _http_post(url, data, headers=None, timeout=60):
    """发送POST请求。"""
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"))
    req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


class AIService:
    """AI大模型服务。"""

    def _cfg(self):
        return _load_llm_config()

    def generate_article(
        self,
        node_name: str,
        node_type: str,
        city: str,
        weather: str,
        user_note: str = "",
        photo_count: int = 0,
    ) -> str:
        """生成单个节点的游记文字。"""
        cfg = self._cfg()
        base_url, api_key, model = cfg["base_url"], cfg["api_key"], cfg["model"]
        if not api_key:
            return ""

        type_names = {
            "hotel": "酒店",
            "attraction": "景点",
            "restaurant": "餐厅",
            "station": "交通枢纽",
        }
        type_name = type_names.get(node_type, "地点")

        prompt = f"""请为我写一段旅游游记，关于在{city}的{node_name}（{type_name}）。

要求：
1. 字数200-300字，第一人称，有感染力
2. 结合当天天气：{weather or '未知'}
3. 描述这个{type_name}的特色和游玩体验
4. 加入一些个人感受和细节描写
5. 语言优美，适合配音朗读
6. 不要使用markdown格式，直接输出正文

"""
        if user_note:
            prompt += f"用户备注：{user_note}\n"
        if photo_count > 0:
            prompt += f"此处有{photo_count}张照片，可以适当提及拍照的体验。\n"

        try:
            resp = _http_post(
                f"{base_url}/chat/completions",
                {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "你是一位专业的旅游作家，擅长写优美、有感染力的游记。"},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.8,
                    "max_tokens": 500,
                },
                headers={"Authorization": f"Bearer {api_key}"},
            )
            return resp["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[AI] 生成游记失败: {e}")
            return ""

    def generate_trip_summary(
        self,
        trip_title: str,
        cities: list[str],
        days: int,
        highlights: list[str],
    ) -> str:
        """生成整个行程的总结性文字。"""
        cfg = self._cfg()
        base_url, api_key, model = cfg["base_url"], cfg["api_key"], cfg["model"]
        if not api_key:
            return ""

        prompt = f"""请为这次旅行写一段开篇引言：

行程：{trip_title}
城市：{'、'.join(cities)}
天数：{days}天
亮点：{'、'.join(highlights[:5])}

要求：
1. 字数150-200字，有诗意和感染力
2. 引出这次旅行的主题和期待
3. 语言优美，适合配音朗读
4. 不要使用markdown格式，直接输出正文
"""
        try:
            resp = _http_post(
                f"{base_url}/chat/completions",
                {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "你是一位专业的旅游作家，擅长写优美、有诗意的旅行开篇。"},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.8,
                    "max_tokens": 300,
                },
                headers={"Authorization": f"Bearer {api_key}"},
            )
            return resp["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[AI] 生成总结失败: {e}")
            return ""


ai_service = AIService()
