# -*- coding: utf-8 -*-
from .auth import router as auth_router
from .memory import router as memory_router
from .settings import router as settings_router
from .admin import router as admin_router

__all__ = ["auth_router", "memory_router", "settings_router", "admin_router"]
