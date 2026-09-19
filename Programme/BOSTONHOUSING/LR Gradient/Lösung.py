import matplotlib.pyplot as plt, random, threading, time, math
import sympy as sp
from tqdm import tqdm

def f(x):
    return 0.1 * x**6 - 1.5 * x**4 + 4 * x**2 + x

fx = "0.1 * x**6 - 1.5 * x**4 + 4 * x**2 + x"

def df(x):
    return 0.6 * x**5 - 6 * x**3 + 8 * x + 1

x = sp.symbols("x")
dfx = sp.diff(fx, x)

X = [x/250 for x in range(-1000, 1001)]
Y = [f(x) for x in X]

def main():
    max_iterationen = 10000
    x_start = random.choice(X)
    x_verlauf = [x_start]

    for iteration in tqdm(range(max_iterationen)):
        x_iteration = x_verlauf[iteration]
        steigung_x_iteration = df(x_iteration)
        x_neu = x_iteration - 0.001 * steigung_x_iteration
        x_verlauf.append(x_neu)
        if x_iteration == x_verlauf[iteration - 1]:
            break

    plt.plot(X, Y)
    plt.scatter(x_verlauf, [f(x) for x in x_verlauf])
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.title("$0.1 * x^6 - 1.5 * x^4 + 4 * x^2 + x$")
    return x_verlauf[-1]

x_y_min = math.inf
for i in tqdm(range(100)):
    temp = main()
    if temp < x_y_min:
        x_y_min = temp
print(x_y_min, f(x_y_min))
print(fx, dfx)
plt.show()