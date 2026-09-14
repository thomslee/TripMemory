#!/bin/bash
echo "===== 后端日志：DELETE 请求 ====="
docker logs trip-memory-backend --since 3h 2>&1 | grep -iE "DELETE|delete|删除" | tail -15
echo ""
echo "===== 后端错误日志 ====="
docker logs trip-memory-backend --since 3h 2>&1 | grep -iE "error|traceback|exception|500" | tail -10
echo ""
echo "===== nginx 错误（delete 相关） ====="
sudo tail -100 /var/log/nginx/error.log 2>/dev/null | grep -i "trips/.*/photos" | tail -5
