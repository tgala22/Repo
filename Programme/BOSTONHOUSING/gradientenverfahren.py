import matplotlib.pyplot as plt, random


class Var:
    def __init__(self, value, derivative=0.0):
        self.v = value # Der Wert
        self.d = derivative # Die Ableitung

    def __add__(self, other):
        # Falls "other" eine normale Zahl ist, wandle sie in Var um
        if not isinstance(other, Var):
            other = Var(other)
        return Var(self.v + other.v, self.d + other.d)

    def __mul__(self, other):
        if not isinstance(other, Var):
            other = Var(other)
        # Produktregel: (u*v)' = u'*v + u*v'
        return Var(self.v * other.v, self.d * other.v + self.v * other.d)
    
    def __pow__(self, exponent):
        return Var(self.v ** exponent, exponent * self.v ** (exponent - 1) * self.d)
    
    def __sub__(self, other):
        if not isinstance(other, Var):
            other = Var(other)
        return Var(self.v - other.v, self.d - other.d)
    
    def __truediv__(self, other):
        if not isinstance(other, Var):
            other = Var(other)
        return Var(self.v / other.v, (self.d * other.v - self.v * other.d) / (other.v ** 2))

    # Erlaubt auch Rechnungen wie "2 + x" statt nur "x + 2"
    __radd__ = __add__
    __rmul__ = __mul__

    def __rsub__(self, other):
        return Var(other).__sub__(self)

    def __rtruediv__(self, other):
        return Var(other).__truediv__(self)

    def __repr__(self):
        return f"Wert: {self.v}, Ableitung: {self.d}"

    def __sub__(self, other):
        return Var(self.v - other.v, self.d - other.d)

def f(x):
    return x**2

def g(x):
    return 0.1 * x**6 - 1.5 * x**4 + 4 * x**2 + x

def g_float(x):
    return g(Var(x)).v


X = [x/250 for x in range(-1000, 1001)]
y = [g(x) for x in X]

max_iterationen = 100

x_start = random.choice(X)

x_verlauf = [x_start]
for iteration in range(max_iterationen):
    x_iteration = x_verlauf[iteration]

    x_var = Var(x_iteration, 1.0)
    y_var = g(x_var)

    steigung_x_iteration = y_var.d

    x_neu = x_iteration - 0.01 * steigung_x_iteration

    x_verlauf.append(x_neu)


plt.plot(X, y)
plt.scatter(x_verlauf, [g(x) for x in x_verlauf])
plt.xlabel("x")
plt.ylabel("y")
plt.title("Funktionsgraph")
plt.show()

# TODO
# Optimieren: Lernrate, Startwert, max_iterations