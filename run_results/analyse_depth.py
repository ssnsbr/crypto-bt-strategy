
# main_list_str = d["main_list"].values[1]  # string from CSV
# main_list = ast.literal_eval(main_list_str)  # convert to actual list of tuples

# df = analyse_main_list(main_list)
import ast
from collections import Counter
from datetime import datetime
import os

import numpy as np
import pandas as pd


def analyse_counter_list(counter_list):
    # [RUN] counter_list [3, 1, 1, 4, 2, 3, 1, 1, 2, 1, -4, -1]
    #  3 means we had ib ba ba tp
    # -4 means we had ib ba ba ba sl
    # -1 means ib sl / dead coin / end
    # +1 means ib tp
    if not counter_list:
        return {"error": "Empty counter_list"}

    sl_max_count = min(counter_list)
    tp_max_count = max(counter_list)
    if (-1 * sl_max_count != tp_max_count):
        print("⚠️ Something may be wrong with the counter_list:", tp_max_count, sl_max_count, counter_list)
    buys = sum(abs(x) for x in counter_list)
    tp_list = [c for c in counter_list if c > 0]
    loss_list = [c for c in counter_list if c < 0]

    len_total = len(counter_list)
    tp_count = len(tp_list)
    loss_count = len(loss_list)
    # -1 = dead coin or early end
    end_count = len([c for c in loss_list if (c != sl_max_count)])
    sl_count = loss_count - end_count

    mean_tp_depth = float(np.mean(tp_list) if tp_list else 0)

    values, counts = np.unique(counter_list, return_counts=True)
    # depth_dict = dict(zip(values, counts))
    depth_dict = {int(v): int(c) for v, c in zip(values, counts)}

    return {
        "buys": buys,
        "sells": len_total,
        "tp_list": tp_list,
        "loss_list": loss_list,
        "len_total": len_total,
        "tp_count": tp_count,
        "loss_count": loss_count,
        "end_count": end_count,
        "sl_count": sl_count,
        "mean_tp_depth": mean_tp_depth,
        "depth_dict": depth_dict,
        "tp_max_count": tp_max_count,
        "sl_max_count": sl_max_count
    }


def analyse_main_list(main_list):
    events = [e[0] for e in main_list]
    prices = [e[1] for e in main_list]
    indexes = [e[2] for e in main_list]
    datetimes = [e[3] for e in main_list]

    segments = []
    current = []

    for e, p, i, d in zip(events, prices, indexes, datetimes):
        current.append((e, p, i, d))
        if e in ['tp', 'sl', 'd', 'e']:  # trade ends
            segments.append(current)
            current = []

    # now each segment = one trade cycle
    stats = []
    for s in segments:
        ib_price = s[0][1]
        end_price = s[-1][1]

        ib_index = s[0][2]
        end_index = s[-1][2]

        # convert strings to datetime objects
        ib_datetime = datetime.fromisoformat(s[0][3])
        end_datetime = datetime.fromisoformat(s[-1][3])

        event_types = [x[0] for x in s]
        depth = event_types.count('ba') + 1  # ib + ba
        outcome = s[-1][0]
        stats.append({
            "depth": depth,
            "ib_price": ib_price,
            "end_price": end_price,
            "ib_index": ib_index,
            "end_index": end_index,
            "ib_datetime": ib_datetime,
            "end_datetime": end_datetime,
            "len_datetime": end_datetime - ib_datetime,

            "outcome": outcome,
            "price_ratio": end_price / ib_price if ib_price else 0
        })
    tmpdf = pd.DataFrame(stats)
    # print(tmpdf.groupby('depth')['ib_price'].mean())
    # print(tmpdf.groupby('depth')['price_ratio'].mean())
    return tmpdf


def analys_one_token_list(row):
    # print(row["counter_list"],"to",ast.literal_eval(row["counter_list"]))
    counter_list = ast.literal_eval(row["counter_list"])
    main_list = ast.literal_eval(row["main_list"])
    result_of_counter = None
    result_of_main = None
    if len(counter_list) > 0:
        result_of_counter = analyse_counter_list(counter_list)
        # print(result_of_counter)
    # print("------Analys Main List------")
    result_of_main = None
    if len(main_list) > 0:
        result_of_main = analyse_main_list(main_list)
        # print(result_of_main)
    return result_of_counter, result_of_main


