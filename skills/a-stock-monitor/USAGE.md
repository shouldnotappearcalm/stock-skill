# A股量化监控系统 - 配置与使用指南

## 一、环境要求

- Python 3.9+
- pip3

## 二、安装与配置

### 1. 安装依赖

在项目根目录或 `scripts` 目录下执行：

```bash
pip3 install akshare flask flask-login ccxt
```

（若仅使用数据更新、选股脚本且不启动 Web，可只装 `akshare`。）

### 2. 数据库路径（已自动处理）

- 数据缓存 SQLite 默认使用 **当前技能/脚本所在目录** 下的 `stock_cache.db`。
- 如需自定义路径，可设置环境变量：  
  `export STOCK_CACHE_DB=/你的路径/stock_cache.db`

### 3. 监控股票配置（选股候选池）

**重要**：短线/中长线选股**只在 watchlist 内的股票上执行**，不会在全市场扫描。若 watchlist 为空或很少，推荐结果会很少或为空，需先扩充候选池。

**方式 A：config 初始 + watchlist 持久**

- 编辑 `scripts/config.py` 的 `WATCHED_STOCKS` 作为默认列表；首次启动 Web 或选股时若无 `watchlist.json` 会据此创建。
- 之后以 **watchlist.json** 为准（Web「股票池管理」与选股脚本都读写该文件）。

**方式 B：直接编辑 watchlist.json**

在 `scripts` 目录下创建或编辑 `watchlist.json`，例如：

```json
["600036", "601318", "600519", "000858", "601012"]
```

**方式 C：批量扩充（推荐）**

用脚本从文件或指数成分股批量加入，见下文「批量维护 watchlist」。

选股脚本会从 watchlist 读取列表，并自动排除创业板(3 开头)和科创板(688 开头)。

### 4. 可选：全局配置

编辑 `scripts/config.py` 可修改：

- `WATCHED_STOCKS`：部分脚本会读取的监控列表
- `WEB_HOST` / `WEB_PORT`：Web 监听地址与端口（当前 Web 入口在 `web_app.py` 中写死端口 5000，若需与 config 一致需改 `web_app.py`）
- `PASSWORD`：Web 登录密码（若 Web 使用 config 中的密码）

## 三、使用方式

### 1. 初始化数据库（首次使用）

进入脚本目录并执行一次，会自动创建 `stock_cache.db` 及表结构：

```bash
cd scripts
python3 -c "from stock_cache_db import StockCache; StockCache().conn.close(); print('OK')"
```

或直接运行会用到缓存的脚本（如下面的「全市场数据更新」），也会自动建库。

### 2. 全市场数据更新（必做一步）

用于拉取全市场行情并写入本地缓存，供「市场情绪」和「选股」使用。建议交易时间内执行：

```bash
cd scripts
python3 update_all_market_data.py
```

若需定时执行，可用系统 cron 或 OpenClaw（见下文），例如每 5 分钟一次。

### 3. 市场情绪

依赖全市场数据已更新，执行：

```bash
cd scripts
python3 market_sentiment.py
```

输出为 JSON 格式的市场情绪评分与统计。

### 4. 批量维护 watchlist

选股仅针对 watchlist 内股票，池子过小时可先批量扩充：

```bash
cd scripts

# 从指数成分股追加（与现有列表合并、去重）
python3 watchlist_batch.py --index hs300
python3 watchlist_batch.py --index zz500

# 从本地文件追加（每行一个 6 位代码，或一行 JSON 数组）
python3 watchlist_batch.py --file codes.txt

# 用指数成分股覆盖当前 watchlist
python3 watchlist_batch.py --index hs300 --replace
```

默认会排除创业板、科创板；保留则加 `--no-filter`。

### 5. 短线选股（每日 3–5 只）

仅对 **watchlist 内**股票打分排序，依赖 `watchlist.json` 与缓存数据：

```bash
cd scripts
python3 short_term_selector.py
```

### 6. 中长线选股（每日 5–10 只）

同样仅对 **watchlist 内**股票，需要 `watchlist.json` 与缓存数据：

```bash
cd scripts
python3 long_term_selector.py
```

### 7. 智能更新（仅交易时间更新）

适合做定时任务，只在 A 股交易时段执行更新逻辑：

```bash
cd scripts
python3 smart_market_updater.py
```

### 8. 启动 Web 界面

```bash
cd scripts
python3 web_app.py
```

- 浏览器访问：`http://localhost:5000`
- 默认账号：`admin` / `admin123`（其他账号见 `web_app.py` 中 `USERS`）
- 功能：监控列表、市场情绪、回测入口等（回测当前为占位实现）

### 9. 检查是否交易时间

```bash
cd scripts
python3 is_trading_time.py
```

## 四、定时任务（可选）

使用 OpenClaw 时，可在交易时间每 5 分钟更新全市场数据（将 `<skill-path>` 换成实际技能路径）：

```bash
openclaw cron add --name "A股全市场数据更新" \
  --schedule "*/5 9-15 * * 1-5" \
  --tz "Asia/Shanghai" \
  --payload '{"kind":"systemEvent","text":"cd <skill-path>/scripts && python3 smart_market_updater.py"}'
```

未使用 OpenClaw 时，可用系统 crontab 配置类似命令。

## 五、常见问题

| 现象 | 处理 |
|------|------|
| 端口 5000 被占用 | 修改 `scripts/web_app.py` 末尾 `app.run(..., port=5001)` 等 |
| 数据全为 null / 一直转圈 | 多为非交易时间或未更新缓存，先执行 `python3 update_all_market_data.py` |
| ModuleNotFoundError: flask_login | 执行 `pip3 install flask-login` |
| 短线/中长线选股报错 | 确认已在 `scripts` 下创建 `watchlist.json` 且全市场数据已更新 |

## 六、目录与脚本速查

| 路径 | 说明 |
|------|------|
| `scripts/web_app.py` | Web 服务入口；监控列表在代码内 `WATCHED_STOCKS`，启动时也会读 `watchlist.json` |
| `scripts/watchlist.json` | 选股与 Web 共用股票池（选股仅在此范围内执行） |
| `scripts/watchlist_batch.py` | 批量维护 watchlist：从文件或指数成分股追加/覆盖 |
| `scripts/config.py` | 全局配置（监控列表、Web、密码等） |
| `scripts/stock_cache_db.py` | 缓存逻辑；库文件默认同目录下 `stock_cache.db` |
| `scripts/update_all_market_data.py` | 全市场数据更新 |
| `scripts/smart_market_updater.py` | 按交易时间触发的智能更新 |
| `scripts/market_sentiment.py` | 市场情绪计算 |
| `scripts/short_term_selector.py` | 短线选股 |
| `scripts/long_term_selector.py` | 中长线选股 |
| `references/API.md` | 接口说明 |
| `references/INSTALL.md` | 安装与验证说明 |

按上述步骤配置并先执行一次「全市场数据更新」，即可正常使用 Web、情绪与选股功能。
