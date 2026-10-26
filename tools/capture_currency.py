"""
Capture photos of your own currency notes (for a sighted helper / during setup).

    .venv\\Scripts\\python tools\\capture_currency.py [--source 0|URL]

Keys in the window:
  1..6   select note: 1=10  2=20  3=50  4=100  5=200  6=500   0 = background (no note)
  SPACE  save one photo to the training dataset
  B      burst: save 30 photos (move/tilt the note slowly while it captures)
  F      save a REFERENCE photo (used immediately by ORB matching - no training needed)
         -> take 2-4 per note: front, back, a bit closer/farther
  Q/Esc  quit

Tips: capture BOTH sides, different backgrounds, lighting, distances, folded/old notes,
partially covered by fingers. ~150+ photos per class gives a good classifier.
"""
import argparse
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from vistara.camera import open_capture  # noqa: E402

KEYMAP = {ord("1"): "10", ord("2"): "20", ord("3"): "50", ord("4"): "100",
          ord("5"): "200", ord("6"): "500", ord("0"): "background"}


def count(d: Path):
    return len(list(d.glob("*.jpg"))) if d.exists() else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=str(config.CAMERA_SOURCE))
    a = ap.parse_args()
    src = int(a.source) if a.source.isdigit() else a.source
    cap = open_capture(src, config.FRAME_WIDTH, config.FRAME_HEIGHT)
    if not cap.isOpened():
        print("Cannot open camera", src)
        return
    current = "10"
    burst = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        ds_dir = config.CURRENCY_DATASET_DIR / current
        ref_dir = config.CURRENCY_REF_DIR / current
        if burst > 0:
            ds_dir.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(ds_dir / f"{int(time.time()*1000)}.jpg"), frame)
            burst -= 1
            time.sleep(0.08)
        view = frame.copy()
        cv2.putText(view, f"Class: {current}   dataset: {count(ds_dir)}   refs: {count(ref_dir)}"
                    + ("   BURST..." if burst else ""), (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(view, "1-6 note | 0 background | SPACE save | B burst | F reference | Q quit",
                    (10, view.shape[0] - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 220, 255), 2)
        cv2.imshow("Currency capture", view)
        k = cv2.waitKey(1) & 0xFF
        if k in (ord("q"), 27):
            break
        if k in KEYMAP:
            current = KEYMAP[k]
        elif k == ord(" "):
            ds_dir.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(ds_dir / f"{int(time.time()*1000)}.jpg"), frame)
        elif k == ord("b"):
            burst = 30
        elif k == ord("f") and current != "background":
            ref_dir.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(ref_dir / f"{int(time.time()*1000)}.jpg"), frame)
            print("saved reference for", current)
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
