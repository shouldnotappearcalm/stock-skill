# stock-skill

A 股量化监控与选股技能集合。当前包含一个子 Skill：`a-stock-monitor`。

## 仓库结构

```
stock-skill/
├── README.md                   # 本文件
└── skills/
    ├── README.md               # skills 目录说明
    └── a-stock-monitor/        # A 股量化监控子 Skill
        ├── SKILL.md            # Skill 能力描述（OpenClaw 标准格式）
        ├── _meta.json          # Skill 元数据（slug、版本等）
        ├── USAGE.md            # 配置与使用指南
        ├── references/         # 数据源方案、API 文档、使用示例等
        └── scripts/            # 所有后端实现脚本
```

## 子 Skill 列表

| Skill | 描述 | 路径 |
|-------|------|------|
| [a-stock-monitor](skills/a-stock-monitor/SKILL.md) | A 股量化监控：市场情绪、智能选股、实时监控、Web 界面 | `skills/a-stock-monitor/` |

## a-stock-monitor 概览

A 股量化选股与实时监控系统，主要能力包括：

- **7 维市场情绪评分**（0–100 分）：涨跌家数比、平均涨幅、涨停/跌停比、强势股占比、成交活跃度、波动率、趋势强度。
- **短线选股**（1–5 天）：RSI、KDJ、MACD、布林带、量价共振五策略，每日推荐 3–5 只，附精确买卖点与动态止损止盈。
- **中长线选股**（20–180 天）：趋势、动量、量能、ADX、波动率、乖离率七策略，每日推荐 5–10 只。
- **实时 Web 看板**：监控自选股价格、涨跌幅排行、市场情绪仪表盘；支持股票详情页、回测/参数优化/股票池管理入口；自选股由 `config.py` 与 `watchlist.json` 管理，可在 Web 端增删。
- **多数据源兜底**：全市场数据更新优先东方财富（akshare `stock_zh_a_spot_em`），失败时降级为 akshare 股票列表 + 腾讯财经批量行情；缓存字段扩展为含昨收、开高低、换手、振幅等。

### 快速开始

```bash
# 安装依赖
pip3 install akshare flask numpy pandas requests

# 监控列表：编辑 skills/a-stock-monitor/scripts/config.py 的 WATCHED_STOCKS，或首次启动后通过 Web 管理
cd skills/a-stock-monitor/scripts
python3 update_all_market_data.py

# 启动 Web 界面
python3 web_app.py
# 浏览器访问 http://localhost:5000
```

详细配置与命令见 [skills/a-stock-monitor/USAGE.md](skills/a-stock-monitor/USAGE.md)。

## 新增更多 Skill

在 `skills/` 下创建新子目录，参考 [skills/README.md](skills/README.md) 中的标准结构，即可将更多量化分析能力以相同模式纳入本仓库管理。

## 技术栈

- Python 3.9+，Flask
- akshare（东方财富 + 腾讯财经兜底）、SQLite 本地缓存（`scripts/stock_cache.db`，含开高低、换手、振幅等字段）
- ECharts + Bootstrap 前端
- `config.py` + `watchlist.json` 管理自选股
- OpenClaw Cron / 系统 crontab 自动化调度

## 许可证

MIT
