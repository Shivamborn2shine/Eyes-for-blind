"""
Offline high-speed Optical Character Recognition (OCR) using native Windows Media OCR.
Designed for visually impaired users to read text on packaging, mail, medicine bottles,
and documents in ~40ms on CPU with zero external heavy binary dependencies.
"""
import asyncio
from typing import Dict, List, Optional
import cv2
import numpy as np

import winrt.windows.media.ocr as ocr
import winrt.windows.globalization as glob
import winrt.windows.graphics.imaging as imaging
import winrt.windows.storage.streams as streams


class TextReader:
    """Native Windows OCR text reader for assistive document and label inspection."""

    def __init__(self):
        self.engine = None
        self._init_engine()

    def _init_engine(self):
        try:
            self.engine = ocr.OcrEngine.try_create_from_user_profile_languages()
            if not self.engine:
                lang = glob.Language("en-US")
                self.engine = ocr.OcrEngine.try_create_from_language(lang)
            if self.engine:
                print(f"[ocr] Windows Media OCR active: {self.engine.recognizer_language.display_name}")
            else:
                print("[ocr] Warning: Unable to initialize Windows OCR engine.")
        except Exception as e:
            print("[ocr] Error initializing OCR engine:", e)

    @property
    def ready(self) -> bool:
        return self.engine is not None

    def read_text(self, bgr_img: np.ndarray, focus_center: bool = True) -> Dict:
        """
        Extract text from an image.
        Returns a dict with:
          - 'text': complete string
          - 'lines': list of line strings
          - 'speech_text': natural concise version for TTS
          - 'word_count': number of words found
        """
        if not self.ready or bgr_img is None or bgr_img.size == 0:
            return {"text": "", "lines": [], "speech_text": "", "word_count": 0}

        h, w = bgr_img.shape[:2]
        if focus_center:
            # Focus on the center 75% where user holds the text/document
            cy1, cy2 = int(h * 0.12), int(h * 0.88)
            cx1, cx2 = int(w * 0.12), int(w * 0.88)
            target = bgr_img[cy1:cy2, cx1:cx2]
        else:
            target = bgr_img

        # Contrast enhancement for clear text edges
        try:
            gray = cv2.cvtColor(target, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
        except Exception:
            enhanced_bgr = target

        # Encode to PNG buffer for Windows.Graphics.Imaging.BitmapDecoder
        ok, buf = cv2.imencode(".png", enhanced_bgr)
        if not ok:
            return {"text": "", "lines": [], "speech_text": "", "word_count": 0}

        try:
            return asyncio.run(self._async_recognize(buf.tobytes()))
        except Exception as e:
            print("[ocr] Recognition error:", e)
            return {"text": "", "lines": [], "speech_text": "", "word_count": 0}

    async def _async_recognize(self, png_bytes: bytes) -> Dict:
        stream = streams.InMemoryRandomAccessStream()
        writer = streams.DataWriter(stream)
        writer.write_bytes(png_bytes)
        await writer.store_async()
        await writer.flush_async()
        writer.detach_stream()
        stream.seek(0)

        decoder = await imaging.BitmapDecoder.create_async(stream)
        bmp = await decoder.get_software_bitmap_async()
        result = await self.engine.recognize_async(bmp)

        raw_text = result.text.strip() if result.text else ""
        lines: List[str] = []
        for line in result.lines:
            line_str = line.text.strip()
            if line_str and len(line_str) > 1:
                lines.append(line_str)

        # Build clean speech text
        # If text is very long (e.g. magazine/book), speak the first 2-3 prominent lines
        if len(lines) == 0:
            speech_text = ""
        elif len(lines) <= 4:
            speech_text = ". ".join(lines)
        else:
            speech_text = f"{'. '.join(lines[:3])}. And {len(lines) - 3} more lines."

        word_count = len(raw_text.split())
        return {
            "text": raw_text,
            "lines": lines,
            "speech_text": speech_text,
            "word_count": word_count,
        }
