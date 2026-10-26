"""
Assistive color identification for visually impaired users.
Analyzes the central target region of camera frames and provides
human-friendly color names in English and Hindi with hex codes and confidence.
"""
from typing import Dict, Tuple, Optional
import cv2
import numpy as np


# Pre-defined natural color reference ranges in HSV
# OpenCV HSV: H in [0, 180], S in [0, 255], V in [0, 255]
COLOR_RANGES = [
    # (name_en, name_hi, hex_code, h_min, h_max, s_min, s_max, v_min, v_max)
    ("Black", "काला", "#171717", 0, 180, 0, 255, 0, 42),
    ("White", "सफ़ेद", "#f8fafc", 0, 180, 0, 35, 195, 255),
    ("Gray", "स्लेटी / ग्रे", "#6b7280", 0, 180, 0, 45, 42, 195),
    ("Dark Red", "गहरा लाल", "#881337", 0, 10, 80, 255, 42, 120),
    ("Red", "लाल", "#dc2626", 0, 9, 75, 255, 120, 255),
    ("Red", "लाल", "#dc2626", 172, 180, 75, 255, 120, 255),
    ("Brown", "भूरा", "#78350f", 9, 22, 70, 255, 42, 120),
    ("Orange", "नारंगी", "#f97316", 10, 22, 80, 255, 120, 255),
    ("Yellow", "पीला", "#facc15", 23, 35, 75, 255, 110, 255),
    ("Dark Green", "गहरा हरा", "#14532d", 36, 85, 70, 255, 42, 110),
    ("Green", "हरा", "#16a34a", 36, 85, 70, 255, 110, 255),
    ("Cyan", "फ़िरोज़ी", "#06b6d4", 86, 100, 70, 255, 80, 255),
    ("Sky Blue", "आसमानी नीला", "#38bdf8", 101, 115, 60, 255, 150, 255),
    ("Navy Blue", "गहरा नीला", "#1e3a8a", 101, 130, 80, 255, 42, 115),
    ("Blue", "नीला", "#2563eb", 101, 130, 80, 255, 115, 255),
    ("Purple", "बैंगनी", "#7c3aed", 131, 155, 60, 255, 50, 255),
    ("Pink", "गुलाबी", "#ec4899", 156, 171, 60, 255, 110, 255),
    ("Beige", "बादामी / क्रीम", "#fef3c7", 15, 35, 25, 75, 170, 240),
]


class ColorIdentifier:
    """Fast, robust assistive color classifier."""

    @staticmethod
    def identify(bgr_img: np.ndarray, box: Optional[Tuple[int, int, int, int]] = None) -> Dict:
        """
        Identify the dominant color in the target region.
        bgr_img: camera frame or cropped region.
        box: optional (x1, y1, x2, y2) bounding box.
        """
        if bgr_img is None or bgr_img.size == 0:
            return {
                "name_en": "Unknown",
                "name_hi": "अज्ञात",
                "hex": "#888888",
                "rgb": (136, 136, 136),
                "conf": 0.0,
            }

        h, w = bgr_img.shape[:2]
        if box is not None:
            x1, y1, x2, y2 = box
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            roi = bgr_img[y1:y2, x1:x2]
        else:
            # Use center 35% focus area to avoid room/table edges
            cy1, cy2 = int(h * 0.32), int(h * 0.68)
            cx1, cx2 = int(w * 0.32), int(w * 0.68)
            roi = bgr_img[cy1:cy2, cx1:cx2]

        if roi.size == 0:
            roi = bgr_img

        # Apply slight Gaussian blur to reduce camera sensor noise/glare
        blurred = cv2.GaussianBlur(roi, (7, 7), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

        # Compute median HSV to be immune to outlier pixels / specular reflections
        h_med = float(np.median(hsv[:, :, 0]))
        s_med = float(np.median(hsv[:, :, 1]))
        v_med = float(np.median(hsv[:, :, 2]))

        # Also get representative BGR color
        b_med = int(np.median(roi[:, :, 0]))
        g_med = int(np.median(roi[:, :, 1]))
        r_med = int(np.median(roi[:, :, 2]))
        actual_hex = f"#{r_med:02x}{g_med:02x}{b_med:02x}"

        # 1. Check Achromatic conditions (Black / White / Gray)
        if v_med < 42:
            return {
                "name_en": "Black",
                "name_hi": "काला",
                "hex": "#111111",
                "rgb": (r_med, g_med, b_med),
                "conf": round(min(1.0, (45 - v_med) / 40 + 0.4), 2),
            }

        if s_med < 35:
            if v_med > 190:
                return {
                    "name_en": "White",
                    "name_hi": "सफ़ेद",
                    "hex": "#f8fafc",
                    "rgb": (r_med, g_med, b_med),
                    "conf": round(min(1.0, (v_med - 180) / 70 + 0.3), 2),
                }
            if v_med > 130:
                return {
                    "name_en": "Light Gray",
                    "name_hi": "हल्का स्लेटी",
                    "hex": "#9ca3af",
                    "rgb": (r_med, g_med, b_med),
                    "conf": 0.85,
                }
            return {
                "name_en": "Dark Gray",
                "name_hi": "गहरा स्लेटी",
                "hex": "#4b5563",
                "rgb": (r_med, g_med, b_med),
                "conf": 0.85,
            }

        # 2. Check Chromatic ranges
        # Beige / Cream check (low saturation yellow-orange with high value)
        if 15 <= h_med <= 35 and 35 <= s_med <= 80 and v_med >= 170:
            return {
                "name_en": "Beige / Cream",
                "name_hi": "क्रीम / बादामी",
                "hex": "#fef3c7",
                "rgb": (r_med, g_med, b_med),
                "conf": 0.88,
            }

        # Brown check (dark orange/red with moderate-to-high saturation)
        if 8 <= h_med <= 24 and v_med <= 115 and s_med >= 60:
            return {
                "name_en": "Brown",
                "name_hi": "भूरा",
                "hex": "#78350f",
                "rgb": (r_med, g_med, b_med),
                "conf": 0.90,
            }

        # Match across predefined ranges
        best_match = None
        best_dist = float("inf")

        for name_en, name_hi, hex_code, h1, h2, s1, s2, v1, v2 in COLOR_RANGES:
            # Hue distance considering circular wrap-around at 180
            h_center = (h1 + h2) / 2
            h_diff = abs(h_med - h_center)
            if h_diff > 90:
                h_diff = 180 - h_diff

            if (h1 <= h_med <= h2) or (h1 > h2 and (h_med >= h1 or h_med <= h2)):
                s_diff = abs(s_med - (s1 + s2) / 2) / 255.0
                v_diff = abs(v_med - (v1 + v2) / 2) / 255.0
                dist = h_diff / 180.0 + s_diff * 0.5 + v_diff * 0.5
                if dist < best_dist:
                    best_dist = dist
                    best_match = (name_en, name_hi, hex_code)

        if best_match is not None:
            name_en, name_hi, hex_code = best_match
            conf = max(0.65, min(0.98, 1.0 - best_dist))
            return {
                "name_en": name_en,
                "name_hi": name_hi,
                "hex": hex_code,
                "actual_hex": actual_hex,
                "rgb": (r_med, g_med, b_med),
                "conf": round(conf, 2),
            }

        return {
            "name_en": "Uncertain",
            "name_hi": "अस्पष्ट",
            "hex": actual_hex,
            "rgb": (r_med, g_med, b_med),
            "conf": 0.50,
        }
