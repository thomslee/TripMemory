# -*- coding: utf-8 -*-
from .auth import router as auth_router
from .memory import router as memory_router
from .baidunet import router as baidunet_router

__all__ = ["auth_router", "memory_router", "baidunet_router"]
