"""大乐透确定性统计与候选组合生成模块。
前区：5个号码从01-35中选取；后区：2个号码从01-12中选取。
位置从最新一期开始计数（位置0）。当前遗漏即位置0，若从未开出则为历史长度下限。
已完成遗漏 = positions[i+1] - positions[i] - 1；mean_completed_omission 在 <2 次出现时为 None。
previous_omission 为最近一次完成的间隔，用于反弹/转折信号。

前区热度 = count5*5 + count10*3 + count30*2。趋势 = (count5/5 - count30/30)*100 + (count10/10 - count30/30)*50。
热度在最新一期命中后乘以 .5，遗漏>=3期后乘以 .7。
冷号分：遗漏 * (1, 1.5, .8) 对应间隔 5..10, 11..20, 其他；
反弹信号（前次间隔>15且当前遗漏<=2）取 max(基础分, 前次间隔)*1.4。
周期分：前次间隔>=3且当前遗漏<=1时加20。
综合分 = 热度minmax*.30 + 当前遗漏/最大遗漏*100*.25 + 平衡分*.20 + 趋势minmax*.25。
平衡分：count30在2..5之间为80，>5为50，否则60。

后区综合分 = count20 minmax*.30 + 当前遗漏/最大遗漏*100*.30
           + 100/(1+abs(当前遗漏-平均已完成间隔))*.20
           + 100/(1+距离(count20,2..4))*.20。

排名并列时按号码升序。候选池按字典序枚举，保留前8组合法的前区组合。
热度/周期策略从调整分Top8开始，冷号从Top12开始，综合从Top8开始，
平衡策略从count30=2..5的号码开始，按距3.5的距离排序，超出后按距区间距离扩展。
后区选号：
- 热号策略：在遗漏3..10中选count20最高的2个
- 冷号策略：在遗漏8..15中选遗漏最大的2个
- 平衡策略：选count20最接近3的2个
- 周期策略：选当前遗漏最接近平均已完成间隔的2个
- 综合策略：选综合分最高的2个

前区硬约束（不放宽）：
- 奇偶比 2:3 或 3:2
- 大小比（>=18为大）2:3 或 3:2
- 和值 60..120
- 三区（01-12, 13-24, 25-35）每区至少1个
"""
from datetime import date
from itertools import combinations
import json
import re

STRATEGIES = {
    1: "增强型热号追随者",
    2: "增强型冷号逆向者",
    3: "增强型平衡策略师",
    4: "增强型周期理论家",
    5: "增强型综合决策者",
}
OPTIONS_PER_GROUP = 8
FRONT_COUNT = 5       # 前区选5个
FRONT_MAX = 35        # 前区1-35
BACK_COUNT = 2        # 后区选2个
BACK_MAX = 12         # 后区1-12


def _integer(value, label, maximum):
    if type(value) is int:
        parsed = value
    elif isinstance(value, str) and re.fullmatch(r"[0-9]{1,2}", value):
        parsed = int(value)
    else:
        raise ValueError(f"{label} 必须为整数或数字字符串")
    if not 1 <= parsed <= maximum:
        raise ValueError(f"{label} 超出 1..{maximum}")
    return parsed


