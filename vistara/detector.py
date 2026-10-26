"""YOLOv8 object detector wrapper (runs on CPU)."""
import threading
from collections import Counter, defaultdict
from dataclasses import dataclass


@dataclass
class Detection:
    name: str
    conf: float
    box: tuple  # x1, y1, x2, y2 (pixels)

    def position(self, frame_w: int) -> str:
        cx = (self.box[0] + self.box[2]) / 2 / frame_w
        return "left" if cx < 0.38 else "right" if cx > 0.62 else "center"

    def proximity(self, frame_h: int) -> str:
        bh = (self.box[3] - self.box[1]) / max(1, frame_h)
        if bh > 0.58:
            return "close"
        elif bh > 0.25:
            return "medium"
        return "far"


class ObjectDetector:
    def __init__(self, model_name="yolov8n.pt", conf=0.45, imgsz=640, teachable=None):
        import torch
        from ultralytics import YOLO  # imported here so startup errors are clear
        self.torch = torch
        self.model = YOLO(model_name)  # auto-downloads ~6 MB the first time
        self.conf = conf
        self.imgsz = imgsz
        self.teachable = teachable
        self.lock = threading.Lock()   # model shared by main + auto-watch threads

    def detect(self, frame):
        with self.lock, self.torch.inference_mode():
            res = self.model.predict(frame, conf=self.conf, imgsz=self.imgsz, verbose=False)[0]
            out = []
            h, w = frame.shape[:2]

            for b in res.boxes:
                cls = int(b.cls[0])
                name = res.names[cls]
                conf = float(b.conf[0])
                box = tuple(int(v) for v in b.xyxy[0].tolist())

                # Check if this crop matches any custom taught item (e.g. headphone, specific bottle)
                if self.teachable and self.teachable.classes and name != "person":
                    x1, y1, x2, y2 = max(0, box[0]), max(0, box[1]), min(w, box[2]), min(h, box[3])
                    if (x2 - x1) > 40 and (y2 - y1) > 40:
                        crop = frame[y1:y2, x1:x2]
                        custom_name, custom_conf = self.teachable.predict(crop, threshold=0.77)
                        if custom_name is not None:
                            name = custom_name
                            conf = max(conf, custom_conf)

                out.append(Detection(name, conf, box))
            del res

            # Check central focus area for handheld items (e.g. note, keys, headphone)
            if self.teachable and self.teachable.classes:
                cx1, cy1 = int(w * 0.22), int(h * 0.2)
                cx2, cy2 = int(w * 0.78), int(h * 0.8)
                center_crop = frame[cy1:cy2, cx1:cx2]
                custom_name, custom_conf = self.teachable.predict(center_crop, threshold=0.77)
                if custom_name is not None and not any(d.name == custom_name for d in out):
                    out.append(Detection(custom_name, custom_conf, (cx1, cy1, cx2, cy2)))

            return out

    def stable_scan(self, frames, allowed=None, min_ratio=0.4):
        """
        Run detection on several frames and keep only objects seen consistently.
        Returns (counts, positions, proximities, last_detections)
          counts      : {'bottle': 1, ...}  (median count across frames)
          positions   : {'bottle': 'left', ...}
          proximities : {'bottle': 'medium', ...}
        """
        per_frame_counts = []
        pos_votes = defaultdict(Counter)
        prox_votes = defaultdict(Counter)
        last = []
        for f in frames:
            dets = self.detect(f)
            if allowed is not None:
                dets = [d for d in dets if d.name in allowed]
            last = dets
            c = Counter(d.name for d in dets)
            per_frame_counts.append(c)
            for d in dets:
                pos_votes[d.name][d.position(f.shape[1])] += 1
                prox_votes[d.name][d.proximity(f.shape[0])] += 1
        if not frames:
            return {}, {}, {}, []
        need = max(1, round(len(frames) * min_ratio))
        counts, positions, proximities = {}, {}, {}
        all_names = set().union(*per_frame_counts) if per_frame_counts else set()
        for name in all_names:
            seen = [c[name] for c in per_frame_counts if c[name] > 0]
            if len(seen) >= need:
                seen.sort()
                counts[name] = seen[len(seen) // 2]
                positions[name] = pos_votes[name].most_common(1)[0][0]
                proximities[name] = prox_votes[name].most_common(1)[0][0] if prox_votes[name] else "medium"
        return counts, positions, proximities, last


def draw(frame, detections, color=(0, 200, 255)):
    import cv2
    for d in detections:
        x1, y1, x2, y2 = d.box
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, f"{d.name} {d.conf:.2f}", (x1, max(18, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
    return frame
