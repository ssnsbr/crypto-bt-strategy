# fibo = [1,1,2,3,5,8,13,21,34,55,89,144,233,377,610,987,1597,2584,4181]
# fibo = [0.145, 0.236, 0.382, 0.5, 0.618, 0.786, 0.886]
# fibo = [0.855, 0.764, 0.618, 0.5, 0.382, 0.214, 0.114]
# fibo = [0.870, 0.775, 0.618, 0.5, 0.382, 0.225, 0.13]
import math
fibo = [1, 0.870, 0.775, 0.618, 0.5, 0.382, 0.225, 0.13]
loss = {}
math.sqrt(0.7861297602813418)
for i in range(1, len(fibo)):
    first = i - 1
    second = i
    r = (1 - fibo[second] / fibo[first])
    r = round(r, 2)
    p = round(fibo[first] / fibo[second], 2)
    print("----")
    print(f"if price goes from {100*fibo[first]:.2f} to {100*fibo[second]} mCap, then it is", f"{r:.2f}", " loss.")
    print(f"if price back from {100*fibo[second]:.2f} to {100*fibo[first]} mCap, then it is", f"{p:.2f}", " profit.")
    loss[f"loss from {fibo[first]} to {fibo[second]}"] = r
print(loss)

first = 100
second = 50
third = 60
start = 1
second_buy = 2
spent = start
portfolio = spent
print(f"-------- start with portfolio = {start} and price {first} mcap.")
portfolio = second / first
loss = (start - portfolio)
p = (first / second)
print(f"-------- price goes from {first} to {second} mCap.")
print("then it is", f"-{loss*100:.0f}%", f"loss. portfolio now=({portfolio})")
print(f"now you need", f"{p*100}% for price to be back at {start}. (back from {second} to {first} mCap)")
portfolio = portfolio + second_buy
spent = spent + second_buy
print(f"if you buy again at {second} mcap, amount of {second_buy}, you have {portfolio} at {second} mcap.")
print(f"-------- price goes from {second} to {third} mCap.")
c = third / second
portfolio = portfolio * c
print("then it is", f" +{(c-1)*100:.0f}%", f"profit. portfolio now=({portfolio})")


def price_go_down(first, second, start=1, new=0.75):
    pnl = second / first
    print(f"-------- price goes from {first} to {second} mCap.", f"-{pnl*100:.0f}%", f"And you need", f"+{(first/second-1)*100}% (back from {second} to {first} mCap)")
    now = new + second / first
    all = start + new
    print(f"if you buy again at {second} mcap, amount of {new} you will have {now} with spent of {all}")
    print(f" you need {all/now}X and {second*(all/now)} mcap.")


def price_go_down_up(first, second, third, start=1):
    portfolio = start
    spent = start
    print("# start with", portfolio)

    pnl1 = second / first
    portfolio = portfolio * pnl1
    print(f"-------- price goes from {first} to {second} mCap.", f"-{pnl1*100:.0f}%", f"And you need", f"+{(first/second-1)*100}% (back from {second} to {first} mCap)")
    print("# portfolio", portfolio)
    pnl2 = round(third / second, 2)
    # print(pnl1,pnl2)
    # print("**** calculating to_buy ", (start * pnl1 * pnl2) - start," / " , (1- pnl2))
    to_buy = start * (pnl1 * pnl2 - 1) / (1 - pnl2)
    to_buy = round(to_buy, 2)
    portfolio = portfolio + to_buy
    spent = spent + to_buy
    print(f"if you buy {to_buy} you would had {to_buy + start*pnl1:.2f} with spent of {spent:.2f}")
    print("# portfolio", portfolio)
    print(f"-------- price goes from {second} to {third} mCap.", f"+{(pnl2-1)*100:.0f}%")
    portfolio = portfolio * pnl2
    print("# portfolio", portfolio, "spent", spent)
    return to_buy


# price_go_down(100,50)
price_go_down_up(100, 38, 50)


for i in range(1, len(fibo)):
    first = i - 1
    second = i
    l = (1 - fibo[second] / fibo[first])
    p = (fibo[first] / fibo[second])
    l = round(l, 2)
    print("----")
    print(f"if price goes from {100*fibo[first]:.2f} to {100*fibo[second]} mCap, then it is", f"-{l:.2f}", f"loss. now=({1-l:.2f})")
    print(f"if price back from {100*fibo[second]:.2f} to {100*fibo[first]} mCap, then it is", f"{p:.2f}", " profit.")

    # print(f"if price goes from {100*fibo[first]:.2f} to {100*fibo[second]} mCap, then you have to buy "
    #                     ,f"{ fibo[second]/fibo[first]:.2f}",f" to get back at {100*fibo[first]:.2f}.")
    # loss[f"loss from {fibo[first]} to {fibo[second]}"] = l
print(loss)
