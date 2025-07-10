
def format_price_to_marketcap(price):
    marketcap = price * 1_000_000_000
    return format_marketcap(marketcap)


def format_marketcap(marketcap):
    """
    Calculates market cap and formats it to K or M.
    """
    if marketcap >= 1_000_000_000:  # Billions
        return f"{marketcap / 1_000_000_000:.2f}B!"
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