def _validated_history(history):
    if not isinstance(history, list) or len(history) < 30:
        raise ValueError("至少需要 30 期真实开奖数据")
    draws, periods = [], set()
    for entry in history:
        if not isinstance(entry, dict):
            raise ValueError("开奖记录必须为对象")
        period = entry.get("period")
        if type(period) is int and period > 0:
            period = str(period)
        if not isinstance(period, str) or not re.fullmatch(r"[0-9]+", period):
            raise ValueError("开奖期号必须为正整数或数字字符串")
        period = str(int(period))
        if int(period) <= 0 or period in periods:
            raise ValueError(f"开奖期号无效或重复: {period}")
        periods.add(period)
        try:
            draw_date = date.fromisoformat(entry["date"]).isoformat()
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"{period} 开奖日期无效") from exc
        fronts = entry.get("front_balls")
        if not isinstance(fronts, list) or len(fronts) != FRONT_COUNT:
            raise ValueError(f"{period} 必须有 {FRONT_COUNT} 个前区号码")
        fronts = sorted(_integer(ball, f"{period} 前区号", FRONT_MAX) for ball in fronts)
        if len(set(fronts)) != FRONT_COUNT:
            raise ValueError(f"{period} 前区号重复")
        backs = entry.get("back_balls")
        if not isinstance(backs, list) or len(backs) != BACK_COUNT:
            raise ValueError(f"{period} 必须有 {BACK_COUNT} 个后区号码")
        backs = sorted(_integer(ball, f"{period} 后区号", BACK_MAX) for ball in backs)
        if len(set(backs)) != BACK_COUNT:
            raise ValueError(f"{period} 后区号重复")
        draws.append({"period": period, "date": draw_date, "fronts": fronts, "backs": backs})
    draws.sort(key=lambda draw: int(draw["period"]), reverse=True)
    if any(draws[i]["date"] <= draws[i + 1]["date"] for i in range(len(draws) - 1)):
        raise ValueError("开奖期号与日期顺序不一致或日期重复")
    return draws


def _minmax(values):
    lo, hi = min(values.values()), max(values.values())
    return {ball: (50.0 if hi == lo else (value - lo) * 100 / (hi - lo))
            for ball, value in values.items()}


def _distance(value, low, high):
    return max(low - value, value - high, 0)


def _ball_stats(draws, color, maximum):
    stats = {}
    for number in range(1, maximum + 1):
        positions = [index for index, draw in enumerate(draws)
                     if (number in draw["fronts"] if color == "front" else number in draw["backs"])]
        gaps = [b - a - 1 for a, b in zip(positions, positions[1:])]
        stats[f"{number:02d}"] = {
            "counts": {str(window): sum(pos < window for pos in positions)
                       for window in (5, 10, 20, 30)},
            "current_omission": positions[0] if positions else len(draws),
            "omission_is_lower_bound": not positions,
            "previous_omission": gaps[0] if gaps else None,
            "mean_completed_omission": sum(gaps) / len(gaps) if gaps else None,
        }
    return stats


def _compute_stats(draws):
    front = _ball_stats(draws, "front", FRONT_MAX)
    back = _ball_stats(draws, "back", BACK_MAX)
    for stat in front.values():
        counts, omission, previous = stat["counts"], stat["current_omission"], stat["previous_omission"]
        stat["heat"] = counts["5"] * 5 + counts["10"] * 3 + counts["30"] * 2
        stat["trend"] = counts["5"] * 20 + counts["10"] * 5 - counts["30"] * 5
        stat["heat_score"] = stat["heat"] * (.5 if omission == 0 else .7 if omission >= 3 else 1)
        base = omission * (1 if 5 <= omission <= 10 else 1.5 if 11 <= omission <= 20 else .8)
        stat["cold_score"] = max(base, previous) * 1.4 if previous is not None and previous > 15 and omission <= 2 else base
        stat["cycle_score"] = stat["trend"] + (20 if previous is not None and previous >= 3 and omission <= 1 else 0)
        stat["balance_score"] = 80 if 2 <= counts["30"] <= 5 else 50 if counts["30"] > 5 else 60
    heat = _minmax({ball: stat["heat"] for ball, stat in front.items()})
    trend = _minmax({ball: stat["trend"] for ball, stat in front.items()})
    max_front_gap = max(stat["current_omission"] for stat in front.values())
    for ball, stat in front.items():
        stat["heat_normalized"] = heat[ball]
        stat["trend_normalized"] = trend[ball]
        stat["omission_normalized"] = stat["current_omission"] * 100 / max_front_gap if max_front_gap else 50.0
        stat["composite_score"] = heat[ball] * .30 + stat["omission_normalized"] * .25 + stat["balance_score"] * .20 + trend[ball] * .25
    frequencies = _minmax({ball: stat["counts"]["20"] for ball, stat in back.items()})
    max_back_gap = max(stat["current_omission"] for stat in back.values())
    for ball, stat in back.items():
        mean = stat["mean_completed_omission"]
        stat["frequency_score"] = frequencies[ball]
        stat["omission_score"] = stat["current_omission"] * 100 / max_back_gap if max_back_gap else 50.0
        stat["cycle_score"] = 100 / (1 + abs(stat["current_omission"] - mean)) if mean is not None else 0.0
        stat["balance_score"] = 100 / (1 + _distance(stat["counts"]["20"], 2, 4))
        stat["composite_score"] = stat["frequency_score"] * .30 + stat["omission_score"] * .30 + stat["cycle_score"] * .20 + stat["balance_score"] * .20
    odd_counts, big_counts = {}, {}
    for draw in draws[:30]:
        odd, big, _, _ = _shape(draw["fronts"])
        odd_counts[odd] = odd_counts.get(odd, 0) + 1
        big_counts[big] = big_counts.get(big, 0) + 1
    return {"front": front, "back": back, "shapes": {"odd_counts": odd_counts, "big_counts": big_counts}}


