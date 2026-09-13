#!/bin/bash
# TripMemory 旅游记忆系统部署脚本（腾讯云 62.234.121.63，与 TripCanvas 共用服务器）
# 用法: bash deploy.sh
set -e

APP_DIR=~/tripmemory
WEB_DIR=/var/www/tripmemory
DB_PASSWORD="${DB_PASSWORD:-123456}"

echo "=== 0. 环境检查 ==="
command -v docker >/dev/null || { echo "缺少 docker"; exit 1; }

echo "=== 1. 准备目录 ==="
mkdir -p "$APP_DIR" "$WEB_DIR"
# 后端代码（部署脚本运行时应在项目根目录）
rsync -a --exclude '.venv' --exclude '__pycache__' --exclude 'static/audio/*' --exclude 'static/bgm/*' --exclude 'static/sample-photos/*' \
  backend/ "$APP_DIR/backend/"
cp docker-compose.yml "$APP_DIR/"
# 配置文件
if [ ! -f "$APP_DIR/.env" ]; then
  cp deploy/.env.production "$APP_DIR/.env"
  echo "已生成 .env，请检查其中的密钥配置"
fi

echo "=== 2. 构建后端镜像（国内镜像源加速） ==="
cd "$APP_DIR"
docker compose build backend

echo "=== 3. 创建数据库（如不存在，复用 news-mysql） ==="
docker exec news-mysql mysql -uroot -p"$DB_PASSWORD" -e \
  "CREATE DATABASE IF NOT EXISTS trip_memory CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

echo "=== 4. 启动后端 ==="
docker compose up -d backend

echo "=== 5. 等待并健康检查 ==="
sleep 4
docker ps --format '{{.Names}} {{.Status}}' | grep trip-memory-backend
curl -s http://127.0.0.1:8003/api/health && echo "" || echo "警告：健康检查失败"

echo "=== 6. 部署前端 ==="
# 本地构建产物通过 scp 上传（在本地执行: scp -r frontend/dist/* ubuntu@62.234.121.63:/var/www/tripmemory/current/）
# 或服务器上已有构建产物则直接解压
if [ -d "frontend/dist" ]; then
  rsync -a --delete frontend/dist/ "$WEB_DIR/current/"
fi

echo "=== 7. nginx 配置 ==="
sudo cp deploy/tripmemory-nginx.conf /etc/nginx/conf.d/tripmemory.conf 2>/dev/null || cp deploy/tripmemory-nginx.conf /etc/nginx/conf.d/tripmemory.conf
sudo nginx -t && sudo nginx -s reload || echo "nginx 未安装或配置失败，请手动处理"

echo ""
echo "=== 部署完成 ==="
echo "前端: http://62.234.121.63:8082"
echo "后端: http://127.0.0.1:8003"
echo ""
echo "注意："
echo "1. TripCanvas 需先部署并运行在 127.0.0.1:8002（backend 通过 localhost 访问）"
echo "2. 确保 trip_canvas 中存在已定稿行程，且服务账号可访问"
echo "3. 百度网盘授权使用 oob 模式（.env 中 BAIDUNET_REDIRECT_URI=oob），无需配置回调地址"
