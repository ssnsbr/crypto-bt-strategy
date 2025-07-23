import pandas as pd
import numpy as np
import datetime


def generate_elliott_wave_data(
    start_market_cap=1000,
    target_market_cap_wave5=100_000,
    initial_volume=1_000_000,
    candles_per_wave_segment=50,  # Number of candles for each sub-wave (e.g., Wave 1, Wave A, Wave B, etc.)
    price_noise_factor=0.01,
    volume_noise_factor=0.1,
    start_date=datetime.datetime(2025, 1, 1)
):
    """
    Generates synthetic memecoin price data following Elliott Wave Theory.

    Args:
        start_market_cap (int): Starting market capitalization.
        target_market_cap_wave5 (int): Target market capitalization at the end of Wave 5.
        initial_volume (int): Starting trading volume.
        candles_per_wave_segment (int): Number of data points (candles) per segment of a wave.
        price_noise_factor (float): Multiplier for random price fluctuations.
        volume_noise_factor (float): Multiplier for random volume fluctuations.
        start_date (datetime.datetime): Starting date for the data.

    Returns:
        pd.DataFrame: A DataFrame with 'Open', 'Close', 'High', 'Low', 'Volume', 'MarketCap', and 'Candle' columns.
    """

    data = []
    current_market_cap = start_market_cap
    current_volume = initial_volume
    base_price_factor = 1  # Used to scale price movements relative to the initial price

    # --- Impulse Wave 1 --- (5 waves up)
    # Let's say Wave 1 targets a moderate increase
    wave1_end_mc = start_market_cap * 3  # Example: 3x increase
    wave1_length = wave1_end_mc - start_market_cap

    # Sub-waves of Wave 1 (i, ii, iii, iv, v)
    # For simplicity, we'll model impulse waves as a continuous climb with corrections
    # We are simulating daily data, so each wave will have 'candles_per_wave_segment' days

    # Wave 1 (overall)
    wave1_open_mc = current_market_cap
    for i in range(candles_per_wave_segment):
        mc = wave1_open_mc + (wave1_length / candles_per_wave_segment) * (i + 1)

        # Add some oscillation within the trend
        oscillation = np.sin(i / (candles_per_wave_segment / (2 * np.pi))) * (wave1_length / candles_per_wave_segment) * 0.1
        mc += oscillation

        close_mc = max(start_market_cap, mc + np.random.uniform(-1, 1) * price_noise_factor * wave1_length)
        open_mc = current_market_cap  # Open is previous close for simulation purposes
        high_mc = max(open_mc, close_mc) * (1 + np.random.uniform(0, price_noise_factor))
        low_mc = min(open_mc, close_mc) * (1 - np.random.uniform(0, price_noise_factor))

        vol = current_volume * (1 + np.random.uniform(-volume_noise_factor, volume_noise_factor))
        vol = max(initial_volume * 0.5, vol)  # Ensure volume doesn't drop too low

        data.append({
            'MarketCap': close_mc,
            'Open_MC': open_mc,
            'High_MC': high_mc,
            'Low_MC': low_mc,
            'Volume': vol,
            'Candle': 'Wave 1'
        })
        current_market_cap = close_mc
        current_volume = vol

    wave1_high_mc = max([d['High_MC'] for d in data if d['Candle'] == 'Wave 1'])
    wave1_low_mc = min([d['Low_MC'] for d in data if d['Candle'] == 'Wave 1'])

    # --- Corrective Wave 2 --- (retraces Wave 1)
    # Typical retracements: 0.5, 0.618, 0.786
    fib_retracement_level_wave2 = np.random.choice([0.5, 0.618, 0.786])
    retracement_amount = (current_market_cap - wave1_open_mc) * fib_retracement_level_wave2
    wave2_target_mc = current_market_cap - retracement_amount

    wave2_start_mc = current_market_cap
    for i in range(candles_per_wave_segment):
        mc = wave2_start_mc - (retracement_amount / candles_per_wave_segment) * (i + 1)

        # Add some oscillation within the trend
        oscillation = np.sin(i / (candles_per_wave_segment / (2 * np.pi))) * (retracement_amount / candles_per_wave_segment) * 0.1
        mc += oscillation

        close_mc = max(start_market_cap, mc + np.random.uniform(-1, 1) * price_noise_factor * retracement_amount)
        open_mc = current_market_cap
        high_mc = max(open_mc, close_mc) * (1 + np.random.uniform(0, price_noise_factor))
        low_mc = min(open_mc, close_mc) * (1 - np.random.uniform(0, price_noise_factor))

        vol = current_volume * (1 + np.random.uniform(-volume_noise_factor, volume_noise_factor) * 0.5)  # Volume decreases in correction
        vol = max(initial_volume * 0.3, vol)

        data.append({
            'MarketCap': close_mc,
            'Open_MC': open_mc,
            'High_MC': high_mc,
            'Low_MC': low_mc,
            'Volume': vol,
            'Candle': 'Wave 2'
        })
        current_market_cap = close_mc
        current_volume = vol

    # --- Impulse Wave 3 --- (strongest, never shortest)
    # Typically 1.618 * Wave 1, or can be much larger. Let's aim for a significant jump.
    wave3_start_mc = current_market_cap
    wave3_length_from_wave1_base = wave1_end_mc - wave1_open_mc
    wave3_target_mc = wave3_start_mc + wave3_length_from_wave1_base * np.random.uniform(2.0, 4.0)  # Larger than 1.618 for a memecoin pump
    wave3_length = wave3_target_mc - wave3_start_mc

    for i in range(candles_per_wave_segment * 2):  # Make Wave 3 longer and more pronounced
        mc = wave3_start_mc + (wave3_length / (candles_per_wave_segment * 2)) * (i + 1)

        # Add some oscillation within the trend
        oscillation = np.sin(i / (candles_per_wave_segment * 2 / (2 * np.pi))) * (wave3_length / (candles_per_wave_segment * 2)) * 0.05
        mc += oscillation

        close_mc = mc + np.random.uniform(-1, 1) * price_noise_factor * wave3_length * 0.2
        open_mc = current_market_cap
        high_mc = max(open_mc, close_mc) * (1 + np.random.uniform(0, price_noise_factor))
        low_mc = min(open_mc, close_mc) * (1 - np.random.uniform(0, price_noise_factor))

        vol = current_volume * (1 + np.random.uniform(0.1, volume_noise_factor * 2))  # Volume increases significantly
        vol = max(initial_volume * 1.5, vol)

        data.append({
            'MarketCap': close_mc,
            'Open_MC': open_mc,
            'High_MC': high_mc,
            'Low_MC': low_mc,
            'Volume': vol,
            'Candle': 'Wave 3'
        })
        current_market_cap = close_mc
        current_volume = vol

    # --- Corrective Wave 4 --- (no overlap with Wave 1's price territory)
    # Wave 4 retraces Wave 3.
    # Check Wave 1's highest low to ensure no overlap
    wave4_start_mc = current_market_cap
    fib_retracement_level_wave4 = np.random.choice([0.236, 0.382])  # Often shallow

    wave3_price_change = wave3_target_mc - wave3_start_mc
    retracement_amount_wave4 = wave3_price_change * fib_retracement_level_wave4
    wave4_target_mc = wave4_start_mc - retracement_amount_wave4

    # Ensure Wave 4 does not overlap Wave 1
    # For simplicity, we define "overlap" as the low of Wave 4 going below the high of Wave 1.
    # However, Elliott Wave rule is that Wave 4 doesn't go below the *high of Wave 1*.
    # Let's use the low of Wave 2 as a proxy for the start of the impulse, so Wave 4 shouldn't go below wave 1's peak.
    # For now, we'll enforce that the low of Wave 4 is above the start_market_cap + a buffer.

    # A more robust check would involve storing the precise price range of Wave 1
    # For now, we'll make sure it doesn't drop to its beginning levels
    wave1_peak_mc_for_overlap_check = max([d['High_MC'] for d in data if d['Candle'] == 'Wave 1'])  # Simple rule of not overlapping

    # Adjust target if it violates the rule
    if wave4_target_mc < wave1_peak_mc_for_overlap_check * 0.8:  # Simple check to avoid major overlap
        wave4_target_mc = wave1_peak_mc_for_overlap_check * 0.8
        retracement_amount_wave4 = wave4_start_mc - wave4_target_mc

    for i in range(candles_per_wave_segment):
        mc = wave4_start_mc - (retracement_amount_wave4 / candles_per_wave_segment) * (i + 1)

        # Add some oscillation within the trend
        oscillation = np.sin(i / (candles_per_wave_segment / (2 * np.pi))) * (retracement_amount_wave4 / candles_per_wave_segment) * 0.1
        mc += oscillation

        close_mc = mc + np.random.uniform(-1, 1) * price_noise_factor * retracement_amount_wave4 * 0.2
        open_mc = current_market_cap
        high_mc = max(open_mc, close_mc) * (1 + np.random.uniform(0, price_noise_factor))
        low_mc = min(open_mc, close_mc) * (1 - np.random.uniform(0, price_noise_factor))

        vol = current_volume * (1 + np.random.uniform(-volume_noise_factor, volume_noise_factor) * 0.5)
        vol = max(initial_volume * 0.5, vol)

        data.append({
            'MarketCap': close_mc,
            'Open_MC': open_mc,
            'High_MC': high_mc,
            'Low_MC': low_mc,
            'Volume': vol,
            'Candle': 'Wave 4'
        })
        current_market_cap = close_mc
        current_volume = vol

    # --- Impulse Wave 5 --- (reaches target)
    wave5_start_mc = current_market_cap
    # Wave 5 could be equal to Wave 1, or 0.618 * Wave 1, or even extended for memecoins.
    # Let's ensure it hits the target_market_cap_wave5.
    wave5_length = target_market_cap_wave5 - wave5_start_mc

    # If the target is not much higher than current, make sure it still has an upward move
    if wave5_length < start_market_cap * 0.1:
        wave5_length = start_market_cap * 0.1  # Ensure some minimal increase
        target_market_cap_wave5 = wave5_start_mc + wave5_length

    for i in range(candles_per_wave_segment):
        mc = wave5_start_mc + (wave5_length / candles_per_wave_segment) * (i + 1)

        # Add some oscillation within the trend
        oscillation = np.sin(i / (candles_per_wave_segment / (2 * np.pi))) * (wave5_length / candles_per_wave_segment) * 0.05
        mc += oscillation

        close_mc = mc + np.random.uniform(-1, 1) * price_noise_factor * wave5_length * 0.1
        close_mc = min(close_mc, target_market_cap_wave5 * 1.05)  # Cap at target with slight overshoot
        open_mc = current_market_cap
        high_mc = max(open_mc, close_mc) * (1 + np.random.uniform(0, price_noise_factor))
        low_mc = min(open_mc, close_mc) * (1 - np.random.uniform(0, price_noise_factor))

        vol = current_volume * (1 + np.random.uniform(-volume_noise_factor, volume_noise_factor))  # Volume can taper off
        vol = max(initial_volume * 0.8, vol)

        data.append({
            'MarketCap': close_mc,
            'Open_MC': open_mc,
            'High_MC': high_mc,
            'Low_MC': low_mc,
            'Volume': vol,
            'Candle': 'Wave 5'
        })
        current_market_cap = close_mc
        current_volume = vol

    # --- Corrective Wave A ---
    waveA_start_mc = current_market_cap
    waveA_drop_factor = np.random.uniform(0.3, 0.6)  # Significant drop after impulse
    waveA_target_mc = waveA_start_mc * (1 - waveA_drop_factor)
    waveA_length = waveA_start_mc - waveA_target_mc

    for i in range(candles_per_wave_segment):
        mc = waveA_start_mc - (waveA_length / candles_per_wave_segment) * (i + 1)

        # Add some oscillation within the trend
        oscillation = np.sin(i / (candles_per_wave_segment / (2 * np.pi))) * (waveA_length / candles_per_wave_segment) * 0.1
        mc += oscillation

        close_mc = mc + np.random.uniform(-1, 1) * price_noise_factor * waveA_length * 0.2
        open_mc = current_market_cap
        high_mc = max(open_mc, close_mc) * (1 + np.random.uniform(0, price_noise_factor))
        low_mc = min(open_mc, close_mc) * (1 - np.random.uniform(0, price_noise_factor))

        vol = current_volume * (1 + np.random.uniform(-volume_noise_factor * 0.8, volume_noise_factor * 0.2))  # Volume can remain high or drop
        vol = max(initial_volume * 0.3, vol)

        data.append({
            'MarketCap': close_mc,
            'Open_MC': open_mc,
            'High_MC': high_mc,
            'Low_MC': low_mc,
            'Volume': vol,
            'Candle': 'Wave A'
        })
        current_market_cap = close_mc
        current_volume = vol

    waveA_low_mc = current_market_cap

    # --- Corrective Wave B --- (retraces Wave A)
    fib_retracement_level_waveB = np.random.choice([0.5, 0.618, 0.786])
    retracement_amount_waveB = (waveA_start_mc - waveA_low_mc) * fib_retracement_level_waveB
    waveB_target_mc = waveA_low_mc + retracement_amount_waveB

    waveB_start_mc = current_market_cap
    for i in range(candles_per_wave_segment):
        mc = waveB_start_mc + (retracement_amount_waveB / candles_per_wave_segment) * (i + 1)

        # Add some oscillation within the trend
        oscillation = np.sin(i / (candles_per_wave_segment / (2 * np.pi))) * (retracement_amount_waveB / candles_per_wave_segment) * 0.1
        mc += oscillation

        close_mc = mc + np.random.uniform(-1, 1) * price_noise_factor * retracement_amount_waveB * 0.2
        open_mc = current_market_cap
        high_mc = max(open_mc, close_mc) * (1 + np.random.uniform(0, price_noise_factor))
        low_mc = min(open_mc, close_mc) * (1 - np.random.uniform(0, price_noise_factor))

        vol = current_volume * (1 + np.random.uniform(-volume_noise_factor * 0.5, volume_noise_factor * 0.5))

        data.append({
            'MarketCap': close_mc,
            'Open_MC': open_mc,
            'High_MC': high_mc,
            'Low_MC': low_mc,
            'Volume': vol,
            'Candle': 'Wave B'
        })
        current_market_cap = close_mc
        current_volume = vol

    # --- Corrective Wave C --- (extends beyond Wave A)
    # Often 1.0 or 1.618 times Wave A's length
    waveC_start_mc = current_market_cap
    waveC_extension_factor = np.random.choice([1.0, 1.618])
    waveC_length = (waveA_start_mc - waveA_low_mc) * waveC_extension_factor
    waveC_target_mc = waveC_start_mc - waveC_length

    # Ensure it doesn't drop to absurdly low levels
    if waveC_target_mc < start_market_cap * 0.5:
        waveC_target_mc = start_market_cap * 0.5
        waveC_length = waveC_start_mc - waveC_target_mc

    for i in range(candles_per_wave_segment):
        mc = waveC_start_mc - (waveC_length / candles_per_wave_segment) * (i + 1)

        # Add some oscillation within the trend
        oscillation = np.sin(i / (candles_per_wave_segment / (2 * np.pi))) * (waveC_length / candles_per_wave_segment) * 0.1
        mc += oscillation

        close_mc = mc + np.random.uniform(-1, 1) * price_noise_factor * waveC_length * 0.2
        close_mc = max(start_market_cap * 0.1, close_mc)  # Don't go below almost zero
        open_mc = current_market_cap
        high_mc = max(open_mc, close_mc) * (1 + np.random.uniform(0, price_noise_factor))
        low_mc = min(open_mc, close_mc) * (1 - np.random.uniform(0, price_noise_factor))

        vol = current_volume * (1 + np.random.uniform(-volume_noise_factor * 0.8, volume_noise_factor * 0.2))  # Volume can pick up on the final drop

        data.append({
            'MarketCap': close_mc,
            'Open_MC': open_mc,
            'High_MC': high_mc,
            'Low_MC': low_mc,
            'Volume': vol,
            'Candle': 'Wave C'
        })
        current_market_cap = close_mc
        current_volume = vol

    df = pd.DataFrame(data)

    # Convert Market Cap to Price (assuming 1B circulating supply)
    df['Close'] = df['MarketCap'] / 1_000_000_000
    df['Open'] = df['Open_MC'] / 1_000_000_000
    df['High'] = df['High_MC'] / 1_000_000_000
    df['Low'] = df['Low_MC'] / 1_000_000_000

    # Ensure OHLC integrity
    df['High'] = df[['Open', 'Close', 'High']].max(axis=1) * (1 + np.random.uniform(0, price_noise_factor * 0.5))
    df['Low'] = df[['Open', 'Close', 'Low']].min(axis=1) * (1 - np.random.uniform(0, price_noise_factor * 0.5))

    # Clean up temporary market cap columns
    df = df.drop(columns=['MarketCap', 'Open_MC', 'High_MC', 'Low_MC'])

    # Add datetime index
    df['Date'] = [start_date + datetime.timedelta(days=i) for i in range(len(df))]
    df = df.set_index('Date')

    # Reorder columns
    df = df[['Open', 'Close', 'High', 'Low', 'Volume', 'Candle']]

    return df


# Generate the DataFrame
memecoin_data = generate_elliott_wave_data(
    start_market_cap=1_000_000,  # Starting at 1 million market cap
    target_market_cap_wave5=100_000_000,  # Up to 100 million market cap for Wave 5 end
    candles_per_wave_segment=30,  # Shorter segments for quicker generation
    price_noise_factor=0.005,
    volume_noise_factor=0.08
)

print(memecoin_data.head())
print("\n--- Market Cap Progression ---")
print(memecoin_data['Close'].plot(title='Simulated Memecoin Price Action').get_figure())
print(memecoin_data.tail())

memecoin_data['Close'].plot(title='Simulated Memecoin Price Action').get_figure()
plot.show()