def _shape(fronts):
    odd = sum(ball % 2 for ball in fronts)
    big = sum(ball >= 18 for ball in fronts)  # 18以上为大
    zones = tuple(sum(low <= ball <= high for ball in fronts) for low, high in ((1, 12), (13, 24), (25, 35)))
    ordered = sorted(fronts)
    adjacent = sum(b - a == 1 for a, b in zip(ordered, ordered[1:]))
    return odd, big, zones, adjacent


def _rank(stats, field):
    return sorted(range(1, len(stats) + 1), key=lambda n: (-stats[f"{n:02d}"][field], n))


def _front_candidates(ranking, initial_size, predicate):
    """枚举前区候选，保留前 OPTIONS_PER_GROUP 组合法组合。"""
    found = []
    for size in range(max(initial_size, FRONT_COUNT), len(ranking) + 1):
        if size == max(initial_size, FRONT_COUNT):
            candidates = combinations(ranking[:size], FRONT_COUNT)
        else:
            candidates = (prefix + (ranking[size - 1],) for prefix in combinations(ranking[:size - 1], FRONT_COUNT - 1))
        for candidate in candidates:
            if predicate(candidate):
                found.append((tuple(sorted(candidate)), size))
                if len(found) == OPTIONS_PER_GROUP:
                    return found
    raise ValueError("完整前区候选池仍不足 8 个合法组合，停止生成；未放宽硬约束")


