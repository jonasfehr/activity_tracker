import time
from pynput import mouse, keyboard

last_input = time.time()

def _update(*args):
    global last_input
    last_input = time.time()

mouse.Listener(on_move=_update, on_click=_update).start()
keyboard.Listener(on_press=_update).start()

def is_active(threshold=60):
    return (time.time() - last_input) < threshold
