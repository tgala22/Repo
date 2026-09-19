import random, time 
class Suchbaum:
    def __init__(self):
        self.wurzel = None
        self.anzahl_knoten = 0
    
    def hinzufügen(self, wert):
        if not self.wurzel:
            self.wurzel = Knoten(wert)
        else:
            self.wurzel.hinzufügen(wert)

    def löschen(self, wert):
        if not self.wurzel:
            raise ValueError("Wert nicht enthalten!")
        self.wurzel = self.wurzel.löschen(wert)
            

    def balancieren(self, SB, liste):
        liste.sort()
        print(liste)
        if len(liste) >= 2:
            liste1 = liste[:len(liste)//2]
            liste1.reverse()
            liste2 = liste[len(liste)//2:]
            SB.hinzufügen(liste2[0])
            liste2.pop(0)
            SB.hinzufügen(liste1[0])
            liste1.pop(0)
            self.balancieren(liste1)
            self.balancieren(liste2)
        elif len(liste) == 1:
            SB.hinzufügen(liste[0])
            liste.pop(0)

    def enthalten(self, wert):
        self.wurzel.enthalten(wert) if self.wurzel else False

    def größe(self):
        return self.anzahl_knoten if self.wurzel else 0

    def höhe(self):
        return self.wurzel.höhe() if self.wurzel else -1

    def größtes(self):
        return self.wurzel.größtes() if self.wurzel else None

    def kleinstes(self):
        return self.wurzel.kleinstes() if self.wurzel else None
    
    def spannweite(self):
        return self.größtes() - self.kleinstes() if self.wurzel else 0

    def abwickeln(self):
        return self.wurzel.abwickeln() if self.wurzel else []

    def graphviz(self):
        with open("graphviz.dot", "w", encoding="utf-8") as datei:
            datei.write("digraph Graph\n")
            datei.write("{\n")
            self.wurzel.zeigen(datei)
            datei.write("}")

class Knoten: 
    def __init__(self, wert):
        self.wert = wert
        self.links = None
        self.rechts = None

    def hinzufügen(self, wert):
        if wert <= self.wert:
            if not self.links:
                self.links = Knoten(wert)
                b.anzahl_knoten += 1
            else:
                self.links.hinzufügen(wert)
        else:
            if not self.rechts:
                self.rechts = Knoten(wert)
                b.anzahl_knoten += 1
            else:
                self.rechts.hinzufügen(wert)
        
    def vorgänger(self):
        aktueller_knoten = self.links

        while aktueller_knoten and aktueller_knoten.rechts:
            aktueller_knoten = aktueller_knoten.rechts
        return aktueller_knoten
    
    def löschen(self, wert):
        if wert < self.wert:
            self.links = self.links.löschen(wert)
        elif wert > self.wert:
            self.rechts = self.rechts.löschen(wert)
        else:
            if not self.links:
                return self.rechts
            if not self.rechts:
                return self.links
            
            vorgänger = self.vorgänger()
            self.wert = vorgänger.wert
            self.links = self.links.löschen(vorgänger.wert)
        return self

    def enthalten(self, wert):
        return wert == self.wert or (wert < self.wert and self.links and self.links.enthalten(wert)) or (wert > self.wert and self.rechts and self.rechts.enthalten(wert))

    def höhe(self):
        return max (self.links.höhe() + 1 if self.links else 0, self.rechts.höhe() + 1 if self.rechts else 0)

    def größtes(self):
        return self.rechts.größtes() if self.rechts else self.wert

    def kleinstes(self):
        return self.links.kleinstes() if self.links else self.wert

    def abwickeln(self):
        return (self.links.abwickeln() if self.links else []) + [self.wert] + (self.rechts.abwickeln() if self.rechts else [])

    def zeigen(self, datei):
        if self.links:
            datei.write(str(self.wert) + " -> " + str(self.links.wert) + ";\n")
            self.links.zeigen(datei)
        if self.rechts:
            datei.write(str(self.wert) + " -> " + str(self.rechts.wert) + ";\n")
            self.rechts.zeigen(datei)

b = Suchbaum()
# b.hinzufügen(50)
# b.hinzufügen(80)
# b.hinzufügen(20)
# b.hinzufügen(15)
# b.hinzufügen(35)
# b.hinzufügen(60)
# b.hinzufügen(100)
# b.hinzufügen(90)
# b.graphviz()

l = [i for i in range(1, 101)]
random.shuffle(l)
for zahl in l:
    b.hinzufügen(zahl)
b.graphviz()

# S = Suchbaum()
# liste = b.abwickeln()
# b.balancieren(S, liste)
# print(S.abwickeln())
# S.graphviz()