def _back_choice(group_id, back):
    """为每种策略选择后区2个号码，返回 (selected_list, adjustments)。"""
    balls = list(back.keys())
    adjustment = []

    if group_id == 1:  # 热号：遗漏3-10中count20最高的2个
        eligible = [b for b in balls if 3 <= back[b]["current_omission"] <= 10]
        if not eligible:
            adjustment.append("后区无遗漏3-10期候选，按距该区间最近优先，再按20期频次排序")
        key = lambda b: (_distance(back[b]["current_omission"], 3, 10), -back[b]["counts"]["20"], b)
        sorted_balls = sorted(balls, key=key)
        selected = sorted(sorted_balls[:BACK_COUNT])

    elif group_id == 2:  # 冷号：遗漏8-15中遗漏最大的2个
        eligible = [b for b in balls if 8 <= back[b]["current_omission"] <= 15]
        if not eligible:
            eligible = [b for b in balls if 3 <= back[b]["current_omission"] <= 20]
            adjustment.append("后区无遗漏8-15期候选，扩展至3-20期")
        if not eligible:
            eligible = balls
            adjustment.append("后区3-20期候选仍为空，扩展至全部12球")
        key = lambda b: (_distance(back[b]["current_omission"], 8, 15), -back[b]["current_omission"], b)
        sorted_balls = sorted(eligible, key=key)
        selected = sorted(sorted_balls[:BACK_COUNT])

    elif group_id == 3:  # 平衡：count20最接近3的2个
        eligible = [b for b in balls if 2 <= back[b]["counts"]["20"] <= 4]
        if not eligible:
            adjustment.append("后区无20期出现2-4次候选，按距该频次区间最近排序")
        key = lambda b: (_distance(back[b]["counts"]["20"], 2, 4), abs(back[b]["counts"]["20"] - 3), b)
        sorted_balls = sorted(balls, key=key)
        selected = sorted(sorted_balls[:BACK_COUNT])

    elif group_id == 4:  # 周期：当前遗漏最接近平均已完成间隔的2个
        eligible = [b for b in balls if back[b]["mean_completed_omission"] is not None]
        if eligible:
            key = lambda b: (abs(back[b]["current_omission"] - back[b]["mean_completed_omission"]), b)
        else:
            eligible = balls
            adjustment.append("后区无完整遗漏间隔，回退至20期频次最高号码")
            key = lambda b: (-back[b]["counts"]["20"], b)
        sorted_balls = sorted(eligible, key=key)
        selected = sorted(sorted_balls[:BACK_COUNT])

    else:  # 综合：综合分最高的2个
        key = lambda b: (-back[b]["composite_score"], b)
        sorted_balls = sorted(balls, key=key)
        selected = sorted(sorted_balls[:BACK_COUNT])

    return selected, adjustment


def _description(group_id, fronts, back_balls, stats):
    odd, big, zones, adjacent = _shape(fronts)
    front = stats["front"]
    back = stats["back"]
    first = f"{fronts[0]:02d}"
    back_str = "-".join(back_balls)

    def omission_text(stat):
        prefix = "至少" if stat["omission_is_lower_bound"] else ""
        return f"{prefix}{stat['current_omission']}期"

    if group_id == 1:
        return f"{first}热度{front[first]['heat']}、调整分{front[first]['heat_score']:.1f}；区间{'-'.join(map(str, zones))}；后区{back_str}近20期{back[back_balls[0]]['counts']['20']}次"
    if group_id == 2:
        return f"{first}遗漏{omission_text(front[first])}；奇偶{odd}:{FRONT_COUNT-odd}、大小{big}:{FRONT_COUNT-big}；尾数{len({n % 10 for n in fronts})}种；后区{back_str}"
    if group_id == 3:
        return f"奇偶{odd}:{FRONT_COUNT-odd}、大小{big}:{FRONT_COUNT-big}；和值{sum(fronts)}、连号{adjacent}对；区间{'-'.join(map(str, zones))}；后区{back_str}"
    if group_id == 4:
        mean0 = back[back_balls[0]]["mean_completed_omission"]
        mean_text = f"{mean0:.1f}期" if mean0 is not None else "暂无完整间隔"
        return f"{first}趋势{front[first]['trend']:+.1f}、周期分{front[first]['cycle_score']:+.1f}；后区{back_str}、平均空期{mean_text}"
    return f"{first}综合{front[first]['composite_score']:.1f}；奇偶{odd}:{FRONT_COUNT-odd}、大小{big}:{FRONT_COUNT-big}；和值{sum(fronts)}；后区{back_str}"


