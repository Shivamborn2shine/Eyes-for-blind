"""Global hotkeys (keyboard / USB numpad) -> action names."""
import queue

# Numpad keys report these names when NumLock is OFF.
NUMPAD_ALT = {"0": "insert", "1": "end", "2": "down", "3": "page down",
              "4": "left", "5": "clear", "6": "right", "7": "home",
              "8": "up", "9": "page up"}


class Hotkeys:
    def __init__(self, mapping: dict):
        self.actions: "queue.Queue[str]" = queue.Queue()
        self.normal = {}   # 'c' -> 'currency'
        self.keypad = {}   # 'end'/'1' (keypad) -> 'remember'
        for action, keys in mapping.items():
            for k in keys:
                k = k.lower()
                if k.startswith("num "):
                    d = k[4:]
                    self.keypad[d] = action
                    self.keypad[NUMPAD_ALT.get(d, d)] = action
                else:
                    self.normal[k] = action
        self.global_ok = False
        try:
            import keyboard
            keyboard.on_press(self._on_press)
            self.global_ok = True
        except Exception as e:
            print("[hotkeys] global hotkeys unavailable, use the preview window:", e)

    def _on_press(self, ev):
        name = (ev.name or "").lower()
        if getattr(ev, "is_keypad", False) and name in self.keypad:
            self.actions.put(self.keypad[name])
        elif name in self.normal:
            self.actions.put(self.normal[name])

    def feed_cv_key(self, key: int):
        """Fallback when the OpenCV window has focus and global hooks are unavailable."""
        if self.global_ok or key < 0:
            return
        if key == 27:
            self.actions.put("quit")
            return
        ch = chr(key & 0xFF).lower()
        if ch in self.normal:
            self.actions.put(self.normal[ch])
