from bokeh.palettes import Category10
from bokeh.models import (
    ColumnDataSource, HoverTool, CrosshairTool, Span,
    DatetimeTickFormatter, NumeralTickFormatter, BoxAnnotation
)
from bokeh.layouts import column
from bokeh.plotting import figure, show, output_notebook
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
        uirevision="constant",
        template="plotly_dark",
        hovermode="x unified",
        xaxis_rangeslider_visible=False,
        height=950,
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1)
    )
    # Set every y-axis: autorange=True, fixedrange=False
    for i in range(1, rows + 1):
        yaxis_name = f"yaxis{i}" if i > 1 else "yaxis"
        fig.update_layout(**{yaxis_name: dict(autorange=True, fixedrange=False)})
    # Also do the secondary y on row 1
    fig.update_layout(yaxis2=dict(autorange=True, fixedrange=False))

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


output_notebook()


def draw_a_coin_from_results(this_run_results, all_portfolio_histories, index=None, coin_name=None, extra_indicators=None):
    if index is not None:
        main_list_str = this_run_results.iloc[index]["main_list"]
        coin_name = this_run_results.iloc[index]["coin"]
    elif coin_name is not None:
        main_list_str = this_run_results[this_run_results["coin"] == coin_name]["main_list"].values[0]
    else:
        print("Coin and index is None!")
        return
    print("drawing for", coin_name)
    main_list = literal_eval(main_list_str)
    draw_zoomable_chart(
        main_list, coin=coin_name,
        filename=find_full_candle_file_name(coin_name),
        portfolio_series=all_portfolio_histories[coin_name],
        show_candles=True,
        extra_indicators=extra_indicators
    )


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
    df = df.sort_values("timestamp")
    df = df.dropna(subset=["open", "high", "low", "close"])
    df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].astype(float) * 1_000_000_000

    # === Resolve indicator series from functions ===
    resolved_indicators = []
    for ind in (extra_indicators or []):
        resolved = dict(ind)  # copy so we don't mutate the original
        if "fn" in resolved:
            resolved["series"] = resolved.pop("fn")(df)
        resolved.setdefault("x", df["timestamp"])
        resolved_indicators.append(resolved)
    has_indicators = bool(resolved_indicators)

    # === Volume ===
    vol_col = None
    for candidate in ["VolumeTradedinbaseasset", "volume", "Volume"]:
        if candidate in df.columns:
            vol_col = candidate
            break
    if vol_col is not None:
        df["adj_volume"] = df[vol_col] * 1_000_000 / df["close"]
        df["avg_volume_60"] = df["adj_volume"].rolling(60, min_periods=1).mean()
    else:
        df["avg_volume_60"] = 0

    # === Trade events ===
    events = pd.DataFrame(main_list, columns=["type", "price", "index", "time", "min", "max"])
    events["time"] = pd.to_datetime(events["time"])

    colors = {
        "ib": "white",
        "ba": "orange",
        "tp": "lime",
        "sl": "red",
        "e": "red",
        "nl": "orange",
        "bfm": "green",
        "d": "red"
    }
    for k in colors:
        print(k, len(events[events["type"] == k]))

    # === Shared x range (drives linked zoom) ===
    x_min = df["timestamp"].min()
    x_max = df["timestamp"].max()

    TOOLS = "xpan,xwheel_zoom,xbox_zoom,ypan,ywheel_zoom,ybox_zoom,reset,save"
    
    DARK_BG = "#0f1117"
    GRID_COL = "#2a2a3a"
    TEXT_COL = "#cccccc"

    def base_fig(height, y_axis_label="", x_range=None):
        kwargs = dict(
            width=1400, height=height,
            background_fill_color=DARK_BG,
            border_fill_color=DARK_BG,
            outline_line_color=GRID_COL,
            tools=TOOLS,
            active_scroll="xwheel_zoom",
            x_axis_type="datetime",
            y_axis_label=y_axis_label,
        )
        if x_range is not None:
            kwargs["x_range"] = x_range
        p = figure(**kwargs)
        p.xgrid.grid_line_color = GRID_COL
        p.ygrid.grid_line_color = GRID_COL
        p.xaxis.major_label_text_color = TEXT_COL
        p.yaxis.major_label_text_color = TEXT_COL
        p.yaxis.axis_label_text_color = TEXT_COL
        p.xaxis.formatter = DatetimeTickFormatter(
            hours="%d %b %H:%M", days="%d %b", months="%b %Y"
        )
        p.add_tools(CrosshairTool(line_color="gray", line_alpha=0.5))
        return p

    # ── Row 1: Price ──────────────────────────────────────────────
    p_price = base_fig(500, y_axis_label="Price")
    p_price.title.text = f"{coin} — Trade Events"
    p_price.title.text_color = TEXT_COL

    if show_candles:
        inc = df["close"] >= df["open"]
        dec = ~inc
        w = 30_000  # candle width in ms — adjust to your candle interval

        src_inc = ColumnDataSource(dict(
            x=df["timestamp"][inc], top=df["close"][inc], bottom=df["open"][inc],
            high=df["high"][inc], low=df["low"][inc]
        ))
        src_dec = ColumnDataSource(dict(
            x=df["timestamp"][dec], top=df["open"][dec], bottom=df["close"][dec],
            high=df["high"][dec], low=df["low"][dec]
        ))
        p_price.segment("x", "high", "x", "low", source=src_inc, color="rgba(0,200,0,0.4)")
        p_price.segment("x", "high", "x", "low", source=src_dec, color="rgba(200,0,0,0.4)")
        p_price.vbar("x", w, "top", "bottom", source=src_inc,
                     fill_color="rgba(0,200,0,0.25)", line_color="rgba(0,200,0,0.5)")
        p_price.vbar("x", w, "top", "bottom", source=src_dec,
                     fill_color="rgba(200,0,0,0.25)", line_color="rgba(200,0,0,0.5)")
    else:
        p_price.line(df["timestamp"], df["close"], color="#4488ff", line_width=1.5, legend_label="Close")

    # Volume on secondary y — Bokeh doesn't have native secondary y, use extra_y_ranges
    from bokeh.models import LinearAxis, Range1d
    vol_max = df["avg_volume_60"].max()
    p_price.extra_y_ranges = {"vol": Range1d(start=0, end=vol_max * 4)}
    vol_axis = LinearAxis(y_range_name="vol", axis_label="Avg Vol (60)",
                          axis_label_text_color=TEXT_COL, major_label_text_color=TEXT_COL)
    p_price.add_layout(vol_axis, "right")
    p_price.line(df["timestamp"], df["avg_volume_60"],
                 color="gold", line_width=1.2, line_dash="dashed",
                 alpha=0.6, y_range_name="vol", legend_label="Avg Vol 60")

    # Trade event markers
    for t, c in colors.items():
        sub = events[events["type"] == t]
        if sub.empty:
            continue
        y = sub["price"] * 1.1 if t == "ib" else sub["price"]
        src = ColumnDataSource(dict(x=sub["time"], y=y, label=sub["type"]))
        p_price.scatter("x", "y", source=src, color=c, size=9 if t == "ib" else 7,
                        alpha=0.85, marker="circle", legend_label=t.upper())
        p_price.add_tools(HoverTool(renderers=[
            p_price.scatter("x", "y", source=src, color=c, size=0, alpha=0)
        ], tooltips=[("Type", "@label"), ("Price", "@y{0.00000000}"), ("Time", "@x{%F %T}")],
            formatters={"@x": "datetime"}, mode="mouse"))

    p_price.legend.background_fill_color = "#1a1a2a"
    p_price.legend.label_text_color = TEXT_COL
    p_price.legend.border_line_color = GRID_COL
    p_price.legend.click_policy = "hide"

    panels = [p_price]

    # ── Indicator rows ────────────────────────────────────────────
    palette = Category10[10]
    for i, ind in enumerate(resolved_indicators or []):
        p_ind = base_fig(180, y_axis_label=ind["name"], x_range=p_price.x_range)
        x = ind.get("x", df["timestamp"])
        p_ind.line(x, ind["series"], color=ind.get("color", palette[i % 10]),
                   line_width=1.5, legend_label=ind["name"])

        for level in ind.get("hlines", []):
            hline = Span(location=level, dimension="width",
                         line_color="gray", line_dash="dashed", line_width=1, line_alpha=0.6)
            p_ind.add_layout(hline)

        p_ind.legend.background_fill_color = "#1a1a2a"
        p_ind.legend.label_text_color = TEXT_COL
        p_ind.legend.border_line_color = GRID_COL
        panels.append(p_ind)

    # ── Portfolio row ─────────────────────────────────────────────
    if portfolio_series is not None:
        portfolio_series.index = pd.to_datetime(portfolio_series.index)
        p_port = base_fig(180, y_axis_label="Portfolio", x_range=p_price.x_range)
        p_port.line(portfolio_series.index, portfolio_series.values,
                    color="cyan", line_width=1.8, legend_label="Portfolio Value")
        p_port.scatter(portfolio_series.index, portfolio_series.values,
                       color="cyan", size=3, alpha=0.5)
        p_port.yaxis.formatter = NumeralTickFormatter(format="0.0a")
        p_port.legend.background_fill_color = "#1a1a2a"
        p_port.legend.label_text_color = TEXT_COL
        p_port.legend.border_line_color = GRID_COL
        panels.append(p_port)

    # ── Render ────────────────────────────────────────────────────
    show(column(*panels, sizing_mode="stretch_width"))


# df["timestamp"] = pd.to_datetime(df["time"], unit="ms", errors="coerce")

# df["RSI_14"] = compute_rsi(df["close"], 14)
# df["ATR"] = compute_atr(df, 14)
extra_indicators = [
    {
        "name": "RSI-14",
        "fn": lambda df: compute_rsi(df["close"], 14),
        "color": "deepskyblue",
        "hlines": [30, 70]
    },
    {
        "name": "ATR",
        "fn": lambda df: compute_atr(df, 14),
        "color": "orange"
    },
    {
        "name": "NATR",
        "fn": lambda df: compute_natr_forman(df, 14),
        "color": "magenta",
        "hlines": [1, 3, 5]
    },
]
draw_a_coin_from_results(this_run_results, all_portfolio_histories, coin_name="2hpLgGFKAG", extra_indicators=extra_indicators)
