# -*- coding: utf-8 -*-
"""AI大模型服务：生成游记文字、配音、背景音乐推荐。"""
import urllib.request
import json
from ..config import settings
from ..database import SessionLocal
from ..models import AppSetting


TRAVEL_TYPE_NAMES = {
    "solo": "单人游",
    "companion": "结伴游",
    "family": "家庭游",
}


def _format_persona(profile: dict | None) -> str:
    """把用户画像格式化为中文描述；无有效信息返回空串。"""
    if not profile:
        return ""
    parts = []
    age = profile.get("age")
    gender = profile.get("gender")
    identity = profile.get("identity")
    prefs = profile.get("preferences") or []
    if age and gender:
        parts.append(f"{age}岁{gender}")
    elif age:
        parts.append(f"{age}岁")
    elif gender:
        parts.append(gender)
    if identity:
        parts.append(identity)
    if prefs:
        parts.append("兴趣：" + "、".join(prefs[:5]))
    return "、".join(parts) if parts else ""


def _format_travel_prefs(travel_prefs: dict | None) -> str:
    """把行程出行偏好格式化为中文描述；无有效信息返回空串。

    travel_type 缺失时按人数推断：1人→单人游；>=2人→结伴游
    （TripCanvas 旧版创建的行程可能未填出行类型）。
    """
    if not travel_prefs or not isinstance(travel_prefs, dict):
        return ""
    parts = []
    ttype = travel_prefs.get("travel_type")
    if ttype:
        parts.append(TRAVEL_TYPE_NAMES.get(ttype, ttype))
    else:
        travelers = travel_prefs.get("travelers")
        if travelers == 1:
            parts.append("单人游")  # 按人数推断：独自出行
        elif travelers and travelers >= 2:
            parts.append("结伴游")  # 按人数推断：结伴出行
    pace = travel_prefs.get("pace")
    if pace:
        pace_names = {"relaxed": "休闲", "balanced": "适中", "intense": "紧凑"}
        parts.append(pace_names.get(pace, pace) + "节奏")
    budget = travel_prefs.get("budget")
    if budget:
        budget_names = {"economy": "经济", "comfort": "舒适", "luxury": "奢华"}
        parts.append(budget_names.get(budget, budget) + "预算")
    travelers = travel_prefs.get("travelers")
    if travelers:
        parts.append(f"{travelers}人出行")
    requirements = travel_prefs.get("requirements")
    if requirements:
        parts.append("特别要求：" + str(requirements))
    return "；".join(parts) if parts else ""


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
        profile: dict | None = None,
        travel_prefs: dict | None = None,
        prev_node: dict | None = None,
        next_node: dict | None = None,
        day_sequence: list[str] | None = None,
    ) -> str:
        """生成单个节点的游记文字。

        除用户画像/出行偏好外，还可注入行程上下文（前后节点、当天路线），
        让游记承上启下（如"刚从悬空寺过来，来到应县木塔"）。
        """
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
        persona = _format_persona(profile)
        if persona:
            prompt += f"我的画像：{persona}。请以贴合我身份和兴趣的视角来写。\n"
        travel_desc = _format_travel_prefs(travel_prefs)
        if travel_desc:
            prompt += f"本次出行：{travel_desc}。请贴合本次出行的类型和节奏。\n"

        # 行程路线上下文：当天序列 + 上一站/下一站，让游记承上启下
        if day_sequence and len(day_sequence) > 1:
            prompt += "今天的行程路线：" + " → ".join(day_sequence) + "\n"
        if prev_node:
            prompt += f"你的上一站是{prev_node.get('name', '上一站')}，从那里一路来到{node_name}。\n"
        if next_node:
            prompt += f"游览完{node_name}后，你接着前往{next_node.get('name', '下一站')}。\n"
        if prev_node or next_node:
            prompt += (
                "请以承上启下的叙事方式写这篇游记："
                "开篇自然呼应你刚刚结束的上一站旅程，"
                "中间描写本站的所见所感，结尾可过渡到接下来的行程。\n"
            )

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
        profile: dict | None = None,
        travel_prefs: dict | None = None,
    ) -> str:
        """生成整个行程的总结性文字（可结合用户画像与出行偏好）。"""
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
        persona = _format_persona(profile)
        if persona:
            prompt += f"旅行者画像：{persona}。\n"
        travel_desc = _format_travel_prefs(travel_prefs)
        if travel_desc:
            prompt += f"本次出行：{travel_desc}。\n"
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
