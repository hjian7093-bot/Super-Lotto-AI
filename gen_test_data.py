"""生成大乐透测试数据，用于验证算法和前端"""
import json
import os
import random
from datetime import datetime, timedelta

random.seed(42)  # 固定随机种子，保证可复现

# 生成100期历史数据
data = []
base_date = datetime(2026, 10, 11)  # 最近一期日期
draw_weekdays = [0, 2, 5]  # 周一、三、六

current_date = base_date
period = 26109

for i in range(100):
    # 找一个开奖日
    while current_date.weekday() not in draw_weekdays:
        current_date -= timedelta(days=1)
    
    front = sorted(random.sample(range(1, 36), 5))
    back = sorted(random.sample(range(1, 13), 2))
    
    data.append({
        "period": str(period - i),
        "date": current_date.strftime("%Y-%m-%d"),
        "front_balls": [f"{n:02d}" for n in front],
        "back_balls": [f"{n:02d}" for n in back]
    })
    
    current_date -= timedelta(days=1)

# 按期号降序排列（已经是降序）
# 计算下一期信息
latest = data[0]
last_draw_date = datetime.strptime(latest["date"], "%Y-%m-%d")
next_date = last_draw_date + timedelta(days=1)
while next_date.weekday() not in draw_weekdays:
    next_date += timedelta(days=1)

next_period = str(int(latest["period"]) + 1)
weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

formatted = {
    "last_updated": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "data": data,
    "next_draw": {
        "next_period": next_period,
        "next_date": next_date.strftime("%Y-%m-%d"),
        "next_date_display": next_date.strftime("%Y年%m月%d日"),
        "weekday": weekday_names[next_date.weekday()],
        "draw_time": "21:25"
    }
}

# 保存到 data/lottery_history.json
output_path = os.path.join(os.path.dirname(__file__), "data", "lottery_history.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(formatted, f, ensure_ascii=False, indent=2)

print(f"已生成 {len(data)} 期测试数据")
print(f"最新期号: {latest['period']}, 日期: {latest['date']}")
print(f"最新开奖: 前区 {latest['front_balls']} + 后区 {latest['back_balls']}")
print(f"下一期: {next_period}期, {next_date.strftime('%Y-%m-%d')} {weekday_names[next_date.weekday()]}")
