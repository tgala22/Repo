class Suchbaum:
    def __init__(self):
        self.wurzel = None
    def hinzufügen(self, wert):
        if not self.wurzel:
            self.wurzel = Knoten(wert)
        else:
            self.wurzel.hinzufügen(wert)

    def grahpviz(self):


class Knoten:
    def __init__(self, wert):
        self.wert = wert
        self.linksinks = None
        self.rechts = None
    def hinzufügen(self, wert):
        if wert <= self.wert
            if not self.links = Knoten(wert):
                self.links = Knoten(wert)
            else:
                self.links.hinzufügen(wert)
        else:
            if not self.rechts = Knoten(wert):
                self.rechts = Knoten(wert)
            else:
                self.rechts.hinzufügen(wert)


        

# b = Suchbaum()
# b.hinzufügen(50)
# b.hinzufügen(20)
# b.hinzufügen(80)
# b.hinzufügen(60)

