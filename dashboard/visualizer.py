import plotly.express as px
import plotly.graph_objects as go


def plot_market_scatter(market_df):
    if market_df.empty:
        return go.Figure()

    df = market_df.copy()
    df["size_amount"] = df["amount"].fillna(0).clip(lower=1)
    fig = px.scatter(
        df,
        x="amount",
        y="pct_chg",
        size="size_amount",
        color="industry",
        hover_name="name",
        hover_data=["ts_code", "close", "volume"],
        title="Latest Daily Snapshot: Amount vs Intraday Return",
        template="plotly_white",
    )
    fig.update_layout(
        yaxis_tickformat=".2%",
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return fig


def plot_industry_amount(industry_df):
    if industry_df.empty:
        return go.Figure()

    show_df = industry_df.head(20).sort_values("amount", ascending=True)
    fig = go.Figure(
        data=[
            go.Bar(
                x=show_df["amount"],
                y=show_df["industry"],
                orientation="h",
                marker_color="#2878b5",
            )
        ]
    )
    fig.update_layout(
        title="Top Industries by Turnover Amount",
        template="plotly_white",
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return fig


def plot_price_history(bars_df, title="Recent Close"):
    if bars_df.empty:
        return go.Figure()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=bars_df["trade_date"],
            y=bars_df["close"],
            mode="lines",
            name="Close",
            line=dict(color="#c43b3b", width=2),
        )
    )
    fig.update_layout(
        title=title,
        template="plotly_white",
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return fig
