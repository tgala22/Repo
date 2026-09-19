class Suchbaum:
    def __init__(self):
        self.wurzel = None
    def hinzufügen(self, wert):
        if not self.wurzel:
            self.wurzel = Knoten(wert)
        else: 
            self.wurzel.hinzufügen(wert)
    def graphviz(self):
        with open("baum.dot", "w") as f:
            f.write("digraph {")
            if self.wurzel:
                self.wurzel.graphviz(f)
            f.write("}")
        
    
    def löschen(self, wert):
        if not self.wurzel:
            raise ValueError("Wert nicht enthalten!")
        elif wert == self.wurzel.wert:
            if not self.wurzel.links and not self.rechts:
                self.wurzel = None
            elif not self.wurzel.links:
                self.wutzel = self.wurzel.rechts
            elif not self.wurzel.links.rechts:
                self.wurzel = self.wurzel.links
            else:
                self.wurzel = self.wurzel.links.gröstes_und_löschen()
        else:
            aktueller_knoten = self.wurzel
            while wert != aktueller_knoten.links.wert and wert != aktueller_knoten.rechts.wert:
                if wert < aktueller_knoten.wert:
                    aktueller_knoten = aktueller_knoten.links
                elif wert > aktueller_knoten.wert:
                    aktueller_knoten = aktueller_knoten.rechts

            if wert == aktueller_knoten.links.wert:
                if not aktueller_knoten.links.links and not aktueller_knoten.links.rechts:
                    aktueller_knoten.links = None
                elif not aktueller_knoten.links.links:
                    aktueller_knoten.links = aktueller_knoten.links.rechts
                elif not aktueller_knoten.links.rechts:
                    aktueller_knoten.links = aktueller_knoten.links.links
                else:
                    aktueller_knoten.links = aktueller_knoten.links.links.größtes_und_löschen()
                    

    

        #self.wurzel.löschen(wert)

    def enthalten(self, wert):
        return wert == self.wert or (wert < self.wert and self.links and self.links.enthalten(wert)) or (wert > self.wert and self.rechts and self.rechts.enthalten(wert))
    
    def größe(self):
        return self.wurzel.größe() if self.wurzel else 0
    
    def höhe(self):
        return self.wurzel.höhe() if self.wurzel else -1
    
    def gröstes(self):
        if not self.wurtzel:
            raise Exception ("Baum leer!")
        return self.wurzel.größtes()
    
    def kleinstes(self):
        if not self.wurzel:
            raise Exception ("Baum leer!")
        return self.wurzel.kleinstes() 
    def spannwiete(self):
        if not self.wurzel:
            raise Exception("Baum leer!")
        return self.gröstes() - self.kleinstes()

    def abwickeln(self):
        return self.wurzel.abwickeln() if self.wurzel else []
    
    def größtes_und_löschen(self):
        if not self.rechts:
            raise Exception("self.rechts existiert nicht!")
        if not self.rechts.rechts:
            gröstes = self.rechts.wert
            self.rechts = self.rechts.links
            return gröstes
        
        return self.rechts.größtes_und_löschen()

class Knoten:
    def __init__(self, wert):
        self.wert = wert
        self.links = None 
        self.rechts = None

    def hinzufügen(self, wert):
        if wert <= self.wert:
            if not self.links:
                self.links = Knoten(wert)
            else:
                self.links.hinzufügen(wert)
        else:
            if not self.rechts:
                self.rechts = Knoten(wert)
            else:
                self.rechts.hinzufügen(wert)
    def graphviz(self, f):
        if self.links:
            f.write(str(self.wert) + "->" + str(self.links.wert) + ";")
            self.links.graphviz(f)
        if self.rechts:
            f.write(str(self.wert) + "->" + str(self.rechts.wert) + ";")
            self.rechts.graphviz(f)

    def enthalten(self, wert):
        return wert == self.wert or (wert < self.wert and self.links and self.links.enthalten(wert)) or (wert > self.wert and self.rechts and self.rechts.enthalten(wert))
    
    def kleinstes(self):
        return self.links.kleinstes() if self.links else self.wert
    
    def größtes(self):
        return self.rechts.größtes() if self.rechts else self.wert

    def größe(self):
        return (self.links.größe() if self.links else 0) + 1 + (self.rechts.größe() if self.rechts else 0)
    
    def höhe(self):
        return max(self.links.höhe() + 1 if self.links else 0, self.rechts.höhe() +1 if self.rechts else 0)
    
    def abwickeln(self):
        return (self.links.abwickeln() if self.links else []) + [self.wert] + (self.rechts.abwickeln() if self. rechts else [])
    
    

        
b = Suchbaum()
b.hinzufügen(50)
b.hinzufügen(10)
b.hinzufügen(30)
b.hinzufügen(60)
b.hinzufügen(20)
b.hinzufügen(80)
b.hinzufügen(40)
b.hinzufügen(100)


b.graphviz()