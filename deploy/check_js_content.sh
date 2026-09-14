#!/bin/bash
F=/var/www/tripmemory/current/assets/MemoryDetail-DfPILn2R.js
echo "===== 文件信息 ====="
ls -la $F
echo "===== 搜 upload / 上传 / photo ====="
echo "upload 出现: $(grep -o 'upload' $F | wc -l) 次"
echo "上传照片 出现: $(grep -o '上传照片' $F | wc -l) 次"
echo "photos/upload 出现: $(grep -o 'photos/upload' $F | wc -l) 次"
echo "===== 前后 200 字符上下文 ====="
grep -o '.\{80\}upload.\{80\}' $F | head -3
