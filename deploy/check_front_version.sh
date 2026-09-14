#!/bin/bash
echo "===== 服务器前端版本检查 ====="
ls /var/www/tripmemory/current/assets/MemoryDetail-*.js
echo ""
echo "===== 是否含 uploadPhotos / 上传逻辑 ====="
grep -l "photos/upload" /var/www/tripmemory/current/assets/MemoryDetail-*.js && echo "新版（含上传接口）" || echo "旧版！不含上传接口"
echo ""
echo "===== index.html 引用的 JS ====="
grep -o 'assets/[^"]*\.js' /var/www/tripmemory/current/index.html
