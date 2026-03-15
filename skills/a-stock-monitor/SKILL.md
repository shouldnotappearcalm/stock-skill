---
name: a-stock-monitor
description: A股量化监控系统 - 7维度市场情绪评分、智能选股引擎（短线5策略+中长线7策略）、实时价格监控、涨跌幅排行榜。支持全市场5000+股票数据采集与分析，多指标共振评分，精确买卖点计算，动态止损止盈。每日自动推荐短线3-5只、中长线5-10只优质股票。包含Web界面、自动化Cron任务、历史数据回溯。适用于A股量化交易、技术分析、选股决策。
metadata:
  openclaw:
    requires:
      bins: ["python3"]
      packages: ["akshare", "flask", "numpy", "pandas", "requests"]
---

# A股量化选股和监控系统

一个完整的A股量化选股、实时监控与市场情绪分析系统。

**版本**: 0.0.1  
**许可证**: MIT

---

## 核心功能

### 1. 市场情绪评分 (7维度)
基于全市场5000+只A股的综合情绪评分（0-100分）：
- 涨跌家数比 (20%)
- 平均涨幅 (20%)
- 涨停/跌停比 (15%)
- 强势股占比 (15%)
- 成交活跃度 (10%)
- 波动率 (10%)
- 趋势强度 (10%)

### 2. 智能选股引擎

#### 短线选股 (1-5天)
**5大策略**，每日推荐3-5只短线机会股：
- **RSI短线** - 超短线RSI策略，适合T+0或快速进出
- **MACD短线** - MACD金叉死叉，短期趋势跟踪
- **KDJ短线** - KDJ超买超卖，适合日内波段
- **布林突破** - 布林带突破，捕捉短期波动
- **放量突破** - 量价齐升，短期强势股

**多指标共振评分体系** (满分100分)：
- RSI信号 (20分)
- KDJ信号 (20分)
- MACD信号 (15分)
- 布林带信号 (15分)
- 量价异动 (15分)
- 资金流向 (15分)

**精确买卖点**：
- 动态止损止盈（基于ATR）
- 买入价、止损价、止盈价自动计算
- 预期收益率、风险收益比

#### 中长线选股 (20-180天)
**7大策略**，每日推荐5-10只优质股票：
- **MA趋势** - 均线多头排列，趋势跟踪 (20-60天)
- **MACD趋势** - MACD趋势确认，中期持有 (15-30天)
- **价值成长** - 长期价值投资 (60-180天)
- **突破回踩** - 突破后回踩买入 (10-30天)
- **底部反转** - RSI+MACD双确认 (15-30天)
- **趋势加速** - 均线多头+放量 (10-20天)
- **强势股回调** - 强势股回调低吸 (5-15天)

**综合评分维度**：
- 技术指标 (40%) - MA/MACD/RSI/KDJ等
- 资金流向 (30%) - 主力资金净流入
- 市场热度 (15%) - 换手率、振幅
- 风险评估 (15%) - 波动率、回撤

**持仓建议**：
- 建议仓位（根据评分）
- 预期收益率
- 风险等级
- 持仓周期

#### 选股范围与配置（重要）

**短线/中长线选股仅在「监控股票池」内执行**：推荐结果只从当前 watchlist 中的股票里打分排序产出，**不会**在全市场 5000+ 只股票中扫描。因此：
- 若 watchlist 为空或仅少量股票，选股结果会很少或为空；
- 需要先通过「默认 config + 手动/批量维护 watchlist」或「批量导入脚本」把候选池扩大到一定规模（例如几百只），再跑选股脚本或定时任务。

**配置方式**：
- 监控股票池以 **watchlist.json** 为准（与 config.py 的 WATCHED_STOCKS 互补：无 watchlist 时用 config 初始化并写入 watchlist）。
- 选股脚本（短线/中长线）读取 watchlist.json，并自动过滤创业板(3 开头)和科创板(688 开头)。
- 支持通过 Web「股票池管理」单只增删，或通过 **批量导入脚本**（见下文）从文件/指数成分股批量加入。

### 3. 实时价格监控
- 交易时间：每5秒更新价格
- 非交易时间：显示历史数据
- 自动判断交易时段（9:15-11:30, 13:00-15:00）

### 4. 涨跌幅排行榜
- 实时涨幅榜（Top 5）
- 实时跌幅榜（Top 5）
- 支持点击跳转股票详情页 `/stock/<code>`

### 5. Web 可视化界面
- 市场情绪仪表盘
- 监控股票卡片展示、股票详情页（`/stock/<code>`）
- 回测、参数优化、股票池管理入口
- 统计数据汇总，响应式设计

## 使用方式

