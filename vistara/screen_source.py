"""
Screen / window capture source - lets a MIRRORED iPhone (AirPlay) act as the camera.

Set up:
  1. Install a free AirPlay receiver on the laptop, e.g. LonelyScreen, 5KPlayer,
     AirServer (trial) or ApowerMirror. iPhone and laptop must be on the same Wi-Fi.
  2. iPhone: Control Centre -> Screen Mirroring -> pick the laptop.
  3. Open the iPhone Camera app (landscape works best).
  4. Run:  python main.py --source "screen:LonelyScreen"     (part of the window title)
           python main.py --list-windows                     (to see window titles)
           python main.py --source screen:monitor1           (whole monitor 1)
           python main.py --source screen:100,100,800,600    (fixed region x,y,w,h)

The window must stay visible (not minimised / covered), it may be in a corner.
Black letter-box bars around the mirrored image are cropped automatically.

Exposes the same small API as cv2.VideoCapture: isOpened(), read(), set(), release().
"""
import ctypes
import threading
import time
from ctypes import wintypes

import numpy as np

user32 = ctypes.windll.user32

# Use real pixel coordinates on high-DPI (125%/150% scaled) laptop screens.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass

EXCLUDE_TITLES = ("vistara vision", "currency capture")  # never capture our own windows


def list_windows():
    """Return [(hwnd, title)] for all visible top-level windows with a title."""
    out = []
    proc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def cb(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            n = user32.GetWindowTextLengthW(hwnd)
            if n:
                buf = ctypes.create_unicode_buffer(n + 1)
                user32.GetWindowTextW(hwnd, buf, n + 1)
                out.append((hwnd, buf.value))
        return True

    user32.EnumWindows(proc(cb), 0)
    return out


def find_window(part: str):
    part = part.lower()
    for hwnd, title in list_windows():
        t = title.lower()
        if part in t and not any(x in t for x in EXCLUDE_TITLES):
            return hwnd, title
    return None, None


def window_client_rect(hwnd):
    """Screen coordinates of the window's client area (without title bar/borders)."""
    rect = wintypes.RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return None
    pt = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    w, h = rect.right - rect.left, rect.bottom - rect.top
    if w < 50 or h < 50:
        return None
    return {"left": pt.x, "top": pt.y, "width": w, "height": h}


class ScreenSource:
    def __init__(self, spec: str):
        self._local = threading.local()   # one mss grabber per thread (Windows requirement)
        self.spec = spec[len("screen:"):].strip() if spec.lower().startswith("screen:") else spec
        self.hwnd = None
        self.title = None
        self.region = None
        self.crop = None          # (y1, y2, x1, x2) inside the grabbed image
        self.last_crop_time = 0
        self.last_locate = 0
        self.opened = self._locate()
        if self.opened:
            print(f"[screen] capturing: {self.title or self.spec} {self.region}")
        else:
            print(f"[screen] window '{self.spec}' not found. Visible windows:")
            for _, t in list_windows():
                print("    -", t)

    @property
    def sct(self):
        s = getattr(self._local, "sct", None)
        if s is None:
            import mss
            factory = getattr(mss, "MSS", None) or mss.mss
            s = self._local.sct = factory()
        return s

    # ---------------------------------------------------------- locate region
    def _locate(self):
        s = self.spec
        if s.lower().startswith("monitor"):
            idx = int(s[7:] or 1)
            mons = self.sct.monitors
            self.region = dict(mons[min(idx, len(mons) - 1)])
            return True
        if s.count(",") == 3:
            x, y, w, h = (int(v) for v in s.split(","))
            self.region = {"left": x, "top": y, "width": w, "height": h}
            return True
        hwnd, title = find_window(s)
        if not hwnd:
            return False
        if user32.IsIconic(hwnd):
            print("[screen] the mirror window is minimised - please restore it")
        self.hwnd, self.title = hwnd, title
        self.region = window_client_rect(hwnd)
        return self.region is not None

    # ---------------------------------------------------------- crop black bars
    def _update_crop(self, img):
        gray = img.max(axis=2)
        rows = np.where(gray.max(axis=1) > 25)[0]
        cols = np.where(gray.max(axis=0) > 25)[0]
        if len(rows) < 50 or len(cols) < 50:
            self.crop = None
            return
        self.crop = (rows[0], rows[-1] + 1, cols[0], cols[-1] + 1)

    # ---------------------------------------------------------- cv2-like API
    def isOpened(self):
        return self.opened

    def set(self, *_):
        return True

    def read(self):
        now = time.time()
        if self.hwnd and now - self.last_locate > 1.0:   # follow the window if moved/resized
            self.last_locate = now
            if not user32.IsWindow(self.hwnd):
                self.opened = self._locate()
            else:
                r = window_client_rect(self.hwnd)
                if r:
                    self.region = r
        if not self.region:
            return False, None
        try:
            shot = self.sct.grab({k: self.region[k] for k in ("left", "top", "width", "height")})
            img = np.frombuffer(shot.bgra, np.uint8).reshape(shot.height, shot.width, 4)[:, :, :3]
        except Exception as e:
            if not getattr(self, "_warned", False):
                self._warned = True
                print("[screen] capture failed:", e,
                      "\n         (run from a normal desktop session, window must be visible)")
            time.sleep(0.2)
            return False, None
        if now - self.last_crop_time > 2.0:
            self.last_crop_time = now
            self._update_crop(img)
        if self.crop:
            y1, y2, x1, x2 = self.crop
            img = img[y1:y2, x1:x2]
        time.sleep(0.03)  # ~25-30 fps is plenty, keeps CPU free for detection
        return True, np.ascontiguousarray(img)

    def release(self):
        try:
            self.sct.close()
        except Exception:
            pass
