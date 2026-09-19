import matplotlib.pyplot as plt, csv, threading, numpy as np
from tqdm import tqdm
from numpy import linalg

def main():
    with open("BostonHousing.csv")as f:
        daten = list(csv.reader(f))
        spaltennamen = daten.pop(0)

    for i in tqdm(range(len(daten))):
        for j in range(len(daten[i])):
            daten[i][j] = float(daten[i][j])

    S0 = [temp[0] for temp in daten]
    S1 = [temp[1] for temp in daten]
    S2 = [temp[2] for temp in daten]
    S3 = [temp[3] for temp in daten]
    S4 = [temp[4] for temp in daten]
    S5 = [temp[5] for temp in daten]
    S6 = [temp[6] for temp in daten]
    S7 = [temp[7] for temp in daten]
    S8 = [temp[8] for temp in daten]
    S9 = [temp[9] for temp in daten]
    S10 = [temp[10] for temp in daten]
    S11 = [temp[11] for temp in daten]
    S12 = [temp[12] for temp in daten]
    S13 = [temp[13] for temp in daten]

    daten_sortiert = daten
    daten_sortiert.sort(key = lambda x: x[-1])

    plt.subplot(2, 2, 1)
    plt.scatter([i for i in range(len(daten_sortiert))],[temp[0] for temp in daten_sortiert], c="y", s=3)
    plt.scatter([i for i in range(len(daten_sortiert))],[np.log(temp[0]) for temp in daten_sortiert], c="b", s=3)
    x = [i for i in range(len(S0))]
    y = [np.log(temp[0]) for temp in daten_sortiert]
    t = sum(y)/len(y)
    dsx = sum(x) / len(x)
    dsy = sum(y) / len(y)
    abx = [dsx - wert for wert in x]
    aby = [dsy - wert for wert in y]
    prxy = [(abx[i] * aby[i]) for i in range(len(abx) - 1)]
    qdx = [wert ** 2 for wert in abx]
    m = sum(prxy) / sum(qdx)
    yg = []
    for zahl in tqdm(x):
        yg.append(m * zahl + t)
    plt.plot(x, yg, c="k")

    plt.subplot(2, 2, 2)
    plt.scatter([i for i in range(len(daten_sortiert))],[temp[5] for temp in daten_sortiert], c="y", s=3)
    plt.scatter([i for i in range(len(daten_sortiert))],[np.log(temp[5]) for temp in daten_sortiert], c="b", s=3)
    x = [i for i in range(len(S5))]
    y = [np.log(temp[5]) for temp in daten_sortiert]
    t = sum(y)/len(y)
    dsx = sum(x) / len(x)
    dsy = sum(y) / len(y)
    abx = [dsx - wert for wert in x]
    aby = [dsy - wert for wert in y]
    prxy = [(abx[i] * aby[i]) for i in range(len(abx) - 1)]
    qdx = [wert ** 2 for wert in abx]
    m = sum(prxy) / sum(qdx)
    yg = []
    for zahl in tqdm(x):
        yg.append(m * zahl + t)
    plt.plot(x, yg, c="k")

    plt.subplot(2, 2, 3)
    plt.scatter([i for i in range(len(daten_sortiert))],[temp[11] for temp in daten_sortiert], c="y", s=3)
    plt.scatter([i for i in range(len(daten_sortiert))],[np.log(temp[11]) for temp in daten_sortiert], c="b", s=3)
    x = [i for i in range(len(S11))]
    y = [np.log(temp[11]) for temp in daten_sortiert]
    t = sum(y)/len(y)
    dsx = sum(x) / len(x)
    dsy = sum(y) / len(y)
    abx = [dsx - wert for wert in x]
    aby = [dsy - wert for wert in y]
    prxy = [(abx[i] * aby[i]) for i in range(len(abx) - 1)]
    qdx = [wert ** 2 for wert in abx]
    m = sum(prxy) / sum(qdx)
    yg = []
    for zahl in tqdm(x):
        yg.append(m * zahl + t)
    plt.plot(x, yg, c="k")

    plt.subplot(2, 2, 4)
    plt.scatter([i for i in range(len(daten_sortiert))],[temp[12] for temp in daten_sortiert], c="y", s=3)
    plt.scatter([i for i in range(len(daten_sortiert))],[np.log(temp[12]) for temp in daten_sortiert], c="b", s=3)
    x = [i for i in range(len(S12))]
    y = [np.log(temp[12]) for temp in daten_sortiert]
    t = sum(y)/len(y)
    dsx = sum(x) / len(x)
    dsy = sum(y) / len(y)
    abx = [dsx - wert for wert in x]
    aby = [dsy - wert for wert in y]
    prxy = [(abx[i] * aby[i]) for i in range(len(abx) - 1)]
    qdx = [wert ** 2 for wert in abx]
    m = sum(prxy) / sum(qdx)
    yg = []
    for zahl in tqdm(x):
        yg.append(m * zahl + t)
    plt.plot(x, yg, c="k")

    daten = [temp[:-1] for temp in daten]
    daten = np.array(daten)

    y = S13
    w = linalg.inv(daten.transpose() @ daten) @ (daten.transpose() @ y)

    gradientJw = (2 * (daten.transpose() @ daten @ w)) - (2 * daten.transpose() @ y)

    plt.show()

main()