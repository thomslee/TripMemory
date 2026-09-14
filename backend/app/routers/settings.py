# -*- coding: utf-8 -*-
"""应用设置路由：大模型 API 等外部接口配置（key-value 存储，敏感字段脱敏）。

模仿 TripCanvas：仅管理员可读写；API Key 返回脱敏值（••••••••），
更新时传空字符串表示清除，传 None 表示不修改。
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AppSetting
from ..routers.auth import require_admin

router = APIRouter(prefix="/api/settings", tags=["settings"])

# 允许配置的 key 白名单（对应各外部接口）
ALLOWED_KEYS = {"llm_base_url", "llm_api_key", "llm_model", "tts_voice"}
# 需要脱敏输出的 key（api_key 类）
SENSITIVE_KEYS = {"llm_api_key"}
MASK = "••••••••"

DEFAULTS = {
    "llm_base_url": "",
    "llm_api_key": "",
    "llm_model": "",
    "tts_voice": "xiaoxiao",
}


class SettingOut(BaseModel):
    """设置项输出：敏感字段（api_key）脱敏显示。"""
    llm_base_url: str = ""
    llm_api_key: str = ""  # 有值显示 "••••••••"，无值显示 ""
    llm_model: str = ""
    tts_voice: str = "xiaoxiao"


class SettingUpdate(BaseModel):
    """设置更新：传空字符串表示清除；传 None 表示不修改该字段。"""
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    tts_voice: str | None = None


def _get_all(db: Session) -> dict:
    """读取全部设置，缺失的 key 用默认值补齐。"""
    result = dict(DEFAULTS)
    rows = db.query(AppSetting).filter(AppSetting.skey.in_(ALLOWED_KEYS)).all()
    for r in rows:
        result[r.skey] = r.svalue or ""
    return result


def _mask(data: dict) -> dict:
    """敏感字段脱敏。"""
    for k in SENSITIVE_KEYS:
        if data.get(k):
            data[k] = MASK
    return data


@router.get("", response_model=SettingOut)
def get_settings(db: Session = Depends(get_db), _admin=Depends(require_admin)):
    """读取全部设置（敏感字段脱敏）。仅管理员。"""
    return SettingOut(**_mask(_get_all(db)))


@router.put("", response_model=SettingOut)
def update_settings(payload: SettingUpdate, db: Session = Depends(get_db),
                    _admin=Depends(require_admin)):
    """批量更新设置；传 None 不修改，传空字符串清除。仅管理员。"""
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    for key, value in updates.items():
        if key not in ALLOWED_KEYS:
            continue
        row = db.get(AppSetting, key)
        if row:
            row.svalue = value
        else:
            db.add(AppSetting(skey=key, svalue=value))
    db.commit()
    return SettingOut(**_mask(_get_all(db)))


def get_setting_value(db: Session, key: str) -> str:
    """读取单个设置的真实值（供后端内部调用，不脱敏）。"""
    if key not in ALLOWED_KEYS:
        return ""
    row = db.get(AppSetting, key)
    return row.svalue if row and row.svalue else DEFAULTS.get(key, "")
