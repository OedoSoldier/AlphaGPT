import time

import pandas as pd
import streamlit as st

from data_service import DashboardService
from visualizer import plot_industry_amount, plot_market_scatter, plot_price_history

st.set_page_config(
    page_title="AlphaGPT A-Share Research",
    page_icon="A",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .stDataFrame { border: none; }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_resource
def get_service():
    return DashboardService()


svc = get_service()

st.sidebar.title("AlphaGPT")
st.sidebar.caption("A-share daily research")
if st.sidebar.button("Refresh Data"):
    st.rerun()

stats = svc.get_database_stats()
market_df = svc.get_market_overview()
industry_df = svc.get_industry_overview()
strategy_data = svc.load_strategy_info()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Securities", f"{int(stats.get('security_count') or 0):,}")
with col2:
    st.metric("Daily Bars", f"{int(stats.get('bar_count') or 0):,}")
with col3:
    latest_date = stats.get("latest_trade_date")
    st.metric("Latest Date", str(latest_date) if latest_date else "N/A")
with col4:
    st.metric("Strategy Market", strategy_data.get("market", "A-share daily"))

tab1, tab2, tab3, tab4 = st.tabs(["Market", "Industries", "Strategy", "Logs"])

with tab1:
    if market_df.empty:
        st.warning("No market data found. Run the Tushare data pipeline first.")
    else:
        st.plotly_chart(plot_market_scatter(market_df), use_container_width=True)
        display_df = market_df.copy()
        display_df["pct_chg"] = display_df["pct_chg"].apply(lambda x: f"{x:.2%}")
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        choices = market_df["ts_code"].tolist()
        selected = st.selectbox("Security", choices)
        if selected:
            name = market_df.loc[market_df["ts_code"] == selected, "name"].iloc[0]
            bars_df = svc.get_recent_bars(selected)
            st.plotly_chart(
                plot_price_history(bars_df, title=f"{selected} {name} Close"),
                use_container_width=True,
            )

with tab2:
    if industry_df.empty:
        st.warning("No industry snapshot available.")
    else:
        st.plotly_chart(plot_industry_amount(industry_df), use_container_width=True)
        show_df = industry_df.copy()
        show_df["avg_pct_chg"] = show_df["avg_pct_chg"].apply(lambda x: f"{x:.2%}")
        st.dataframe(show_df, use_container_width=True, hide_index=True)

with tab3:
    formula = strategy_data.get("formula", "Not trained yet")
    if isinstance(formula, list):
        formula_text = ", ".join(str(x) for x in formula)
    else:
        formula_text = str(formula)

    strategy_df = pd.DataFrame(
        [
            ("Market", strategy_data.get("market", "A-share daily")),
            ("Score", strategy_data.get("score", "N/A")),
            ("Formula", formula_text),
            ("Features", ", ".join(strategy_data.get("features", []))),
        ],
        columns=["Field", "Value"],
    )
    st.dataframe(strategy_df, use_container_width=True, hide_index=True)

with tab4:
    logs = svc.get_recent_logs(50)
    if logs:
        st.code("".join(logs), language="text")
    else:
        st.caption("No logs found.")

if st.sidebar.checkbox("Auto-refresh 30s", value=False):
    time.sleep(30)
    st.rerun()
