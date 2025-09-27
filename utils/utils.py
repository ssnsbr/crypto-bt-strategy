from datetime import datetime


def getstring(dic):
    ret = ""
    for p, v in dic.items():  # Changed from strategy_params to dic
        if isinstance(v, int) and v > 1000:  # Fixed type checking
            ret = ret + "_" + str(p) + "-" + format_marketcap(v)
        else:
            ret = ret + "_" + str(p) + "-" + str(v)
    return ret


def get_name(strategy_class, strategy_params, sizer_class, sizer_params, len_file):
    date_str = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")  # or "%Y%m%d_%H%M%S" if you want timestamp
    naming = [strategy_class.__name__, sizer_class.__name__, date_str, "len-" + str(len_file)]
    # Detail string (longer version, readable)
    details = {
        "strategy": strategy_class.__name__,
        "strategy_params": strategy_params,
        "sizer": sizer_class.__name__,
        "sizer_params": sizer_params,
        "time": date_str,
        "len": len_file,
    }
    name = "_".join(naming)
    # detail = "_".join(details)

    return name, details


def format_price_to_marketcap(price):
    marketcap = price * 1_000_000_000
    return format_marketcap(marketcap)


def format_marketcap(marketcap):
    """
    Calculates market cap and formats it to K or M.
    """
    if marketcap >= 1_000_000_000:  # Billions
        return f"{marketcap / 1_000_000_000:.2f}B"
    elif marketcap >= 1_000_000:  # Millions
        return f"{marketcap / 1_000_000:.2f}M"
    elif marketcap >= 1_000:  # Thousands
        return f"{marketcap / 1_000:.2f}K"
    else:
        return f"{marketcap:.2f}"  # Less than a thousand, show raw value


def prepare_marketcap_data(df_original):
    df_marketcap = df_original.copy()
    # Apply the conversion to relevant price columns
    for col in ['open', 'high', 'low', 'close']:  # Ensure these column names match your DataFrame
        if col in df_marketcap.columns:
            df_marketcap[col] = df_marketcap[col] * 1_000_000_000
    return df_marketcap
