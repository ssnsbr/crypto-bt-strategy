from ast import literal_eval
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import os


def draw_a_coin_from_results(this_run_results, all_portfolio_histories, index=None, coin_name=None, extra_indicators=None):
    if index is not None:
        main_list_str = this_run_results.iloc[index]["main_list"]
        coin_name = this_run_results.iloc[index]["coin"]
    elif coin_name is not None:
        main_list_str = this_run_results[this_run_results["coin"] == coin_name]["main_list"].values[0]
        coin_name = coin_name
    else:
        print("Coin and index is None!")
        return
    print("drawing for ", coin_name)
    main_list = literal_eval(main_list_str)
    draw_zoomable_chart(main_list, coin=coin_name, filename=find_full_candle_file_name(coin_name), portfolio_series=all_portfolio_histories[coin_name], show_candles=True, extra_indicators=extra_indicators)


def find_full_candle_file_name(coin, dir="/content/drive/MyDrive/charts/1s/"):
    for f in os.listdir(dir):
        if coin in f:
            return dir + f
    print(coin, "Not found! in", dir)


def draw_zoomable_chart(main_list, coin, filename, portfolio_series=None, show_candles=False, extra_indicators=None):
    # === Load candle data ===
    df = pd.read_csv(filename)
    if "time" in df.columns:
        df["timestamp"] = pd.to_datetime(df["time"], unit="ms", errors="coerce")
    else:
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", errors="coerce")
    df = df.sort_values("time")
    df = df.dropna(subset=["open", "high", "low", "close"])
    df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].astype(float)
    df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]] * 1_000_000_000

    # === Compute average volume ===
    vol_col = None
    for candidate in ["VolumeTradedinbaseasset", "volume", "Volume"]:
        if candidate in df.columns:
            vol_col = candidate
            break
    if vol_col is not None:
        df["adj_volume"] = df[vol_col] * 1_000_000 / df["close"]
        df["avg_volume_60"] = df["adj_volume"].rolling(60, min_periods=1).mean()
    else:
        print("[Warning] No volume column found — skipping avg_volume_60")
        df["avg_volume_60"] = 0

    # === Extract trade events ===
    events = pd.DataFrame(main_list, columns=["type", "price", "index", "time", "min", "max"])
    events["time"] = pd.to_datetime(events["time"])

    # === Define colors ===
    colors = {"ib": "white", "ba": "orange", "tp": "lime", "sl": "red", "e": "red", "nl": "orange", "bfm": "green", "d": "red"}
    for k, v in colors.items():
        print(k, len(events[events["type"] == k]))

    # === Dynamic subplot layout ===
    has_indicators = bool(extra_indicators)
    has_portfolio = portfolio_series is not None

    rows = 1
    row_heights = [0.55]
    subtitles = [f"{coin} — Trade Events"]
    specs = [[{"secondary_y": True}]]

    portfolio_row = None
    indicator_rows = []

    for ind in (extra_indicators or []):
        rows += 1
        indicator_rows.append(rows)
        row_heights.append(0.2)
        subtitles.append(ind["name"])
        specs.append([{}])
    # if has_indicators:
    #     rows += 1
    #     indicator_row = rows
    #     row_heights.append(0.25)
    #     subtitles.append(", ".join(ind["name"] for ind in extra_indicators))
    #     specs.append([{}])

    if has_portfolio:
        rows += 1
        portfolio_row = rows
        row_heights.append(0.2)
        subtitles.append("Portfolio Value Over Time")
        specs.append([{}])

    total = sum(row_heights)
    row_heights = [h / total for h in row_heights]

    fig = make_subplots(
        rows=rows, cols=1,
        shared_xaxes=True,
        row_heights=row_heights,
        vertical_spacing=0.05,
        subplot_titles=subtitles,
        specs=specs
    )

    # === Candlestick chart ===
    if show_candles:
        fig.add_trace(go.Candlestick(
            x=df["timestamp"],
            open=df["open"], high=df["high"], low=df["low"], close=df["close"],
            name="Candles",
            increasing_line_color="rgba(0,255,0,0.3)", decreasing_line_color="rgba(255,0,0,0.3)",
            increasing_fillcolor="rgba(0,255,0,0.2)", decreasing_fillcolor="rgba(255,0,0,0.2)",
            showlegend=False
        ), row=1, col=1, secondary_y=False)

    # === Avg volume ===
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["avg_volume_60"],
        mode="lines", name="Avg Volume (60)",
        line=dict(color="gold", width=1.5, dash="dot"), opacity=0.7
    ), row=1, col=1, secondary_y=True)

    # === Trade event markers ===
    for t, c in colors.items():
        sub = events[events["type"] == t]
        if not sub.empty:
            fig.add_trace(go.Scatter(
                x=sub["time"],  # ← correct: event timestamps, not df timestamps
                y=sub["price"] * 1.1 if t in ["ib"] else sub["price"],
                mode="markers+text",
                text=sub["type"],
                textposition="top center",
                textfont=dict(size=9, color=c),
                marker=dict(color=c, size=9 if t in ["ib"] else 8,
                            opacity=0.8, line=dict(width=1, color="black")),
                name=t.upper(), showlegend=True
            ), row=1, col=1, secondary_y=False)

    # === Indicators ===
    # if has_indicators:
    #     for ind in extra_indicators:
    #         fig.add_trace(go.Scatter(
    #             x=ind.get("x", df["timestamp"]),
    #             y=ind["series"],
    #             mode="lines", name=ind["name"],
    #             line=dict(color=ind.get("color", "white"), width=1.5)
    #         ), row=indicator_row, col=1)
    #         for level in ind.get("hlines", []):
    #             fig.add_hline(y=level, line_dash="dot", line_color="gray", row=indicator_row, col=1)
    if has_indicators:
        for ind, ind_row in zip(extra_indicators, indicator_rows):
            fig.add_trace(go.Scatter(
                x=ind.get("x", df["timestamp"]),
                y=ind["series"],
                mode="lines", name=ind["name"],
                line=dict(color=ind.get("color", "white"), width=1.5)
            ), row=ind_row, col=1)
            for level in ind.get("hlines", []):
                fig.add_hline(y=level, line_dash="dot", line_color="gray", row=ind_row, col=1)
    # === Portfolio ===
    if has_portfolio:
        portfolio_series.index = pd.to_datetime(portfolio_series.index)
        fig.add_trace(go.Scatter(
            x=portfolio_series.index, y=portfolio_series.values,
            mode="lines+markers", name="Portfolio Value",
            line=dict(color="cyan", width=2), marker=dict(size=4)
        ), row=portfolio_row, col=1)
        fig.update_yaxes(type="log", row=portfolio_row, col=1)  # ← fixed, was hardcoded row=3

    # === Layout ===
    fig.update_layout(
        template="plotly_dark", hovermode="x unified",
        xaxis_rangeslider_visible=False, height=950,
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1)
    )
    fig.update_yaxes(title_text="Price", secondary_y=False, row=1, col=1)
    fig.update_yaxes(title_text="Avg Volume (60)", secondary_y=True, row=1, col=1)

    fig.show()
# df["RSI_14"] = compute_rsi(df["close"], 14)
# df["RSI_30"] = compute_rsi(df["close"], 30)

# extra_indicators=[
#         {"name": "RSI-14", "series": df["RSI_14"].values, "color": "deepskyblue", "hlines": [30, 70]},
#         {"name": "RSI-30", "series": df["RSI_30"].values, "color": "deepskyblue", "hlines": [30, 70]},
# ]
# Don't pass .values — pass the Series with its index intact, or pass x explicitly
# extra_indicators=[
#     {"name": "RSI-14", "series": df["RSI_14"], "x": df["time"], "color": "deepskyblue", "hlines": [30, 70]},
#     {"name": "RSI-30", "series": df["RSI_30"], "x": df["time"], "color": "orange",      "hlines": [30, 70]},
# ]