def build_prediction_plan(history: list) -> dict:
    """验证真实开奖数据并为每种策略生成8组候选；无I/O。"""
    draws = _validated_history(history)
    stats = _compute_stats(draws)
    front = stats["front"]
    heat_top = set(_rank(front, "heat")[:10])
    cold_top = set(_rank(front, "current_omission")[:10])
    trend_top = set(_rank(front, "trend")[:10])

    def valid_cold(fronts):
        return (sum(n % 2 for n in fronts) in (2, 3) and 2 <= sum(n >= 18 for n in fronts) <= 3
                and len({n % 10 for n in fronts}) >= 4)

    def valid_balance(fronts):
        odd, big, zones, adjacent = _shape(fronts)
        return (odd in (2, 3) and big in (2, 3) and 60 <= sum(fronts) <= 120
                and adjacent <= 1 and 1 <= zones[0] <= 3 and 1 <= zones[1] <= 3 and 1 <= zones[2] <= 3)

    def valid_composite(fronts):
        selected = set(fronts)
        return (sum(n % 2 for n in fronts) in (2, 3) and sum(n >= 18 for n in fronts) in (2, 3)
                and 60 <= sum(fronts) <= 120 and len(selected & heat_top) >= 2
                and bool(selected & cold_top) and bool(selected & trend_top))

    balance_rank = sorted(range(1, FRONT_MAX + 1), key=lambda n: (
        _distance(front[f"{n:02d}"]["counts"]["30"], 2, 5),
        abs(front[f"{n:02d}"]["counts"]["30"] - 3.5), n))
    middle_count = sum(2 <= stat["counts"]["30"] <= 5 for stat in front.values())

    specifications = {
        1: (_rank(front, "heat_score"), 8, lambda fronts: all(1 <= n <= 3 for n in _shape(fronts)[2])),
        2: (_rank(front, "cold_score"), 12, valid_cold),
        3: (balance_rank, middle_count, valid_balance),
        4: (_rank(front, "cycle_score"), 8, lambda fronts: True),
        5: (_rank(front, "composite_score"), 8, valid_composite),
    }

    options = {}
    for group_id, (ranking, initial_size, predicate) in specifications.items():
        back_balls, back_adjustments = _back_choice(group_id, stats["back"])
        try:
            choices = _front_candidates(ranking, initial_size, predicate)
        except ValueError as exc:
            raise ValueError(f"策略{group_id}：{exc}") from exc
        options[group_id] = []
        for index, (fronts, pool_size) in enumerate(choices, 1):
            adjustments = list(back_adjustments)
            if pool_size > initial_size:
                rule = "按距30期出现2-5次区间的距离扩池" if group_id == 3 else "按策略得分降序扩池"
                adjustments.append(f"前区原候选池{initial_size}球不足8个合法组合，{rule}至{pool_size}球；硬约束保持不变")
            description = _description(group_id, fronts, back_balls, stats)
            if len(description) > 100:
                raise ValueError(f"策略{group_id}程序生成描述超过100字")
            option = {
                "candidate_id": f"{group_id}-{index:02d}",
                "group_id": group_id,
                "front_balls": [f"{n:02d}" for n in fronts],
                "back_balls": back_balls,
                "strategy": STRATEGIES[group_id],
                "description": description,
            }
            if adjustments:
                option["adjustments"] = adjustments
            options[group_id].append(option)

    return {
        "options": options,
        "stats": stats,
        "sources": {"history_count": len(draws), "latest_period": draws[0]["period"],
                    "oldest_period": draws[-1]["period"], "latest_date": draws[0]["date"],
                    "oldest_date": draws[-1]["date"]},
    }


def format_plan(plan: dict) -> str:
    """Keep the full statistics in Python; send only grounded candidates to the model."""
    compact = {
        "source": plan["sources"],
        "groups": [{"group_id": group_id, "strategy": STRATEGIES[group_id],
                    "candidates": [{key: value for key, value in candidate.items()
                                    if key not in ("group_id", "strategy")}
                                   for candidate in plan["options"][group_id]]}
                   for group_id in STRATEGIES],
    }
    return json.dumps(compact, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


if __name__ == "__main__":
    import os
    data_path = os.path.join(os.path.dirname(__file__), "data", "lottery_history.json")
    with open(data_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    result = build_prediction_plan(raw["data"])
    print(json.dumps(result, ensure_ascii=False, indent=2))
