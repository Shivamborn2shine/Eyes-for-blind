"""
Vistara Vision - central configuration.
Edit the values here instead of touching the code.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"

# ---------------------------------------------------------------- Camera
# "auto" = uses iPhone direct browser cast when active, otherwise laptop webcam 0
# 0 = built-in laptop webcam, 1 = USB webcam.
# "iphone" = iPhone direct browser cast (open http://<laptop-ip>:5000/cam in Safari)
# iPhone via SCREEN MIRRORING (AirPlay receiver app on laptop, e.g. LonelyScreen):
#   "screen:LonelyScreen" / "screen:5KPlayer" / "screen:AirServer"
#   Run  python main.py --list-windows  to see visible window titles.
CAMERA_SOURCE = "auto"
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
SHOW_PREVIEW = True          # preview window for the sighted helper / demo

# ---------------------------------------------------------------- Web Interface
ENABLE_WEB_SERVER = True
WEB_HOST = "0.0.0.0"         # 0.0.0.0 allows phone/tablet on same Wi-Fi to view
WEB_PORT = 5000

# ---------------------------------------------------------------- Language
# "en" or "hi". Can be toggled at runtime with the language hotkey.
DEFAULT_LANGUAGE = "en"
SPEECH_RATE = 165            # words per minute for the offline voice

# ---------------------------------------------------------------- Object detection
YOLO_MODEL = "yolov8n.pt"    # nano model -> fast enough on a laptop CPU
DETECTION_CONFIDENCE = 0.45
DETECTION_IMG_SIZE = 640

# Objects that are treated as "personal belongings" for left-behind alerts.
# (Names are COCO classes understood by YOLOv8.)
TRACKED_ITEMS = [
    "cell phone", "bottle", "backpack", "handbag", "umbrella", "book",
    "laptop", "cup", "remote", "keyboard", "mouse", "scissors",
    "suitcase", "clock", "toothbrush", "wine glass", "teddy bear",
]

# ---------------------------------------------------------------- Left-behind logic
SNAPSHOT_FRAMES = 8          # frames analysed when remembering / checking a place
MIN_HITS_RATIO = 0.4         # object must appear in >= 40% of frames to count
AUTO_WATCH = True            # auto-warn when user walks away and items remain
AUTO_WATCH_ABSENT_SECONDS = 6  # no person visible for this long -> "user left"
AUTO_WATCH_INTERVAL = 0.7    # seconds between background detections

# ---------------------------------------------------------------- Currency
CURRENCY_MODEL = MODELS_DIR / "currency_cls.pt"   # created by tools/train_currency.py
CURRENCY_REF_DIR = DATA_DIR / "currency_refs"     # fallback reference images
CURRENCY_DATASET_DIR = DATA_DIR / "currency_dataset"
CURRENCY_CLASSES = ["10", "20", "50", "100", "200", "500", "background"]
CURRENCY_MIN_CONFIDENCE = 0.65
CURRENCY_VOTE_FRAMES = 3     # majority vote over frames for stability & speed
ORB_MIN_GOOD_MATCHES = 14    # robust threshold for handheld webcam notes

# ---------------------------------------------------------------- Memory
MEMORY_FILE = DATA_DIR / "memory.json"
TEACHABLE_FILE = DATA_DIR / "teachable_objects.json"
TTS_CACHE_DIR = DATA_DIR / "tts_cache"

# ---------------------------------------------------------------- Hotkeys
# Global hotkeys (work even when the preview window is not focused).
# Number-pad keys are included so a cheap USB numpad can act as a big-button remote.
HOTKEYS = {
    "currency": ["c", "num 1"],
    "remember": ["r", "num 2"],
    "leaving":  ["l", "num 3"],
    "describe": ["d", "num 4"],
    "where":    ["w", "num 5"],
    "language": ["h", "num 6"],
    "teach":    ["t", "num 7"],
    "read_text": ["o", "num 8"],
    "color":    ["k", "num 9"],
    "undo_note": ["u"],
    "continuous_currency": ["x"],
    "help":     ["f1", "num 0"],
    "quit":     ["esc"],
}
