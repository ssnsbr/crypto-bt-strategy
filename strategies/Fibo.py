
# [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597, 2584, 4181, 6765, 10946, 17711, 28657, 46368, 75025, 121393, 196418, 317811, 514229, 832040, 1346269, 2178309, 3524578, 5702887]
# [0.146,0.236,0.382,0.500,0.618,0.786,1.000,1.272,1.382,1.500,1.618,2,2.618,4.236]
# [0.001, 0.001, 0.002, 0.003, 0.005, 0.008, 0.013, 0.021, 0.027, 0.034, 0.034, 0.044, 0.056, 0.056, 0.071, 0.09, 0.09,
# 0.115, 0.146, 0.146, 0.186,

from numpy import sqrt
Fibonacci_Levels = [0.013, 0.021, 0.027, 0.034, 0.044, 0.056, 0.071, 0.09, 0.115, 0.146, 0.236, 0.382, 0.500, 0.618, 0.786, 1.000, 1.272, 1.382, 1.500, 1.618, 2, 2.618, 3.33, 4.236]
Fibonacci_Retracement = [0.146, 0.236, 0.382, 0.500, 0.618, 0.786]
Fibonacci_Extension = [1.000, 1.272, 1.382, 1.500, 1.618, 2, 2.618, 3.33, 4.236]
Fibonacci_Retracement_important = [0.236, 0.382, 0.500, 0.618, 0.786]
Fibonacci_Extension_important = [1.000, 1.272, 1.618, 2, 2.618]


def fibos():
    f = [1, 1, 2, 3]
    for i in range(30):
        f.append(f[-2] + f[-1])
    return f


fs = fibos()
print(fs)
fs.reverse()
print(fs)
r = []
for i in (fs):
    r.append(round(fs[15] / i, 3))
    r.append(round(sqrt(fs[15] / i), 3))
r.sort()
print(r)
[0.115, 0.146, 0.186, 0.236, 0.3, 0.382, 0.618, 0.786, 1.0, 1.272, 1.618, 2.058, 2.618, 3.33, 4.236, 4.236, 5.388, 6.854, 6.854, 8.719, 11.089, 11.09, 14.11, 17.934, 17.944, 22.861, 28.917, 29.035, 37.332, 45.722, 46.978, 64.661, 64.661, 76.018, 122.971, 199.095, 321.615, 522.625, 836.2, 1393.667, 2090.5, 4181.0, 4181.0]
