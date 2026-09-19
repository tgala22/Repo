import pandas as pd
# Daten einlesen (df wie "data frame")
df = pd.read_csv("data.csv")

# Daten ohne die Spalte mit den vorherzusagenden Werten sind X
X = df.drop(columns="medv")
# Die Spalte mit den vorherzusagenden Werten ist y
y = df["medv"].values
def Fehlerfunktion(x, w, b, y):
    y_vorhersage = w * x + b
    zwischenwert = y - y_vorhersage
    fehler = zwischenwert ** 2
    return fehler










