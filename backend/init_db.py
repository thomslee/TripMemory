# -*- coding: utf-8 -*-
"""初始化数据库：创建库和表。"""
import pymysql
from app.config import settings
from app.database import engine, Base
from app.models import User, MemoryTrip, MemoryNode, MemoryPhoto  # noqa: F401


def init_database():
    # 创建数据库
    conn = pymysql.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        charset="utf8mb4",
    )
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {settings.DB_NAME} DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cursor.close()
    conn.close()
    print(f"数据库 {settings.DB_NAME} 已创建")

    # 创建表
    Base.metadata.create_all(bind=engine)
    print("数据表已创建")


if __name__ == "__main__":
    init_database()
