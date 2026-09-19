import mss
import mss.tools
import time
import threading

running = True

def screenshot_loop():
    while running:
        with mss.MSS() as sct:
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            mss.tools.to_png(sct_img.rgb, sct_img.size, output="bild.png")
        time.sleep(2)

thread = threading.Thread(target=screenshot_loop, daemon=True)
thread.start()

while True:
    if input("Drücke 'q' + Enter, um das Programm zu beenden: ").strip().lower() == 'q':
        running = False
        break