def analys_one_df_of_tokens(rdf):
    list_result_of_counter = []
    for i, row in rdf.iterrows():
        result_of_counter, result_of_main = analys_one_token_list(row)
        if result_of_counter is not None:
            list_result_of_counter.append(result_of_counter)
    ndf = pd.DataFrame(list_result_of_counter)
    print("--" * 10, f"ndf shape {ndf.shape}", "--" * 10)
    return ndf


def analyse_depth_dict(ndf):
    # ndf["depth_dict"]
    combined = Counter()
    for d in ndf["depth_dict"]:
        combined.update(d)
    sorted_combined = dict(sorted(combined.items()))
    # print(sorted_combined)
    return sorted_combined


def is_sl(depth, count, sizes, ba_factor=0.8, tp_factor=1.2, sl_factor=0.7):
    amount = 0
    pow = 0
    # depth = -4 is 4 meaning size[3]*0.8
    abs_depth = depth * -1
    while abs_depth > 0:
        power = sl_factor * (ba_factor ** pow)
        amount = amount + sizes[abs_depth - 1] * (1 - power)
        # print(f'{sizes[abs_depth-1]}* 1 -',  int(pow)*"0.8*" ,"=",sizes[abs_depth-1] * ( 1 - power))
        abs_depth = abs_depth - 1
        pow = pow + 1
    # print(f" ============================ {count} * {amount} = {count * amount}")
    total_lost = count * amount
    return total_lost * -1


def is_tp(depth, count, sizes, ba_factor=0.8, tp_factor=1.2, sl_factor=0.7):
    amount = 0
    pow = 0
    # depth = 4 is 4 meaning size[3]*0.8
    abs_depth = depth
    while abs_depth > 0:
        power = ((ba_factor ** pow) * tp_factor)
        amount = amount + sizes[abs_depth - 1] * (power - 1)
        # print(f'{sizes[abs_depth-1]}* 1 -',  int(pow)*"0.8*" ,"* 1.2=",sizes[abs_depth-1] * (power - 1 ))
        abs_depth = abs_depth - 1
        pow = pow + 1
    # print(f" ============================ {count} * {amount} = {count * amount}")
    p = count * amount
    return p


def get_row_res(depth_distribution, sizes, ba_factor=0.8, tp_factor=1.2, sl_factor=0.7):
    a = 0
    for depth, count in depth_distribution.items():
        if depth < 0:
            s = is_sl(depth, count, sizes, ba_factor=ba_factor, tp_factor=tp_factor, sl_factor=sl_factor)
        else:
            s = is_tp(depth, count, sizes, ba_factor=ba_factor, tp_factor=tp_factor, sl_factor=sl_factor)
        a = a + s
        # print(depth,count,s)
        # print(a)
    return a


if __name__ == '__main__':
    results_folder = "/content/drive/MyDrive/charts/results/"
    data_analys_list = []
    for f in os.listdir(results_folder):
        if f.endswith('.csv') and not f.startswith("all_portfolio_histories") and not f.endswith("_ath.csv"):
            lenstr = f.split("_")[-2].split("-")[-1]
            if int(lenstr) > 100:
                rdf = pd.read_csv(os.path.join(results_folder, f))
                if "main_list" in rdf.columns:
                    print("--" * 10, f, "--" * 10)
                    ndf = analys_one_df_of_tokens(rdf)
                    sorted_combined = analyse_depth_dict(ndf)
                    print(f'for ${f} sorted_combined is ${sorted_combined}')

                    # print(result)
                    # print(analyse_counter_list(result["counter_list"]))
                    # print(analyse_main_list(result["main_list"]))
                    # # e/100
                    data_analys_list.append(sorted_combined)

    # Create comprehensive results DataFrame
    data_analys_df = pd.DataFrame(data_analys_list)

    # Display the results
    print("Analysis Summary:")
    print("=" * 80)
    print(data_analys_df.columns)
    print(data_analys_df)
