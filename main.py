"""
Vistara Vision - main application.

    .venv\\Scripts\\python main.py              # laptop webcam
    .venv\\Scripts\\python main.py --source 1   # USB webcam
    .venv\\Scripts\\python main.py --source http://192.168.1.5:4747/video   # DroidCam
    .venv\\Scripts\\python main.py --source "screen:LonelyScreen"         # mirrored iPhone (AirPlay)
    .venv\\Scripts\\python main.py --list-windows                         # find the mirror window title
"""
import argparse
import queue
import sys
import threading
import time

import cv2

# Windows consoles default to cp1252 -> printing Hindi would crash. Force UTF-8 and line buffering.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass

import config
from vistara.camera import Camera
from vistara.currency import CurrencyRecognizer
from vistara.detector import ObjectDetector, draw
from vistara.hotkeys import Hotkeys
from vistara.i18n import I18N
from vistara.memory import ItemMemory
from vistara.speech import Speaker, beep
from vistara.teachable import TeachableClassifier


class VistaraApp:
    def __init__(self, source, lang):
        self.tr = I18N(lang)
        self.tr_en = I18N("en")
        self.speaker = Speaker(config.TTS_CACHE_DIR, config.SPEECH_RATE)
        self.camera = Camera(source, config.FRAME_WIDTH, config.FRAME_HEIGHT)
        self.memory = ItemMemory(config.MEMORY_FILE)
        self.teachable = TeachableClassifier(config.TEACHABLE_FILE)
        self.hotkeys = Hotkeys(config.HOTKEYS)
        self.running = True
        self.status = "Starting..."
        self.overlay_dets = []
        self.overlay_until = 0
        self.money_total = 0
        self.money_last = 0
        self.continuous_currency = False
        self.continuous_last_detected = None
        self.continuous_last_time = 0
        self.ocr_last_result = {"text": "", "lines": [], "speech_text": "", "time": 0}
        self.color_last_result = {"name_en": "", "name_hi": "", "hex": "", "conf": 0, "time": 0}
        self.ocr = None
        self.color_id = None
        # auto-watch state
        self.last_person_time = time.time()
        self.auto_alerted = False
        self.person_armed = False   # user seen since last REMEMBER
        self.current_web_dets = []  # live detections for web dashboard

    # ------------------------------------------------------------------ speech
    def say(self, key, interrupt=False, **kw):
        """kw values may be callables f(i18n) so they get localised + English fallback."""
        loc = {k: (v(self.tr) if callable(v) else v) for k, v in kw.items()}
        eng = {k: (v(self.tr_en) if callable(v) else v) for k, v in kw.items()}
        text = self.tr.t(key, **loc)
        fallback = self.tr_en.t(key, **eng)
        self.status = fallback
        self.speaker.say(text, self.tr.lang, fallback_en=fallback, interrupt=interrupt)

    # ------------------------------------------------------------------ setup
    def setup(self):
        print("Loading models, please wait...")
        if not self.camera.start():
            self.say("camera_error")
            self.speaker.wait()
            return False
        self.detector = ObjectDetector(config.YOLO_MODEL, config.DETECTION_CONFIDENCE,
                                       config.DETECTION_IMG_SIZE, teachable=self.teachable)
        self.detector.detect(self.camera.read())  # warm-up
        self.currency = CurrencyRecognizer(config.CURRENCY_MODEL, config.CURRENCY_REF_DIR,
                                           config.CURRENCY_MIN_CONFIDENCE,
                                           config.ORB_MIN_GOOD_MATCHES)
        try:
            from vistara.ocr import TextReader
            self.ocr = TextReader()
        except Exception as e:
            print("[ocr] Could not initialize TextReader:", e)

        try:
            from vistara.color import ColorIdentifier
            self.color_id = ColorIdentifier()
        except Exception as e:
            print("[color] Could not initialize ColorIdentifier:", e)

        if getattr(config, "ENABLE_WEB_SERVER", True):
            try:
                from vistara.web import create_web_server
                create_web_server(self, getattr(config, "WEB_HOST", "0.0.0.0"),
                                  getattr(config, "WEB_PORT", 5000))
            except Exception as e:
                print("[web] Could not start web server:", e)
        self.say("welcome")
        return True

    # ------------------------------------------------------------------ actions
    def act_currency(self):
        beep("scan")
        if not self.currency.ready and not (self.teachable and self.teachable.classes):
            self.say("note_unsure")
            return
        frames = self.camera.frames(config.CURRENCY_VOTE_FRAMES, delay=0.12)
        value, agree = self.currency.predict_vote(frames, teachable=self.teachable, ocr=self.ocr, color_id=self.color_id)
        if value is None:
            self.say("note_unsure" if agree > 0 else "note_none", interrupt=True)
            return
        now = time.time()
        if now - self.money_last > 60:      # new counting session after 1 min idle
            self.money_total = 0
            self.currency.reset_session()
        self.money_last = now
        val_int = int(value)
        self.currency.add_note(val_int)
        self.money_total = sum(self.currency.history)
        self.say("note_found", interrupt=True, value=value)
        if len(self.currency.history) > 1:
            self.say("total", total=self.money_total)

    def act_currency_breakdown(self):
        breakdown = self.currency.get_breakdown()
        if not breakdown.get("history"):
            self.say("undo_none", interrupt=True)
            return
        total = breakdown["total"]
        count = breakdown["count"]
        parts = []
        for d, c in breakdown["counts"].items():
            if self.tr.lang == "hi":
                parts.append(f"{c} note {d} rupaye ke")
            else:
                parts.append(f"{c} note{'s' if c > 1 else ''} of {d} rupees")
        detail = ", ".join(parts)
        self.say("currency_breakdown", interrupt=True, total=total, count=count, details=detail)

    def act_undo_currency(self):
        undone, total = self.currency.undo_last()
        self.money_total = total
        if undone is not None:
            beep("ok")
            self.say("undo_note", interrupt=True, value=undone, total=total)
        else:
            self.say("undo_none", interrupt=True)

    def act_toggle_continuous_currency(self):
        self.continuous_currency = not self.continuous_currency
        self.continuous_last_detected = None
        if self.continuous_currency:
            beep("ok")
            self.say("auto_currency_on", interrupt=True)
        else:
            self.say("auto_currency_off", interrupt=True)

    def act_read_text(self):
        beep("scan")
        self.say("read_text_reading")
        frame = self.camera.read()
        if frame is None or not self.ocr or not self.ocr.ready:
            self.say("read_text_none", interrupt=True)
            return
        res = self.ocr.read_text(frame)
        if res.get("text"):
            self.ocr_last_result = {**res, "time": time.time()}
            beep("ok")
            self.say("read_text_found", interrupt=True, text=res["speech_text"])
        else:
            self.say("read_text_none", interrupt=True)

    def act_color(self):
        beep("scan")
        self.say("color_inspecting")
        frame = self.camera.read()
        if frame is None or not self.color_id:
            return
        res = self.color_id.identify(frame)
        self.color_last_result = {**res, "time": time.time()}
        beep("ok")
        color_name = res["name_hi"] if self.tr.lang == "hi" else res["name_en"]
        self.say("color_found", interrupt=True, color=color_name)

    def _scan(self, allowed, n=config.SNAPSHOT_FRAMES):
        frames = self.camera.frames(n, delay=0.1)
        counts, pos, prox, last = self.detector.stable_scan(frames, allowed, config.MIN_HITS_RATIO)
        self.overlay_dets, self.overlay_until = last, time.time() + 4
        return counts, pos, prox

    def act_remember(self):
        beep("scan")
        self.say("scanning")
        excluded = {"background", "empty", "nothing"}
        custom_items = {k for k in self.teachable.classes.keys() if k.lower() not in excluded}
        tracked = set(config.TRACKED_ITEMS).union(custom_items)
        counts, pos, prox = self._scan(tracked)
        if not counts:
            self.say("remember_none")
            return
        self.memory.remember(counts, pos, prox)
        self.auto_alerted = False
        self.person_armed = False
        self.last_person_time = time.time()
        self.say("remembered", items=lambda tr: tr.items_phrase(counts, pos, prox))

    def act_leaving(self):
        beep("scan")
        if not self.memory.has_snapshot():
            self.say("no_memory")
            return
        self.say("scanning")
        counts, pos, prox = self._scan(set(self.memory.snapshot))
        left, picked, lpos, lprox = self.memory.leaving_audit(counts, pos, prox)
        if left:
            beep("alert")
            self.say("left_items", items=lambda tr: tr.items_phrase(left, lpos, lprox))
        else:
            self.say("nothing_left")
            self.memory.clear_snapshot()

    def act_find_item(self, query: str):
        found = self.memory.find_item(query)
        if not found:
            self.say("item_not_found", interrupt=True, name=query)
            return None
        clock = found["clock_hi"] if self.tr.lang == "hi" else found["clock_en"]
        prox = found["prox_hi"] if self.tr.lang == "hi" else found["prox_en"]
        m = found["minutes_ago"]
        def ago(tr, m=m):
            if m < 1:
                return tr.t("just_now")
            return tr.t("min_ago", n=m) if m < 60 else tr.t("hr_ago", n=m // 60)
        self.say("where_item_precise", interrupt=True,
                 item=lambda tr, n=found["name"]: tr.obj(n),
                 clock=clock, prox=prox, ago=ago)
        return found

    def act_describe(self):
        beep("scan")
        counts, pos, prox = self._scan(None, n=4)
        if not counts:
            self.say("describe_none")
            return
        self.memory.update_seen({k: v for k, v in counts.items() if k in config.TRACKED_ITEMS}, pos, prox)
        self.memory.save()
        self.say("describe", items=lambda tr: tr.items_phrase(counts, pos, prox))

    def act_where(self):
        if not self.memory.last_seen:
            self.say("where_none")
            return
        recent = sorted(self.memory.last_seen.items(), key=lambda kv: -kv[1]["time"])[:3]
        for name, info in recent:
            mins = int((time.time() - info["time"]) / 60)
            def ago(tr, m=mins):
                if m < 1:
                    return tr.t("just_now")
                return tr.t("min_ago", n=m) if m < 60 else tr.t("hr_ago", n=m // 60)
            clock = info.get("clock_hi" if self.tr.lang == "hi" else "clock_en", info.get("pos", "center"))
            prox = info.get("prox_hi" if self.tr.lang == "hi" else "prox_en", "nearby")
            self.say("where_item_precise", item=lambda tr, n=name: tr.obj(n),
                     clock=clock, prox=prox, ago=ago)

    def act_teach(self, label="custom object"):
        beep("scan")
        self.say("teach_start", name=label)
        # Give user 2.2 seconds to hold up the item into the center of the camera
        time.sleep(2.2)
        beep("scan")
        frames = self.camera.frames(10, delay=0.12)
        count = self.teachable.learn(label, frames)
        if count > 0:
            beep("ok")
            self.say("teach_done", name=label)
        else:
            self.say("teach_empty")

    def act_language(self):
        self.tr.toggle()
        self.say("lang_switched", interrupt=True)

    def act_help(self):
        self.say("help", interrupt=True)

    # ------------------------------------------------------------------ threads
    def action_worker(self):
        table = {
            "currency": self.act_currency,
            "currency_breakdown": self.act_currency_breakdown,
            "remember": self.act_remember,
            "leaving": self.act_leaving,
            "describe": self.act_describe,
            "where": self.act_where,
            "language": self.act_language,
            "teach": self.act_teach,
            "read_text": self.act_read_text,
            "color": self.act_color,
            "undo_note": self.act_undo_currency,
            "continuous_currency": self.act_toggle_continuous_currency,
            "help": self.act_help,
        }
        while self.running:
            try:
                action = self.hotkeys.actions.get(timeout=0.2)
            except queue.Empty:
                continue
            if action == "quit":
                self.running = False
                break
            # drop duplicate presses that piled up while busy
            while not self.hotkeys.actions.empty():
                nxt = self.hotkeys.actions.get()
                if nxt == "quit":
                    self.running = False
                    return
            beep("ok")
            try:
                table[action]()
            except Exception as e:
                print(f"[action {action}] error:", e)

    def auto_watch(self):
        """Background: log item sightings + warn if user walks away leaving items."""
        import gc
        loop_count = 0
        last_disk_save = time.time()
        while self.running:
            time.sleep(config.AUTO_WATCH_INTERVAL)
            loop_count += 1
            if loop_count % 100 == 0:
                gc.collect()

            frame = self.camera.read()
            if frame is None:
                continue
            try:
                dets = self.detector.detect(frame)
                self.current_web_dets = dets
            except Exception:
                continue
            w = frame.shape[1]
            if any(d.name == "person" for d in dets):
                self.last_person_time = time.time()
                self.auto_alerted = False
                self.person_armed = True

            # Filter out negative background/empty classes from tracked items
            excluded = {"background", "empty", "nothing"}
            custom_items = {k for k in self.teachable.classes.keys() if k.lower() not in excluded}
            tracked = set(config.TRACKED_ITEMS).union(custom_items)

            items = [d for d in dets if d.name in tracked]
            if items:
                counts = {}
                pos = {}
                prox = {}
                frame_area = frame.shape[0] * frame.shape[1]
                for d in items:
                    counts[d.name] = counts.get(d.name, 0) + 1
                    pos[d.name] = d.position(w)
                    prox[d.name] = d.proximity(frame_area)
                self.memory.update_seen(counts, pos, prox)

            # Continuous Currency Auto-Count check
            if self.continuous_currency and (time.time() - self.continuous_last_time > 2.0):
                val, conf = self.currency.predict(frame, teachable=self.teachable, ocr=self.ocr, color_id=self.color_id)
                if val is not None and conf > 0.65:
                    if val != self.continuous_last_detected:
                        self.continuous_last_detected = val
                        self.continuous_last_time = time.time()
                        self.act_currency()
                else:
                    self.continuous_last_detected = None

            if (config.AUTO_WATCH and self.memory.has_snapshot() and not self.auto_alerted
                    and self.person_armed
                    and time.time() - self.last_person_time > config.AUTO_WATCH_ABSENT_SECONDS):
                # confirm with a stable multi-frame scan before alarming
                counts, pos, prox = self._scan(set(self.memory.snapshot), n=5)
                left, picked, lpos, lprox = self.memory.leaving_audit(counts, pos, prox)
                self.auto_alerted = True
                if left:
                    beep("alert")
                    self.say("auto_left", items=lambda tr: tr.items_phrase(left, lpos, lprox))

            now = time.time()
            if now - last_disk_save > 15.0:
                self.memory.save()
                last_disk_save = now

    # ------------------------------------------------------------------ main loop
    def run(self):
        if not self.setup():
            return
        threading.Thread(target=self.action_worker, daemon=True).start()
        threading.Thread(target=self.auto_watch, daemon=True).start()
        win = "Vistara Vision"
        while self.running:
            frame = self.camera.read()
            if config.SHOW_PREVIEW and frame is not None:
                if time.time() < self.overlay_until:
                    draw(frame, self.overlay_dets)
                h = frame.shape[0]
                cv2.rectangle(frame, (0, h - 60), (frame.shape[1], h), (20, 20, 20), -1)
                cv2.putText(frame, self.status[:110], (10, h - 35), cv2.FONT_HERSHEY_SIMPLEX,
                            0.55, (255, 255, 255), 1)
                cv2.putText(frame, f"[C] Note  [R] Remember  [L] Leaving  [D] Describe  [W] Where  "
                            f"[H] Lang:{self.tr.lang.upper()}  [Esc] Quit",
                            (10, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 255), 1)
                if self.memory.has_snapshot():
                    cv2.putText(frame, "Remembered: " + ", ".join(self.memory.snapshot),
                                (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (80, 255, 120), 2)
                cv2.imshow(win, frame)
                key = cv2.waitKey(30)
                self.hotkeys.feed_cv_key(key)
                if cv2.getWindowProperty(win, cv2.WND_PROP_VISIBLE) < 1:
                    self.running = False
            else:
                time.sleep(0.05)
        self.say("goodbye", interrupt=True)
        self.speaker.wait(5)
        self.memory.save()
        self.camera.stop()
        cv2.destroyAllWindows()


def parse_source(s):
    return int(s) if s is not None and s.isdigit() else s


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Vistara Vision - assistive vision for the blind")
    ap.add_argument("--source", help="camera index (0,1..), DroidCam URL, or screen:<window title>")
    ap.add_argument("--list-windows", action="store_true",
                    help="list visible window titles (to pick the iPhone mirror window)")
    ap.add_argument("--lang", choices=["en", "hi"], default=config.DEFAULT_LANGUAGE)
    ap.add_argument("--no-preview", action="store_true")
    ap.add_argument("--port", type=int, default=getattr(config, "WEB_PORT", 5000))
    ap.add_argument("--no-web", action="store_true")
    args = ap.parse_args()
    if args.list_windows:
        from vistara.screen_source import list_windows
        for _, title in list_windows():
            print(" -", title)
        sys.exit(0)
    if args.no_preview:
        config.SHOW_PREVIEW = False
    if args.no_web:
        config.ENABLE_WEB_SERVER = False
    config.WEB_PORT = args.port
    src = parse_source(args.source) if args.source is not None else config.CAMERA_SOURCE
    VistaraApp(src, args.lang).run()
