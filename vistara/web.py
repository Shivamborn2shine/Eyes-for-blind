"""
Vistara Vision Web Dashboard & Streaming Server.

Provides:
  - High-framerate MJPEG video streaming at /video_feed
  - Real-time status API at /api/status
  - Remote control actions at /api/action/<name>
  - On-the-fly camera switching at /api/switch_camera
"""
import logging
import threading
import time
from pathlib import Path

import cv2
from flask import Flask, Response, jsonify, render_template, request

# Silence default flask request logging so console remains clean
log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)


def create_web_server(app_instance, host="0.0.0.0", port=5000):
    template_dir = Path(__file__).resolve().parent.parent / "web" / "templates"
    flask_app = Flask(__name__, template_folder=str(template_dir))

    @flask_app.route("/")
    def index():
        return render_template("index.html")

    @flask_app.route("/cam")
    def cam():
        return render_template("cam.html")

    @flask_app.route("/api/upload_frame", methods=["POST"])
    def api_upload_frame():
        import numpy as np
        from vistara.camera import update_remote_frame
        try:
            data = request.get_data()
            if not data:
                return jsonify({"ok": False}), 400
            nparr = np.frombuffer(data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is not None:
                update_remote_frame(img)
                return jsonify({"ok": True})
            return jsonify({"ok": False}), 400
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    def generate_frames():
        while app_instance.running:
            frame = app_instance.camera.read()
            if frame is None:
                time.sleep(0.04)
                continue

            # Draw latest detection boxes on the web stream if available
            dets = getattr(app_instance, "current_web_dets", [])
            for d in dets:
                x1, y1, x2, y2 = d.box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 210, 255), 2)
                label = f"{d.name} {int(d.conf * 100)}%"
                cv2.putText(
                    frame,
                    label,
                    (x1, max(18, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 210, 255),
                    2,
                )

            # Overlay status bar on video stream
            h, w = frame.shape[:2]
            cv2.rectangle(frame, (0, h - 36), (w, h), (15, 20, 28), -1)
            status_txt = getattr(app_instance, "status", "Ready")[:80]
            cv2.putText(
                frame,
                status_txt,
                (12, h - 12),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
            )

            # Compress to JPEG
            ok, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            if not ok:
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
            )
            time.sleep(0.03)

    @flask_app.route("/video_feed")
    def video_feed():
        return Response(
            generate_frames(),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )

    @flask_app.route("/api/status")
    def api_status():
        dets = getattr(app_instance, "current_web_dets", [])
        w = app_instance.camera.width or 1280
        det_data = [
            {"name": d.name, "conf": round(d.conf, 2), "position": d.position(w)}
            for d in dets
        ]

        person_present = any(d.name == "person" for d in dets)

        return jsonify(
            {
                "status": getattr(app_instance, "status", "Ready"),
                "language": app_instance.tr.lang,
                "money_total": app_instance.money_total,
                "continuous_currency": getattr(app_instance, "continuous_currency", False),
                "camera_source": str(app_instance.camera.source),
                "person_in_view": person_present,
                "current_detections": det_data,
                "snapshot": app_instance.memory.snapshot,
                "snapshot_pos": app_instance.memory.snapshot_pos,
                "last_seen": app_instance.memory.last_seen,
                "ocr_result": getattr(app_instance, "ocr_last_result", {}),
                "color_result": getattr(app_instance, "color_last_result", {}),
                "taught_classes": app_instance.teachable.list_classes()
                if hasattr(app_instance, "teachable")
                else {},
            }
        )

    @flask_app.route("/api/teach", methods=["POST"])
    def api_teach():
        data = request.get_json(silent=True) or {}
        label = data.get("label", "").strip()
        if not label:
            return jsonify({"ok": False, "error": "Label is required"}), 400
        app_instance.act_teach(label)
        count = len(app_instance.teachable.classes.get(label.lower(), []))
        return jsonify({"ok": True, "label": label, "count": count})

    @flask_app.route("/api/taught_classes", methods=["GET"])
    def api_taught_classes():
        classes = (
            app_instance.teachable.list_classes()
            if hasattr(app_instance, "teachable")
            else {}
        )
        return jsonify({"ok": True, "classes": classes})

    @flask_app.route("/api/delete_class/<label>", methods=["DELETE"])
    def api_delete_class(label):
        ok = (
            app_instance.teachable.delete_class(label)
            if hasattr(app_instance, "teachable")
            else False
        )
        return jsonify({"ok": ok})

    @flask_app.route("/api/clear_classes", methods=["POST"])
    def api_clear_classes():
        ok = (
            app_instance.teachable.clear_all()
            if hasattr(app_instance, "teachable")
            else False
        )
        return jsonify({"ok": ok})

    @flask_app.route("/api/action/<action_name>", methods=["POST"])
    def api_action(action_name):
        action_name = action_name.lower()
        if action_name == "clear_memory":
            app_instance.memory.clear_snapshot()
            app_instance.say("remember_none")
            return jsonify({"ok": True})
        if action_name == "reset_total":
            app_instance.money_total = 0
            if hasattr(app_instance, "currency"):
                app_instance.currency.reset_session()
            return jsonify({"ok": True})
        if action_name in ("undo_note", "undo_currency"):
            app_instance.act_undo_currency()
            return jsonify({"ok": True, "money_total": app_instance.money_total})
        if action_name in ("continuous_currency", "toggle_continuous_currency"):
            app_instance.act_toggle_continuous_currency()
            return jsonify({"ok": True, "continuous_currency": app_instance.continuous_currency})
        if action_name in ("currency_breakdown", "breakdown"):
            app_instance.act_currency_breakdown()
            bd = app_instance.currency.get_breakdown() if hasattr(app_instance, "currency") else {}
            return jsonify({"ok": True, "breakdown": bd})
        if action_name in ("read_text", "ocr"):
            app_instance.act_read_text()
            return jsonify({"ok": True, "ocr_result": app_instance.ocr_last_result})
        if action_name in ("color", "identify_color"):
            app_instance.act_color()
            return jsonify({"ok": True, "color_result": app_instance.color_last_result})

        # Standard actions supported by hotkeys
        app_instance.hotkeys.actions.put(action_name)
        return jsonify({"ok": True, "action": action_name})

    @flask_app.route("/api/currency_breakdown", methods=["GET"])
    def api_currency_breakdown():
        bd = app_instance.currency.get_breakdown() if hasattr(app_instance, "currency") else {"total": 0, "count": 0, "counts": {}, "history": []}
        return jsonify({"ok": True, "breakdown": bd})

    @flask_app.route("/api/find_item", methods=["POST"])
    def api_find_item():
        data = request.get_json(silent=True) or {}
        item = data.get("item", "").strip()
        if not item:
            return jsonify({"ok": False, "error": "Item query is required"}), 400
        found = app_instance.act_find_item(item)
        return jsonify({"ok": True, "item": item, "found": bool(found), "result": found})

    @flask_app.route("/api/ocr_result", methods=["GET"])
    def api_ocr_result():
        return jsonify({"ok": True, "result": getattr(app_instance, "ocr_last_result", {})})

    @flask_app.route("/api/color_result", methods=["GET"])
    def api_color_result():
        return jsonify({"ok": True, "result": getattr(app_instance, "color_last_result", {})})

    @flask_app.route("/api/switch_camera", methods=["POST"])
    def api_switch_camera():
        data = request.get_json(silent=True) or {}
        source = data.get("source")
        if source is None:
            return jsonify({"ok": False, "error": "No source specified"}), 400

        # Parse integer camera index if numeric string
        if isinstance(source, str) and source.isdigit():
            source = int(source)

        try:
            old_cam = app_instance.camera
            old_cam.stop()

            from vistara.camera import Camera

            new_cam = Camera(source, app_instance.camera.width, app_instance.camera.height)
            if not new_cam.start():
                # Revert if failed
                old_cam.start()
                return jsonify({"ok": False, "error": f"Could not connect to {source}"}), 400

            app_instance.camera = new_cam
            return jsonify({"ok": True, "source": str(source)})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    cert_path = Path(__file__).resolve().parent.parent / "data" / "cert.pem"
    key_path = Path(__file__).resolve().parent.parent / "data" / "key.pem"
    ssl_ctx = (str(cert_path), str(key_path)) if cert_path.exists() and key_path.exists() else None
    proto = "https" if ssl_ctx else "http"

    thread = threading.Thread(
        target=lambda: flask_app.run(
            host=host, port=port, debug=False, use_reloader=False, threaded=True, ssl_context=ssl_ctx
        ),
        daemon=True,
    )
    thread.start()
    print(f"[web] Dashboard live at: {proto}://localhost:{port} (or {proto}://{host}:{port})")
    print(f"[web] iPhone camera streamer: {proto}://192.168.1.7:{port}/cam")
    return thread
