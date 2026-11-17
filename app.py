
#!/usr/bin/env python3
"""SEIJI Notify Console — demo-only Flask backend.

No SMS gateways, OTP endpoints, phone numbers, or voice-call providers.
All notification previews are simulated locally.
"""

import os
import threading
import uuid
from collections import deque
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, make_response, render_template, request, session

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "change-this-demo-secret-before-deploy"
)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(os.environ.get("RENDER")),
    MAX_CONTENT_LENGTH=16 * 1024,
)

LOCK = threading.RLock()
SESSIONS = {}
MANILA = ZoneInfo("Asia/Manila")

ALLOWED_GROUPS = {
    "Subscribed users",
    "Test group",
    "Myself (preview)"
}


def now_text():
    return datetime.now(MANILA).strftime("%I:%M:%S %p")


def get_state():
    sid = session.get("sid")

    if not sid:
        sid = uuid.uuid4().hex
        session["sid"] = sid

    with LOCK:
        if sid not in SESSIONS:
            SESSIONS[sid] = {
                "recipients": 24,
                "queued": 0,
                "delivered_demo": 0,
                "logs": deque(maxlen=60),
            }

            SESSIONS[sid]["logs"].append({
                "time": now_text(),
                "event": "Demo console initialized",
                "recipient": "Local preview",
                "status": "READY",
                "kind": "system",
            })

        return SESSIONS[sid]


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"

    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )

    return response


@app.route("/")
def index():
    response = make_response(
        render_template("index.html")
    )

    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/api/status")
def api_status():
    state = get_state()

    with LOCK:
        return jsonify({
            "ok": True,
            "mode": "DEMO",
            "online": True,
            "recipients": state["recipients"],
            "queued": state["queued"],
            "delivered_demo": state["delivered_demo"],
            "logs": list(state["logs"]),
        })


@app.route("/api/demo/preview", methods=["POST"])
def api_demo_preview():
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return jsonify({
            "ok": False,
            "error": "Invalid request body."
        }), 400

    message = str(
        payload.get("message", "")
    ).strip()

    group = str(
        payload.get("group", "Subscribed users")
    ).strip()

    if not message:
        return jsonify({
            "ok": False,
            "error": "Write a message first."
        }), 400

    if len(message) > 160:
        return jsonify({
            "ok": False,
            "error": "Keep the preview under 160 characters."
        }), 400

    if group not in ALLOWED_GROUPS:
        return jsonify({
            "ok": False,
            "error": "Choose a valid demo recipient group."
        }), 400

    state = get_state()

    with LOCK:
        state["delivered_demo"] += 1

        state["logs"].appendleft({
            "time": now_text(),
            "event": "Notification preview generated",
            "recipient": group,
            "status": "SIMULATED",
            "kind": "demo",
        })

        result = {
            "ok": True,
            "message": (
                "Demo preview created. No SMS or call was sent."
            ),
            "delivered_demo": state["delivered_demo"],
            "logs": list(state["logs"]),
        }

    return jsonify(result)


@app.route("/api/ping")
def api_ping():
    return jsonify({
        "ok": True,
        "mode": "DEMO"
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
