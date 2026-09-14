#!/bin/bash
echo "===== 大同行程照片记录 ====="
docker exec news-mysql mysql -uroot -p123456 -e "SELECT p.id, p.filename, p.file_path, p.taken_time, p.match_status, p.match_score, p.file_size FROM trip_memory.memory_photos p JOIN trip_memory.memory_trips t ON p.trip_id=t.id WHERE t.title LIKE '%大同%' ORDER BY p.id;" 2>/dev/null
echo ""
echo "===== 行程3 节点时间（匹配用） ====="
docker exec news-mysql mysql -uroot -p123456 -e "SELECT id, day_no, name, start_time, lat, lng FROM trip_memory.memory_nodes WHERE trip_id=3 ORDER BY day_no, sort_order;" 2>/dev/null
echo ""
echo "===== 后端最近日志（上传/匹配） ====="
docker logs trip-memory-backend --tail 80 2>&1 | grep -E "POST|PUT|GET /api/memory/trips/3" | tail -20
