import sklearn
import matplotlib.pyplot as plt
from tqdm import tqdm

y, x = sklearn.datasets.make_regression(n_samples=10000001, noise=20, n_features=1, n_targets=1)

x = [i for i in range(len(y))]
y = [float(wert) for wert in y]

t = sum(y) / len(y)

m = 0

dsx = sum(x) / len(x)
dsy = sum(y) / len(y)

abx = [dsx - wert for wert in x]
aby = [dsy - wert for wert in y]

prxy = [(abx[i] * aby[i]) for i in range(len(abx) - 1)]

qdx = [wert ** 2 for wert in abx]

m1 = sum(prxy) / sum(qdx)

xg = [i for i in range(min(x), max(x))]
yg = []
for zahl in tqdm(xg):
    yg.append(m1 * zahl + t)

cm = 1/2.54
plt.subplots(figsize=(25 * cm, 15 * cm))
# plt.plot(x, y, c="r")
plt.plot(xg, yg, label="Methode 1", c="c")
ydif_1 = [abs((yg[i] - y[i]) ** 2) for i in range(len(y) - 1)]

m = []
for i in tqdm(range(len(y) - 1)):
    try:
        m.append((y[i] - y[i + 1]) / (x[i] - x[i + 1]))
    except:
        pass
    try:
        m.append((y[i] - y[i + 2]) / (x[i] - x[i + 2]))
    except:
        pass
m2 = sum(m) / len(m)

xg = [i for i in range(min(x), max(x))]
yg = []
for zahl in tqdm(xg):
    yg.append(m2 * zahl + t)

plt.plot(xg, yg, label="Methode 2", c="k")
ydif_2 = [abs((yg[i] - y[i]) ** 2) for i in range(len(y) - 1)]

print()
print("Steigung 1: ", m1)
print("Steigung 2: ", m2)
print()
print("Gesamtabstand Methode 1: ", sum(ydif_1))
print("Gesamtabstand Methode 2: ", sum(ydif_2))
print()

plt.scatter(x, y, s=3, c="r")
plt.legend(loc="upper right")
plt.title("Regression")
plt.show()