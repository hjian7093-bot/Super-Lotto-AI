# 大乐透开奖与 AI 预测数据展示系统

一个现代化的大乐透数据展示系统，支持历史开奖数据查看和多策略 AI 预测展示。

## ✨ 主要特性

- 🎨 现代化 UI 设计，支持亮色/暗色主题切换
- 📊 历史开奖数据展示
- 🎯 多策略预测结果对比
- 📱 完全响应式设计，支持移动端
- ⚡ 优雅的动画效果和交互体验

## 🚀 快速开始

### Windows
```cmd
start_server.bat
```

### macOS/Linux
```bash
./start_server.sh
```

### 手动启动
```bash
python -m http.server 8000
```

然后在浏览器中打开：http://localhost:8000

## 🔮 预测策略

每种策略生成 8 组候选：

| 策略 | 说明 |
|---|---|
| 热号追随者 | 选择最近 30 期高频号码，追踪热门趋势 |
| 冷号逆向者 | 选择最近 30 期低频号码，期待均值回归 |
| 平衡策略师 | 综合奇偶比、大小比、和值、区间等多维度平衡 |
| 周期理论家 | 选择短期频率上穿长期频率的号码 |
| 综合决策者 | 融合以上所有策略的综合方案 |

## 📁 项目结构

```
Super-Lotto-AI/
├── index.html                 # 主页面
├── css/
│   └── style.css              # 样式文件
├── js/
│   ├── app.js                 # 主应用逻辑
│   ├── data-loader.js         # 数据加载模块
│   └── components.js          # UI 组件
├── data/
│   ├── lottery_history.json   # 历史开奖数据
│   └── ai_predictions.json    # AI 预测数据
├── fetch_history/
│   └── fetch_lottery_history.py  # 数据爬取脚本
├── prediction_rules.py        # 预测算法核心
├── gen_predictions.py         # 生成预测数据脚本
├── start_server.sh            # 启动脚本 (macOS/Linux)
├── start_server.bat            # 启动脚本 (Windows)
└── README.md                   # 项目说明
```

## 🔄 更新数据

### 更新历史开奖数据
```bash
cd fetch_history
python fetch_lottery_history.py
```

脚本会自动从 500 彩票网爬取最新数据，合并去重，并同步到 `data/lottery_history.json`。

### 生成预测数据
```bash
python gen_predictions.py
```

## 📝 数据格式

### 规则
- 前区：5 个号码，范围 01-35
- 后区：2 个号码，范围 01-12
- 开奖日：每周一、三、六晚 21:25

### lottery_history.json
```json
{
  "last_updated": "2026-10-13T10:00:00Z",
  "data": [
    {
      "period": "26109",
      "date": "2026-10-10",
      "front_balls": ["02", "08", "15", "16", "18"],
      "back_balls": ["02", "03"]
    }
  ],
  "next_draw": {
    "next_period": "26110",
    "next_date": "2026-10-12",
    "draw_time": "21:25"
  }
}
```

## ⚠️ 重要提示

**浏览器安全限制**:
- ❌ 不能直接双击 `index.html` 打开（会遇到 CORS 错误）
- ✅ 必须通过 HTTP 服务器访问

## 🛠️ 技术栈

- **前端**: 纯 JavaScript (ES6+) + Chart.js
- **样式**: 现代 CSS (CSS Variables, Flexbox, Grid)
- **数据爬取**: Python 3 + BeautifulSoup
- **预测算法**: 纯 Python 标准库实现

## ⚖️ 免责声明

本网站展示的预测数据仅供参考和研究使用，不构成任何购彩建议。彩票开奖结果具有随机性，任何预测都无法保证中奖。请理性购彩，量力而行。
