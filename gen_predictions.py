"""生成前端用的 ai_predictions.json 格式数据"""
import json
import os
from datetime import datetime
from prediction_rules import build_prediction_plan

# 加载历史数据
data_path = os.path.join(os.path.dirname(__file__), "data", "lottery_history.json")
with open(data_path, "r", encoding="utf-8") as f:
    history_data = json.load(f)

# 生成预测方案
plan = build_prediction_plan(history_data["data"])
sources = plan["sources"]
options = plan["options"]

# 构造前端期望的格式
# 用一个模型作为示例
predictions = []
for group_id_str, group_options in options.items():
    for opt in group_options:
        predictions.append({
            "group_id": opt["group_id"],
            "strategy": opt["strategy"],
            "front_balls": opt["front_balls"],
            "back_balls": opt["back_balls"],
            "description": opt["description"]
        })

# 多模型格式（复制一份作为第二个模型）
def make_model(model_id, model_name, multiplier=1.0):
    # 简单变换一下，让不同模型有差异
    model_predictions = []
    for p in predictions:
        new_p = dict(p)
        # 随机调整后区作为不同模型的差异
        import random
        random.seed(hash(model_id) % 1000)
        new_back = sorted(random.sample([f"{i:02d}" for i in range(1, 13)], 2))
        new_p["back_balls"] = new_back
        model_predictions.append(new_p)
    return {
        "model_id": model_id,
        "model_name": model_name,
        "predictions": model_predictions
    }

ai_predictions = {
    "prediction_date": datetime.now().strftime("%Y-%m-%d"),
    "target_period": history_data["next_draw"]["next_period"],
    "models": [
        make_model("gpt5", "GPT-5"),
        make_model("claude45", "Claude 4.5"),
        make_model("gemini25", "Gemini 2.5 Pro"),
        make_model("deepseek-r1", "DeepSeek R1"),
    ]
}

output_path = os.path.join(os.path.dirname(__file__), "data", "ai_predictions.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(ai_predictions, f, ensure_ascii=False, indent=2)

print(f"已生成预测数据: {len(ai_predictions['models'])} 个模型")
print(f"目标期号: {ai_predictions['target_period']}")
print(f"每期预测组数: {len(ai_predictions['models'][0]['predictions'])}")
