AlphaGPT 仓库速读

这版仓库默认是一套“A股日线数据 + 因子挖掘 + 离线回测 + 看板”的研究系统。数据源从原来的 Birdeye/Solana 链路切换为 Tushare，默认同步全 A 正常上市股票，排除 ST 和上市不足 180 天的标的，行情默认使用前复权日线。

代码组织
- data_pipeline/：Tushare 股票池与日线同步，写入 Postgres。
- model_core/：A股日线特征、公式生成、StackVM 执行和 open-to-open 回测。
- dashboard/：Streamlit 看板，展示市场快照、行业成交额和策略信息。
- execution/、strategy_manager/：保留的 crypto legacy 代码，默认流程不使用。
- times.py、lord/：研究脚本或实验材料。

主流程
1. `uv sync` 创建 Python 3.11 环境。
2. 配置 `.env`，至少设置数据库和 `TUSHARE_TOKEN`。
3. `uv run python -m data_pipeline.run_pipeline` 同步 `securities` 与 `daily_bars`。
4. `uv run python -m model_core.engine` 训练并输出 `best_astock_strategy.json`。
5. `uv run streamlit run dashboard/app.py` 打开研究看板。

核心设计
- 模型不是直接预测价格，而是生成可解释的公式 token 序列。
- `StackVM` 将公式应用到特征张量，得到每只股票每天的因子信号。
- 回测使用 A股日线 open-to-open 收益，并通过 `tradable_mask` 避免停牌/缺失日。
- 当前版本只做离线研究，不接券商交易 API，不做真实下单。

默认因子
- RET：1 日收益
- RET5：5 日收益
- VOL_CHG：成交量相对 20 日均量变化
- PRESSURE：K 线实体强度
- MA_DEV：收盘价相对 20 日均线偏离
- AMOUNT_STRENGTH：成交额强度

环境与文档
- 默认使用 `pyproject.toml` + `uv.lock` 管理环境。
- Solana/Jupiter/Birdeye 依赖已移入 `crypto-legacy` extra。
- Tushare 接口参考：`stock_basic`、`daily`、`pro_bar` 与权限说明。