### 快速开始

1. **安装依赖**
```bash
pip3 install akshare flask numpy pandas requests
```

2. **配置监控股票（选股候选池）**
- 编辑 `scripts/config.py` 中的 `WATCHED_STOCKS` 作为初始列表；或
- 直接维护同目录下的 `watchlist.json`（选股与 Web 均以此为准）；或
- 启动 Web 后通过「股票池管理」页单只增删；或
- **批量扩充候选池**：使用 `scripts/watchlist_batch.py` 从本地文件或指数成分股（如沪深300、中证500）批量加入，详见下方「批量维护 watchlist」。

3. **启动Web服务**
```bash
cd scripts/
python3 web_app.py
```
访问 `http://localhost:5000`

### 自动化运行

**设置Cron任务**（交易时间每5分钟更新）：
```bash
openclaw cron add --name "A股全市场数据更新" \
  --schedule "*/5 9-15 * * 1-5" \
  --tz "Asia/Shanghai" \
  --payload '{"kind":"systemEvent","text":"cd <skill-path>/scripts && python3 smart_market_updater.py"}'
```

替换 `<skill-path>` 为技能安装路径。

### 批量维护 watchlist

选股只针对 watchlist 内股票，若池子太小可先批量扩充：

```bash
cd scripts

# 从本地文件追加（每行一个 6 位代码，或 JSON 数组）
python3 watchlist_batch.py --file codes.txt

# 从指数成分股追加（与现有列表合并、去重）
python3 watchlist_batch.py --index hs300
python3 watchlist_batch.py --index zz500

# 用指数成分股覆盖当前 watchlist（慎用）
python3 watchlist_batch.py --index hs300 --replace
```

默认会排除创业板(3 开头)、科创板(688 开头)，与选股逻辑一致。

### 手动执行

```bash
# 更新全市场数据
python3 scripts/update_all_market_data.py

# 计算市场情绪
python3 scripts/market_sentiment.py

# 智能更新（仅交易时间）
python3 scripts/smart_market_updater.py

# 检查交易时间
python3 scripts/is_trading_time.py

# 短线选股（仅对 watchlist 内股票，每日推荐3-5只）
python3 scripts/short_term_selector.py

# 中长线选股（仅对 watchlist 内股票，每日推荐5-10只）
python3 scripts/long_term_selector.py

# 增强版中长线选股
python3 scripts/enhanced_long_term_selector.py
```

**脚本运行说明**：`is_trading_time.py` 在非交易时间会以退出码 1 退出（用于 cron 判断）。数据更新与选股脚本依赖网络，且会遍历 watchlist，执行时间可能较长（数分钟至十几分钟），属正常现象。

**数据验证**：可用 `verify_data_sources.py` 拉取指定股票的实时价、K 线、成交额/成交量并打印，便于核对单位与数值。示例：`python3 scripts/verify_data_sources.py 600519`（默认实时 + 最近 5 日 K 线）、`python3 scripts/verify_data_sources.py 000858 --days 10 --cache`（含缓存对比）。

## 目录结构

```
scripts/
├── config.py                       # 配置：WATCHED_STOCKS、Tushare、Web 等
├── web_app.py                      # Flask Web 服务
├── stock_cache_db.py               # SQLite 缓存（含开高低、换手、振幅等字段）
├── watchlist.json                  # 自选股列表（与 config 互补，Web 可维护）
├── stock_async_fetcher.py          # 异步数据获取
├── market_sentiment.py             # 市场情绪计算
├── is_trading_time.py              # 交易时间判断
├── smart_market_updater.py         # 智能更新器
├── update_all_market_data.py       # 全市场数据更新（东方财富→akshare+腾讯兜底）
├── short_term_selector.py          # 短线选股引擎
├── long_term_selector.py           # 中长线选股引擎
├── enhanced_long_term_selector.py  # 增强版中长线选股
├── advanced_long_term_indicators.py # 中长线高级指标（DMI/PEG）
├── fundamental_data.py             # 基本面数据（占位，可选对接 Tushare）
├── strategy_config.py              # 策略配置文件
├── unified_data_source.py          # 统一数据源（新浪→腾讯→东财/akshare 多级兜底）
├── verify_data_sources.py         # 数据验证：拉取实时/K线/成交等并打印，核对单位
├── watchlist_batch.py              # 批量维护 watchlist（文件/指数成分股）
└── templates/
    ├── index.html                  # 首页仪表盘
    └── stock_detail.html           # 股票详情页
```

## API端点

### GET /api/market/sentiment
返回全市场情绪评分

