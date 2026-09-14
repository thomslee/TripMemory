# -*- coding: utf-8 -*-
"""本地单测：模拟大同行程验证新匹配算法（日期维度 + 并列取时间差最小）。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, date
from types import SimpleNamespace as NS
from app.services.photo_matcher import _photo_day, _time_score, _time_diff_minutes

# ---- 模拟大同行程节点（同服务器数据） ----
nodes = [
    NS(id=40, day_no=1, name="悬空寺", start_time="10:00", lat="39.661139", lng="113.715781"),
    NS(id=41, day_no=1, name="浑源古城", start_time="12:00", lat="39.6993950", lng="113.6927640"),
    NS(id=42, day_no=1, name="应县木塔", start_time="14:59", lat="39.5664650", lng="113.1888310"),
    NS(id=43, day_no=1, name="星程酒店", start_time="19:03", lat="40.0950540", lng="113.2890340"),
    NS(id=44, day_no=2, name="星程酒店", start_time="08:00", lat="40.0950540", lng="113.2890340"),
    NS(id=45, day_no=2, name="云冈石窟", start_time="09:04", lat="40.1131570", lng="113.1377630"),
    NS(id=46, day_no=2, name="喜晋道面馆", start_time="13:48", lat="40.0925290", lng="113.2996290"),
    NS(id=47, day_no=2, name="华严寺", start_time="15:24", lat="40.0925310", lng="113.2950600"),
    NS(id=48, day_no=2, name="星程酒店", start_time="17:03", lat="40.0950540", lng="113.2890340"),
    NS(id=49, day_no=3, name="星程酒店", start_time="08:00", lat="40.0950540", lng="113.2890340"),
    NS(id=50, day_no=3, name="善化古寺", start_time="08:50", lat="40.0870410", lng="113.3003350"),
    NS(id=51, day_no=3, name="星程酒店", start_time="11:00", lat="40.095054", lng="113.289034"),
]
depart = date(2026, 6, 10)

def pick(photo_dt):
    """按新算法（无 GPS 时间兜底）选节点：同天候选 + 分数高 + 已到优先 + 时间差最小"""
    day = _photo_day(photo_dt, depart)
    day_nodes = [n for n in nodes if n.day_no == day] if day else nodes
    ranked = []
    for node in day_nodes:
        ts = _time_score(photo_dt, node)
        if ts <= 0:
            continue
        diff = _time_diff_minutes(photo_dt, node)
        # 节点 start_time 与照片拼成 datetime 判断是否已到
        from datetime import datetime as _dt
        node_dt = _dt.strptime(f"{photo_dt.strftime('%Y-%m-%d')} {node.start_time}", "%Y-%m-%d %H:%M")
        after = 0 if photo_dt >= node_dt else 1
        ranked.append((ts, after, -diff, node.name))
    ranked.sort(key=lambda x: (-x[0], x[1], -x[2]))
    return day, ranked[0][3] if ranked else None

cases = [
    ("06-10 10:14", datetime(2026,6,10,10,14,45), "悬空寺"),
    ("06-10 12:16", datetime(2026,6,10,12,16,53), "浑源古城"),
    ("06-10 14:34", datetime(2026,6,10,14,34,9), "应县木塔"),
    ("06-10 15:38", datetime(2026,6,10,15,38,49), "应县木塔"),
    ("06-11 09:49", datetime(2026,6,11,9,49,29), "云冈石窟"),
    ("06-11 10:38", datetime(2026,6,11,10,38,2), "云冈石窟"),
    ("06-11 16:08", datetime(2026,6,11,16,8,36), "华严寺"),
    ("06-11 17:10", datetime(2026,6,11,17,10,22), "星程酒店"),
    ("06-12 09:16", datetime(2026,6,12,9,16,48), "善化古寺"),
    ("06-12 10:02", datetime(2026,6,12,10,2,2), "善化古寺"),
]
ok = 0
for label, dt, expect in cases:
    day, got = pick(dt)
    mark = "PASS" if got == expect else "FAIL"
    if got == expect:
        ok += 1
    print(f"{mark}  {label} day{day} -> {got} (期望 {expect})")
print(f"\n{ok}/{len(cases)} 通过")
