# AlphaGPT

AlphaGPT 当前默认是一套离线 A 股日线研究系统。它使用 Tushare 同步 A 股日线行情，将标准化后的行情写入 Postgres，再用 PyTorch 挖掘公式型因子，并通过 Streamlit 提供研究看板。

旧版 Solana / Birdeye / Jupiter 相关代码仍保留在 legacy 模块中，便于参考和迁移，但不再属于默认环境和默认工作流。

## 快速开始

使用 uv 安装依赖：

```powershell
uv sync
```

创建本地 `.env` 配置文件：

```powershell
Copy-Item .env.example .env
```

编辑 `.env`，至少设置下面这些配置：

```dotenv
DB_USER=postgres
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=astock_quant
TUSHARE_TOKEN=your_tushare_token_here
```

如果数据库还不存在，先创建数据库：

```powershell
psql -U postgres -c "CREATE DATABASE astock_quant;"
```

同步 Tushare 数据：

```powershell
uv run python -m data_pipeline.run_pipeline
```

训练策略：

```powershell
uv run python -m model_core.engine
```

启动看板：

```powershell
uv run streamlit run dashboard/app.py
```

## 配置说明

默认数据源是 Tushare：

```dotenv
TUSHARE_ADJ=qfq
TUSHARE_START_DATE=20180101
TUSHARE_END_DATE=
TUSHARE_INCREMENTAL=true
TUSHARE_REQUEST_INTERVAL_SECONDS=0.25
TUSHARE_MAX_RETRIES=3
TUSHARE_NO_PROXY=true
TUSHARE_MIN_LIST_DAYS=180
TUSHARE_EXCLUDE_ST=true
TUSHARE_UNIVERSE_LIMIT=0
```

小规模验证时，可以临时指定少量股票和较短日期区间：

```powershell
$env:TUSHARE_CODES="000001.SZ,600000.SH"
$env:TUSHARE_START_DATE="20240101"
$env:TUSHARE_END_DATE="20240301"
uv run python -m data_pipeline.run_pipeline
```

`TUSHARE_ADJ=qfq` 是默认设置，表示使用前复权行情。也可以设置为 `hfq` 使用后复权，或设置为 `none` / `raw` 使用未复权日线。

如果系统环境配置了代理，数据管线默认会在连接 Tushare 时临时绕过代理。保持 `TUSHARE_NO_PROXY=true` 即可；只有明确希望 Tushare 也走代理时才改成 `false`。

## 数据模型

A 股数据管线会写入两张主表：

- `securities`：股票代码、简称、名称、地域、行业、市场、交易所、上市日期和上市状态。
- `daily_bars`：交易日期、股票代码、开盘价、最高价、最低价、收盘价、成交量、成交额和数据来源。

模型加载器会构建 6 个日线特征：

- `RET`：1 日收盘收益。
- `RET5`：5 日收盘收益。
- `VOL_CHG`：成交量相对 20 日均量的变化。
- `PRESSURE`：K 线实体强度。
- `MA_DEV`：收盘价相对 20 日均线的偏离。
- `AMOUNT_STRENGTH`：成交额强度。

回测使用 open-to-open 目标收益，并通过 `ASTOCK_TRADE_COST_RATE` 配置交易成本。

## 测试

运行静态编译检查和单元测试：

```powershell
uv run python -m compileall data_pipeline model_core dashboard
uv run pytest
```

pytest 测试只使用本地构造的 DataFrame，不会调用真实 Tushare API。

## Tushare 参考资料

- `stock_basic`：https://tushare.pro/wctapi/documents/25.md
- `daily`：https://tushare.pro/wctapi/documents/27.md
- `pro_bar`：https://tushare.pro/wctapi/documents/109.md
- 权限说明：https://tushare.pro/document/1?doc_id=108

Tushare 的接口权限和调用频率取决于账号积分。如果数据管线返回空数据，优先检查 token 是否有效、账号是否有对应接口权限，以及日期区间是否合理。

## Legacy Crypto 模块

旧版 crypto 执行链路仍保留在 `execution/` 和部分 `strategy_manager/` 代码中，但相关依赖已经变成可选项：

```powershell
uv sync --extra crypto-legacy
```

默认 A 股工作流不会连接 Solana、Jupiter、Birdeye 或任何券商接口。它只产出离线数据、研究结果和看板视图，不进行真实交易。
