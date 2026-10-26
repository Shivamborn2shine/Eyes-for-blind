"""
Teachable Vision Model for Vistara Vision.

Allows the user to teach ANY custom object in seconds (e.g., "20 rupee note",
"headphone", "keys", "wallet", "medicine bottle") by capturing a few visual
embeddings using MobileNetV3 feature extractor + Cosine Similarity.
Zero training wait, runs in real-time on CPU.
"""
import json
import threading
from pathlib import Path

import cv2
import numpy as np
import torch
import torchvision.models as models
import torchvision.transforms as transforms


class TeachableClassifier:
    def __init__(self, data_path: Path):
        self.data_path = Path(data_path)
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()

        # Load MobileNetV3-Small feature extractor
        weights = models.MobileNet_V3_Small_Weights.DEFAULT
        mobilenet = models.mobilenet_v3_small(weights=weights).eval()
        # Extract features right before the classification head (576-dim vector)
        self.feature_extractor = mobilenet.features
        self.pool = mobilenet.avgpool

        # Preprocessing transform matching ImageNet standards
        self.transform = transforms.Compose(
            [
                transforms.ToPILImage(),
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
                ),
            ]
        )

        # Dictionary of classes: { "headphone": [ [vector_1], [vector_2], ... ] }
        self.classes = {}
        self._load()

    def _load(self):
        if self.data_path.exists():
            try:
                data = json.loads(self.data_path.read_text(encoding="utf-8"))
                self.classes = {
                    k: [np.array(v, dtype=np.float32) for v in vecs]
                    for k, vecs in data.items()
                }
                print(f"[teachable] Loaded {len(self.classes)} custom taught classes: {list(self.classes.keys())}")
            except Exception as e:
                print("[teachable] Error loading custom memory:", e)
                self.classes = {}

    def save(self):
        with self.lock:
            serializable = {
                k: [v.tolist() for v in vecs] for k, vecs in self.classes.items()
            }
            self.data_path.write_text(
                json.dumps(serializable, indent=2), encoding="utf-8"
            )

    @torch.inference_mode()
    def get_embedding(self, bgr_img: np.ndarray) -> np.ndarray:
        """Extract a 576-dimensional L2-normalized feature vector from an image crop."""
        rgb_img = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
        tensor = self.transform(rgb_img).unsqueeze(0)  # Shape: (1, 3, 224, 224)
        feat = self.feature_extractor(tensor)
        feat = self.pool(feat)
        feat = torch.flatten(feat, 1).squeeze(0).numpy()
        norm = np.linalg.norm(feat)
        if norm > 1e-6:
            feat = feat / norm
        return feat

    def learn(self, label: str, bgr_frames: list) -> int:
        """
        Teach a new object using a list of camera frames/crops.
        Stores normalized feature embeddings for both center ROI and full frame.
        """
        label = label.strip().lower()
        if not label or not bgr_frames:
            return 0

        embeddings = []
        for frame in bgr_frames:
            if frame is None or frame.size == 0:
                continue
            h, w = frame.shape[:2]
            # Center crop (central 60%) to focus tightly on the held object rather than background walls
            cy1, cy2 = int(h * 0.2), int(h * 0.8)
            cx1, cx2 = int(w * 0.2), int(w * 0.8)
            center_crop = frame[cy1:cy2, cx1:cx2]
            embeddings.append(self.get_embedding(center_crop))
            embeddings.append(self.get_embedding(frame))

        if not embeddings:
            return 0

        with self.lock:
            if label not in self.classes:
                self.classes[label] = []
            self.classes[label].extend(embeddings)
            # Keep max 40 exemplars per class to keep memory ultra-light
            if len(self.classes[label]) > 40:
                self.classes[label] = self.classes[label][-40:]

        self.save()
        print(f"[teachable] Successfully taught '{label}' with {len(embeddings)} new samples.")
        return len(embeddings)

    def predict(self, bgr_img: np.ndarray, threshold: float = 0.76):
        """
        Compare bgr_img against all taught classes using Cosine Similarity.
        Supports negative background suppression.
        Returns: (best_label, confidence) or (None, confidence)
        """
        if not self.classes or bgr_img is None or bgr_img.size == 0:
            return None, 0.0

        query_emb = self.get_embedding(bgr_img)
        best_label = None
        best_score = -1.0

        with self.lock:
            # 1. First measure background / negative similarity if taught
            bg_score = -1.0
            for bg_key in ["background", "empty", "nothing"]:
                if bg_key in self.classes and self.classes[bg_key]:
                    bg_sims = [float(np.dot(query_emb, ex)) for ex in self.classes[bg_key]]
                    bg_sims.sort(reverse=True)
                    top_bg = bg_sims[: min(3, len(bg_sims))]
                    bg_score = max(bg_score, sum(top_bg) / len(top_bg))

            # 2. Measure against positive taught classes
            for label, exemplars in self.classes.items():
                if not exemplars or label in ["background", "empty", "nothing"]:
                    continue
                sims = [float(np.dot(query_emb, ex)) for ex in exemplars]
                sims.sort(reverse=True)
                top_k = sims[: min(3, len(sims))]
                score = sum(top_k) / len(top_k)

                if score > best_score:
                    best_score = score
                    best_label = label

        # If background matches closer or within 0.04 margin of the object, suppress!
        if bg_score > 0 and (bg_score >= best_score - 0.04):
            return None, best_score

        if best_score >= threshold:
            return best_label, best_score
        return None, best_score

    def list_classes(self):
        with self.lock:
            return {k: len(v) for k, v in self.classes.items()}

    def delete_class(self, label: str):
        label = label.strip().lower()
        with self.lock:
            if label in self.classes:
                del self.classes[label]
                self.save()
                return True
        return False

    def clear_all(self):
        with self.lock:
            self.classes.clear()
            self.save()
            return True
