import numpy as np
import sounddevice as sd
import speech_recognition as sr
import scipy.io.wavfile as wav
import io
import time
import os
import ollama

# --- KONFIGURATION ---
SAMPLERATE = 16000
SCHWELLENWERT = 0.04       # Erhöhe auf 0.06, falls Jeff von alleine anspringt
STILLE_DAUER = 1.5         # Sekunden Stille, bis die Aufnahme stoppt
SIGNALWORT = "auto"

def jeff_spricht(text_antwort):
    """Nutzt die macOS Sprachausgabe und wartet, bis sie fertig ist."""
    bereinigter_text = text_antwort.replace('"', '').replace("'", "")
    os.system(f'say "{bereinigter_text}"')

def audio_zu_text(audio_daten):
    """Wandelt das Audio über Google in Text um."""
    byte_io = io.BytesIO()
    wav.write(byte_io, SAMPLERATE, audio_daten)
    byte_io.seek(0)
    
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(byte_io) as source:
            audio = recognizer.record(source)
        return recognizer.recognize_google(audio, language="de-DE")
    except:
        return ""

def frage_jeff_ki(reine_frage):
    """Schickt die Frage an Ollama und startet die Sprachausgabe."""
    print("\n[Jeff denkt nach...]")
    try:
        response = ollama.chat(model='phi3', messages=[
            {
                'role': 'system', 
                'content': 'Du bist Jeff, ein smarter KI-Assistent. Antworte auf Deutsch, extrem kurz und knackig (maximal 1-2 Sätze).'
            },
            {'role': 'user', 'content': reine_frage}
        ])
        
        antwort = response['message']['content']
        print(f"\n🤖 JEFF sagt: {antwort}\n")
        jeff_spricht(antwort)
        
    except Exception as e:
        print(f"Fehler bei der Kommunikation mit Ollama: {e}")

def haupt_schleife():
    print(f"\n=== 🟢 COCHLE-STEUERUNG BEREIT ===")
    print(f"Sprich einfach einen Satz, der mit '{SIGNALWORT}' beginnt.")
    print(f"Beispiel: '{SIGNALWORT}, wie geht es dir?'\n")
    
    while True:
        print("-> System hört zu...")
        gesamte_aufnahme = []
        stille_start = None
        aufnahme_aktiv = False
        
        # Das Mikrofon wird geöffnet
        with sd.InputStream(samplerate=SAMPLERATE, channels=1, dtype='float32') as stream:
            while True:
                # Liest fortlaufend winzige 0.1-Sekunden-Häppchen (keine Blockaden!)
                audio_block, _ = stream.read(int(SAMPLERATE * 0.1))
                lautstaerke = np.linalg.norm(audio_block) / np.sqrt(len(audio_block))
                
                if not aufnahme_aktiv:
                    if lautstaerke > SCHWELLENWERT:
                        print("[...Aufnahme läuft...]")
                        aufnahme_aktiv = True
                        gesamte_aufnahme.append(audio_block)
                else:
                    gesamte_aufnahme.append(audio_block)
                    
                    if lautstaerke < SCHWELLENWERT:
                        if stille_start is None:
                            stille_start = time.time()
                        elif time.time() - stille_start > STILLE_DAUER:
                            print("[Aufnahme beendet. Mikrofon geschlossen.]")
                            break
                    else:
                        stille_start = None
                        
        # Mikrofon ist hier automatisch geschlossen, während Google und die KI arbeiten
        if len(gesamte_aufnahme) > 0:
            audio_np = np.concatenate(gesamte_aufnahme, axis=0)
            audio_int16 = (audio_np * 32767).astype(np.int16)
            
            print("[Verarbeite Audiodaten mit Google...]")
            text = audio_zu_text(audio_int16)
            
            if text:
                print(f"Gehört: '{text}'")
                
                # Prüfen, ob "Jeff" im Satz vorkommt
                if SIGNALWORT in text.lower():
                    # Schneidet das Wort "Jeff" vorne oder hinten weg, damit nur die Frage bleibt
                    reine_frage = text.lower().replace(SIGNALWORT, "").strip()
                    
                    if "stopp" in reine_frage or "beenden" in reine_frage:
                        print("Programm wird beendet. Auf Wiedersehen!")
                        jeff_spricht("Auf Wiedersehen!")
                        break
                    
                    if reine_frage:
                        # KI antwortet. Mikrofon bleibt währenddessen absolut zu.
                        frage_jeff_ki(reine_frage)
                    else:
                        print("[Du hast nur 'Jeff' gesagt, aber keine Frage gestellt.]")
                        jeff_spricht("Ja, ich höre dich. Wie kann ich helfen?")
                else:
                    print(f"[Name '{SIGNALWORT}' nicht im Satz enthalten. Ignoriert.]")
            else:
                print("[Kein Text erkannt / Hintergrundgeräusch]")
        
        # Kurze Pause vor der nächsten Runde
        time.sleep(1)

if __name__ == "__main__":
    try:
        haupt_schleife()
    except KeyboardInterrupt:
        print("\nProgramm beendet.")




 
