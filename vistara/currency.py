"""
Indian currency note recognition.

Two back-ends (picked automatically):
  A) Trained classifier  -> models/currency_cls.pt   (best accuracy; see tools/train_currency.py)
  B) ORB feature matching against a few reference photos in data/currency_refs/<value>/*.jpg
     (works with only 2-4 photos per note side - good for a quick demo, no training).
"""
from collections import Counter
from pathlib import Path

import cv2
import numpy as np


class CurrencyRecognizer:
    def __init__(self, model_path: Path, ref_dir: Path, min_conf=0.65, orb_min_matches=14):
        self.min_conf = min_conf
        self.orb_min = orb_min_matches
        self.cls_model = None
        self.refs = []  # (value, keypoints, descriptors)
        self.history = []  # Session history of counted notes: [20, 50, 10]
        if Path(model_path).exists():
            from ultralytics import YOLO
            self.cls_model = YOLO(str(model_path))
            print(f"[currency] using trained classifier: {model_path}")
        self.orb = cv2.ORB_create(nfeatures=1500)
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
        self._load_refs(Path(ref_dir))
        if self.cls_model is None and not self.refs:
            print("[currency] WARNING: no model and no reference images. "
                  "Run tools/capture_currency.py first (see README).")

    @property
    def ready(self):
        return self.cls_model is not None or bool(self.refs)

    def add_note(self, val: int):
        self.history.append(int(val))

    def undo_last(self):
        """Undo the last added note. Returns (undone_val, remaining_total) or (None, 0)."""
        if not self.history:
            return None, 0
        undone = self.history.pop()
        return undone, sum(self.history)

    def reset_session(self):
        self.history.clear()

    # ---------------------------------------------------------- ORB refs
    def _load_refs(self, ref_dir: Path):
        if not ref_dir.exists():
            return
        for cls_dir in sorted(p for p in ref_dir.iterdir() if p.is_dir()):
            for img_path in list(cls_dir.glob("*.jpg")) + list(cls_dir.glob("*.png")):
                img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
                if img is None:
                    continue
                img = self._resize(img)
                kp, des = self.orb.detectAndCompute(img, None)
                if des is not None and len(kp) > 50:
                    self.refs.append((cls_dir.name, kp, des))
        if self.refs:
            print(f"[currency] loaded {len(self.refs)} reference images for ORB matching")

    @staticmethod
    def _resize(gray, width=800):
        h, w = gray.shape[:2]
        if w == width:
            return gray
        return cv2.resize(gray, (width, int(h * width / w)))

    def _predict_orb(self, frame):
        gray = self._resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        gray = cv2.equalizeHist(gray)
        kp, des = self.orb.detectAndCompute(gray, None)
        if des is None or len(kp) < 25:
            return None, 0.0
        scores = Counter()
        for value, rkp, rdes in self.refs:
            pairs = self.matcher.knnMatch(rdes, des, k=2)
            good = [m for m, *n in pairs if n and m.distance < 0.78 * n[0].distance]
            if len(good) < 7:
                continue
            src = np.float32([rkp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
            dst = np.float32([kp[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
            try:
                _, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
                inliers = int(mask.sum()) if mask is not None else 0
            except Exception:
                inliers = 0
            scores[value] = max(scores[value], inliers)
        if not scores:
            return None, 0.0
        value, best = scores.most_common(1)[0]
        if best < self.orb_min:
            return None, best / self.orb_min
        return value, min(1.0, best / (2 * self.orb_min))

    # ---------------------------------------------------------- classifier
    def _predict_cls(self, frame):
        r = self.cls_model.predict(frame, imgsz=224, verbose=False)[0]
        idx = int(r.probs.top1)
        conf = float(r.probs.top1conf)
        name = r.names[idx]
        if name == "background" or conf < self.min_conf:
            return None, conf
        return name, conf

    BANKNOTE_COLORS = {
        "10": ["Brown", "Beige", "Dark Red", "Black"],
        "20": ["Yellow", "Green", "Dark Green", "Orange"],
        "50": ["Cyan", "Sky Blue", "Blue"],
        "100": ["Purple", "Sky Blue", "Blue", "Gray"],
        "200": ["Orange", "Yellow", "Brown"],
        "500": ["Gray", "Dark Gray", "Light Gray", "White"],
    }

    def get_breakdown(self) -> dict:
        """Return detailed breakdown of counted banknotes in current session."""
        counts = Counter(self.history)
        return {
            "total": sum(self.history),
            "count": len(self.history),
            "denominations": {str(k): counts[k] for k in sorted(counts.keys(), key=lambda x: -x)},
        }

    # ---------------------------------------------------------- public
    def predict(self, frame, teachable=None, ocr=None, color_id=None):
        """
        Multi-modal ensemble banknote prediction:
        Combines Dual-Sided ORB + Custom Teachable Embeddings + OCR Digits + Base Color Profile.
        """
        h, w = frame.shape[:2]
        center_crop = frame[int(h * 0.15):int(h * 0.85), int(w * 0.15):int(w * 0.85)]
        if center_crop.size == 0:
            center_crop = frame

        # 1. Check teachable custom model
        if teachable is not None and teachable.classes:
            t_name, t_conf = teachable.predict(center_crop, threshold=0.76)
            if t_name is not None:
                import re
                digits = re.findall(r"\b(10|20|50|100|200|500)\b", t_name)
                if digits:
                    return digits[0], t_conf

        # 2. Check trained YOLO classifier if exists
        if self.cls_model is not None:
            c_val, c_conf = self._predict_cls(frame)
            if c_val is not None:
                return c_val, c_conf

        # 3. Check Dual-Sided ORB feature matching
        orb_val, orb_score = None, 0.0
        if self.refs:
            orb_val, orb_score = self._predict_orb(frame)

        # 4. Optional OCR Numeral check
        ocr_val = None
        if ocr is not None and ocr.ready:
            import re
            res = ocr.read_text(center_crop, focus_center=False)
            text = res.get("text", "")
            nums = re.findall(r"\b(10|20|50|100|200|500)\b", text)
            if nums:
                ocr_val = nums[0]

        # 5. Optional Dominant Color check
        color_name = None
        if color_id is not None:
            c_res = color_id.identify(center_crop)
            color_name = c_res.get("name_en")

        # Decision Fusion:
        # A) If ORB matches with solid confidence:
        if orb_val is not None and orb_score >= 0.70:
            # If confirmed by OCR or Color, boost confidence
            if orb_val == ocr_val:
                return orb_val, 0.98
            if color_name and color_name in self.BANKNOTE_COLORS.get(orb_val, []):
                return orb_val, min(0.96, orb_score + 0.15)
            return orb_val, orb_score

        # B) If OCR spotted a clear numeral (e.g. note folded or angled):
        if ocr_val is not None:
            # Cross-verify with color
            if color_name and color_name in self.BANKNOTE_COLORS.get(ocr_val, []):
                return ocr_val, 0.92
            if orb_val == ocr_val:
                return ocr_val, 0.95
            if orb_score > 0.4:
                return ocr_val, 0.85

        # C) Standard ORB threshold
        if orb_val is not None:
            return orb_val, orb_score

        return None, 0.0

    def predict_vote(self, frames, teachable=None, ocr=None, color_id=None):
        """Majority vote across frames -> (value or None, agreement 0..1)."""
        votes = Counter()
        for f in frames:
            v, _ = self.predict(f, teachable=teachable, ocr=ocr, color_id=color_id)
            if v is not None:
                votes[v] += 1
        if not votes:
            return None, 0.0
        value, n = votes.most_common(1)[0]
        agreement = n / len(frames)
        return (value, agreement) if agreement >= 0.40 else (None, agreement)
