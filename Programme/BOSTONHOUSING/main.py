import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Daten einlesen (df wie "data frame")
df = pd.read_csv("data.csv")

# Daten ohne die Spalte mit den vorherzusagenden Werten sind X
X = df.drop(columns="medv")
# Die Spalte mit den vorherzusagenden Werten ist y
y = df["medv"].values

# Daten um eine konstante Spalte ergÃ¤nzen, um den "y-Achsenabschnitt" der Gerade zu simulieren
X["bias"] = 1

# Vorhersage entsprechend der Normalengleichung bestimmen
X_T = X.T
X_T_X = X_T.dot(X)

try:
    X_T_X_inv = np.linalg.inv(X_T_X)
except np.linalg.LinAlgError:
    X_T_X_inv = np.linalg.pinv(X_T_X)

weights = X_T_X_inv.dot(X_T).dot(y)

prediction = X.dot(weights)

# Ergebnisse plotten:
# 1. Vorhersagen vs. tatsächliche Werte
fig, axes = plt.subplots(1, 3, figsize=(14, 5))
ax1 = axes[0]
ax1.scatter(y, prediction, alpha=0.6)
ax1.plot([y.min(), y.max()], [y.min(), y.max()], "r--", lw=2)
ax1.set_xlabel("tatsächliche Werte")
ax1.set_ylabel("Vorhersagen")
ax1.set_title("Vorhersagen vs. tatsächliche Werte")
ax1.grid(True, alpha=0.3)

# 2. Residuen
ax2 = axes[1]
residuals = y - prediction
ax2.scatter(prediction, residuals, alpha=0.6)
ax2.axhline(y=0, color="r", linestyle="--", lw=2)
ax2.set_xlabel("Vorhersagen")
ax2.set_ylabel("Residuen")
ax2.set_title("Residuen")
ax2.grid(True, alpha=0.3)

# 3. Fehlerverteilung
ax4 = axes[2]
error_percent = np.abs(residuals / y) * 100
ax4.hist(error_percent, bins=20, edgecolor="black", alpha=0.7)
ax4.set_xlabel("Prozentualer Fehler")
ax4.set_ylabel("Häufigkeit")
ax4.set_title("Verteilung des prozentualen Fehlers")
ax4.grid(True, alpha=0.3)
    

plt.show()