# -*- coding: utf-8 -*-
"""凭据加解密工具：用于加密存储用户绑定的 TripCanvas 账号密码。

使用应用 SECRET_KEY 派生 Fernet 密钥，可逆加密。即使数据库泄露，
绑定的第三方账号密码也无法直接明文读取。
"""
import base64
import hashlib

from cryptography.fernet import Fernet

from ..config import settings


def _fernet() -> Fernet:
    """从 SECRET_KEY 派生稳定的 32 字节密钥。"""
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_password(plain: str | None) -> str | None:
    """加密明文密码；None 原样返回。"""
    if not plain:
        return None
    return _fernet().encrypt(plain.encode("utf-8")).decode()


def decrypt_password(cipher: str | None) -> str | None:
    """解密密文密码；None 或解密失败返回 None。"""
    if not cipher:
        return None
    try:
        return _fernet().decrypt(cipher.encode("utf-8")).decode("utf-8")
    except Exception:
        return None
