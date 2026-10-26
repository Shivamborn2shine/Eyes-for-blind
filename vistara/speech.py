"""
Speech output in English / Hindi.

Strategy (works fully offline whenever possible):
 1. Windows SAPI voices (incl. OneCore voices like "Microsoft Kalpana/Hemant - Hindi"
    which you get free by adding the Hindi speech pack in Windows Settings).
 2. If no Hindi voice is installed -> Google TTS (gTTS) with a local mp3 cache, so
    each sentence needs the internet only the first time.
 3. If that also fails -> speak the English sentence instead.
"""
import hashlib
import queue
import sys
import threading
import time

ONECORE_PATH = r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech_OneCore\Voices"
SAPI_PATH = r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices"
LANG_CODES = {"en": ("409", "809", "4009", "c09"), "hi": ("439",)}


class Speaker:
    def __init__(self, cache_dir, rate_wpm=165):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.rate_wpm = rate_wpm
        self.q: "queue.Queue[tuple]" = queue.Queue()
        self.busy = threading.Event()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    # ------------------------------------------------------------ public API
    def say(self, text: str, lang: str = "en", fallback_en: str | None = None,
            interrupt: bool = False):
        if interrupt:
            self.clear()
        print(f"[SPEAK/{lang}] {text}")
        self.q.put((text, lang, fallback_en))

    def clear(self):
        try:
            while True:
                self.q.get_nowait()
        except queue.Empty:
            pass

    def wait(self, timeout=15):
        end = time.time() + timeout
        while (not self.q.empty() or self.busy.is_set()) and time.time() < end:
            time.sleep(0.05)

    # ------------------------------------------------------------ worker
    def _worker(self):
        self._init_engines()
        while True:
            text, lang, fallback = self.q.get()
            self.busy.set()
            try:
                ok = self._speak_sapi(text, lang)
                if not ok and lang != "en":
                    ok = self._speak_gtts(text, lang)
                if not ok:
                    self._speak_sapi(fallback or text, "en") or self._speak_pyttsx3(fallback or text)
            except Exception as e:  # never let the speech thread die
                print("[speech error]", e)
            finally:
                self.busy.clear()

    def _init_engines(self):
        self.sapi = None
        self.voices = {}
        self.pg_ready = False
        if sys.platform.startswith("win"):
            try:
                import comtypes
                import comtypes.client
                comtypes.CoInitialize()
                self.sapi = comtypes.client.CreateObject("SAPI.SpVoice")
                # SAPI rate is -10..10; 0 ~= 165 wpm
                self.sapi.Rate = max(-10, min(10, int((self.rate_wpm - 165) / 15)))
                for path in (SAPI_PATH, ONECORE_PATH):
                    try:
                        cat = comtypes.client.CreateObject("SAPI.SpObjectTokenCategory")
                        cat.SetId(path, False)
                        tokens = cat.EnumerateTokens()
                        for i in range(tokens.Count):
                            tok = tokens.Item(i)
                            try:
                                code = tok.GetAttribute("Language").lower()
                            except Exception:
                                code = ""
                            for lang, codes in LANG_CODES.items():
                                if any(c in code.split(";") for c in codes) and lang not in self.voices:
                                    self.voices[lang] = tok
                    except Exception:
                        pass
                names = {k: v.GetDescription() for k, v in self.voices.items()}
                print("[speech] voices:", names or "default only")
                if "hi" not in self.voices:
                    print("[speech] No offline Hindi voice found -> will use gTTS (cached). "
                          "Tip: Settings > Time & Language > Speech > Add voices > Hindi.")
            except Exception as e:
                print("[speech] SAPI unavailable:", e)
                self.sapi = None

    def _speak_sapi(self, text, lang):
        if self.sapi is None:
            return False
        if lang != "en" and lang not in self.voices:
            return False
        try:
            if lang in self.voices:
                self.sapi.Voice = self.voices[lang]
            self.sapi.Speak(text)
            return True
        except Exception as e:
            print("[speech] SAPI failed:", e)
            return False

    def _speak_gtts(self, text, lang):
        path = self.cache_dir / f"{lang}_{hashlib.md5(text.encode('utf-8')).hexdigest()}.mp3"
        if not path.exists():
            try:
                from gtts import gTTS
                gTTS(text=text, lang=lang).save(str(path))
            except Exception as e:
                print("[speech] gTTS failed (offline?):", e)
                return False
        return self._play_mp3(path)

    def _play_mp3(self, path):
        # 1. Native Windows Multimedia API (zero external dependencies, 100% offline)
        if sys.platform.startswith("win"):
            try:
                import ctypes
                import uuid
                alias = f"mp3_{uuid.uuid4().hex[:8]}"
                p = str(path.resolve())
                ret = ctypes.windll.winmm.mciSendStringW(f'open "{p}" type mpegvideo alias {alias}', None, 0, None)
                if ret == 0:
                    ctypes.windll.winmm.mciSendStringW(f'play {alias} wait', None, 0, None)
                    ctypes.windll.winmm.mciSendStringW(f'close {alias}', None, 0, None)
                    return True
            except Exception as e:
                print("[speech] winmm playback warning:", e)

        # 2. Fallback to pygame only if installed
        try:
            import os
            os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
            import pygame
            if not self.pg_ready:
                pygame.mixer.init()
                self.pg_ready = True
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
            pygame.mixer.music.unload()
            return True
        except ImportError:
            return False
        except Exception as e:
            print("[speech] mp3 playback fallback failed:", e)
            return False

    def _speak_pyttsx3(self, text):
        try:
            import pyttsx3
            eng = pyttsx3.init()
            eng.setProperty("rate", self.rate_wpm)
            eng.say(text)
            eng.runAndWait()
            eng.stop()
            return True
        except Exception as e:
            print("[speech] pyttsx3 failed:", e)
            return False


def beep(kind="ok"):
    """Short audio cue so the user knows a key press was received."""
    try:
        import winsound
        freq, dur = {"ok": (880, 120), "scan": (660, 80), "alert": (1200, 350)}.get(kind, (880, 120))
        threading.Thread(target=winsound.Beep, args=(freq, dur), daemon=True).start()
    except Exception:
        pass
