"""Threaded camera reader: laptop webcam, USB webcam, phone URL (DroidCam),
mirrored iPhone screen ("screen:<window title>"), or direct browser iPhone cast ("iphone")."""
import threading
import time

import cv2
import numpy as np

# Global buffer for frames uploaded directly from iPhone browser (/cam)
REMOTE_FRAME = None
REMOTE_FRAME_LOCK = threading.Lock()
REMOTE_FRAME_TIME = 0


def update_remote_frame(img: np.ndarray):
    """Called by Flask whenever the iPhone streams a frame."""
    global REMOTE_FRAME, REMOTE_FRAME_TIME
    with REMOTE_FRAME_LOCK:
        REMOTE_FRAME = img
        REMOTE_FRAME_TIME = time.time()


def get_remote_frame(timeout=3.0):
    """Return latest remote iPhone frame if fresh."""
    with REMOTE_FRAME_LOCK:
        if REMOTE_FRAME is not None and (time.time() - REMOTE_FRAME_TIME) < timeout:
            return True, REMOTE_FRAME.copy()
    return False, None


class RemoteStreamSource:
    """Reads frames uploaded over local Wi-Fi from an iPhone browser."""

    def __init__(self, timeout=3.0):
        self.timeout = timeout

    def isOpened(self):
        return True

    def set(self, *_):
        return True

    def read(self):
        ok, frame = get_remote_frame(self.timeout)
        if not ok:
            time.sleep(0.04)
            return False, None
        return True, frame

    def release(self):
        pass


def open_capture(source, width=1280, height=720):
    """Return a cv2.VideoCapture-like object for any supported source."""
    if isinstance(source, str):
        s_lower = source.lower().strip()
        if s_lower.startswith("screen"):
            from vistara.screen_source import ScreenSource
            return ScreenSource(source)
        if s_lower in ("iphone", "remote", "cam", "web"):
            return RemoteStreamSource()
        if s_lower == "auto":
            source = 0

    if isinstance(source, int):
        cap = cv2.VideoCapture(source, cv2.CAP_DSHOW)  # DirectShow = fast open on Windows
        if not cap.isOpened():
            cap = cv2.VideoCapture(source)
    else:
        cap = cv2.VideoCapture(source)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


class Camera:
    def __init__(self, source=0, width=1280, height=720):
        self.source = source
        self.width, self.height = width, height
        self.frame = None
        self.lock = threading.Lock()
        self.running = False
        self.cap = None

    def _open(self):
        return open_capture(self.source, self.width, self.height)

    def start(self) -> bool:
        self.cap = self._open()
        if not self.cap.isOpened():
            print("[camera] Hardware webcam not found, waiting for iPhone camera stream...")
            self.cap = RemoteStreamSource()
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()
        return True

    def _loop(self):
        fails = 0
        while self.running:
            # Check for live direct iPhone browser stream (priority in auto mode)
            if self.source == "auto":
                ok_remote, remote_frame = get_remote_frame(timeout=2.5)
                if ok_remote:
                    with self.lock:
                        self.frame = remote_frame
                    time.sleep(0.02)
                    continue

            ok, frame = self.cap.read()
            if ok and frame is not None:
                fails = 0
                with self.lock:
                    self.frame = frame
            else:
                fails += 1
                time.sleep(0.04)
                # Auto-reconnect network or dropped streams
                if fails > 40 and not isinstance(self.cap, RemoteStreamSource):
                    print("[camera] reconnecting...")
                    self.cap.release()
                    time.sleep(1)
                    self.cap = self._open()
                    fails = 0

    def read(self):
        with self.lock:
            return None if self.frame is None else self.frame.copy()

    def frames(self, n, delay=0.08):
        out = []
        for _ in range(n):
            f = self.read()
            if f is not None:
                out.append(f)
            time.sleep(delay)
        return out

    def stop(self):
        self.running = False
        time.sleep(0.1)
        if self.cap is not None:
            self.cap.release()