**响应示例**:
```json
{
  "score": 57,
  "level": "偏乐观",
  "emoji": "🟢",
  "description": "市场偏强，情绪稳定",
  "stats": {
    "total": 5000,
    "gainers": 2460,
    "losers": 2534,
    "limit_up": 15,
    "limit_down": 3
  }
}
```

### GET /api/stocks
返回所有监控股票数据

### GET /api/stocks/realtime
返回监控股票实时价格（轻量级）

### GET /api/stock/<code>
返回单只股票详情（含缓存中的开高低、换手、振幅等字段）

### GET/POST/DELETE /api/watchlist
获取、添加、删除自选股列表（与 `watchlist.json` 同步）

## 配置说明

### 交易时间配置
默认交易时间：周一至周五 9:15-15:00

修改 `is_trading_time.py`：
```python
TRADING_HOURS = {
    'morning': (9, 15, 11, 30),    # 9:15-11:30
    'afternoon': (13, 0, 15, 0),   # 13:00-15:00
}
```

### 数据缓存配置
SQLite数据库：`stock_cache.db`
默认缓存时间：30分钟

修改 `stock_cache_db.py`：
```python
MAX_AGE_MINUTES = 30  # 缓存有效期
```

### 监控股票配置
编辑 `scripts/config.py` 的 `WATCHED_STOCKS`，或维护 `scripts/watchlist.json`；Web 端「股票池管理」会读写 `watchlist.json`。

### 市场情绪阈值
修改 `market_sentiment.py`：
```python
# 情绪等级阈值
LEVELS = [
    (80, 100, '极度乐观', '🔴'),
    (65, 79, '乐观', '🟠'),
    (55, 64, '偏乐观', '🟢'),
    # ...
]
```

## 数据来源与兜底

- **统一数据源**（`unified_data_source.py`）：对外单一入口，内部多级兜底，选股/Web 通过 `hybrid_data_source` 调用。
  - **实时行情兜底顺序**：新浪 → 腾讯 → akshare（东方财富）；任一失败自动切下一源。
  - **历史 K 线兜底顺序**：东方财富(ak) → 新浪(ak) → 腾讯(ak)，均经 akshare 封装，返回统一列 `date, open, high, low, close, volume, amount`。
- **全市场更新**（`update_all_market_data.py`）：优先东方财富，失败时降级为 akshare 股票列表 + 腾讯财经批量行情。
- **本地缓存**：SQLite（`stock_cache.db`）存储行情及开高低、换手、振幅等字段。

## 性能优化

1. **分级更新**
   - 实时价格: 5 秒（仅价格+涨跌）
   - 完整数据: 30 秒（含技术指标）
   - 后端更新: 5 分钟（全市场数据）
2. **智能缓存**
   - 交易时间: 5 分钟缓存
   - 非交易时间: 显示历史数据
3. **异步获取**
   - 使用异步方式获取全市场数据
   - 避免阻塞主线程

## 故障排查

### 问题 1：数据全为 null

- **原因**：非交易时间主数据源返回空，或网络异常。
- **解决**：先运行 `python3 update_all_market_data.py`（已支持东方财富 + 腾讯兜底）；若仍无数据可等待交易时间或检查网络。

### 问题 2：Web 界面一直转圈

- **原因**：数据库无有效数据。
- **解决**：运行 `python3 update_all_market_data.py`。

### 问题 3：Cron 任务不执行

- **原因**：时区配置错误。
- **解决**：确保时区设置为 `Asia/Shanghai`。

### 问题 4：端口被占用

- **原因**：Flask 默认端口 5000 冲突。
- **解决**：修改 `web_app.py` 中的端口号。

## 扩展开发

### 添加新的监控指标

编辑 `market_sentiment.py`，添加新的评分维度：

```python
def calculate_sentiment(stocks):
    # 添加新维度
    new_dimension_score = calculate_new_dimension(stocks)
    
    # 调整权重
    score = (
        gain_ratio_score * 0.18 +      # 降低原有权重
        # ...
        new_dimension_score * 0.10      # 新维度10%
    )
```

### 自定义告警规则

创建新的告警脚本：

```python
def check_custom_alert():
    cache = StockCache()
    stocks = cache.get_all_stocks()
    
    # 自定义告警逻辑
    alerts = []
    for stock in stocks:
        if stock['change_pct'] > 5:
            alerts.append(stock)
    
    if alerts:
        send_alert(alerts)
```

## 技术栈

- **后端**：Python 3.9+, Flask
- **数据**：akshare, SQLite
- **前端**：jQuery, Bootstrap
- **自动化**：OpenClaw Cron

## 许可证

MIT License

## 致谢

- akshare 提供 A 股数据接口
- OpenClaw 提供自动化调度能力

