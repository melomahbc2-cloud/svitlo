"""Одна перевірка світла (для запуску за розкладом у GitHub Actions)."""
import json
import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import tinytuya

TZ = ZoneInfo("Europe/Kyiv")
STATE_FILE = "state.json"
DEVICE_ID = os.environ["TUYA_DEVICE_ID"]

cloud = tinytuya.Cloud(
    apiRegion=os.environ["TUYA_REGION"],
    apiKey=os.environ["TUYA_KEY"],
    apiSecret=os.environ["TUYA_SECRET"],
    apiDeviceID=DEVICE_ID,
)


def notify(text):
    requests.post(
        f"https://api.telegram.org/bot{os.environ['TG_TOKEN']}/sendMessage",
        data={"chat_id": os.environ["TG_CHAT_ID"], "text": text},
        timeout=15,
    )


def is_online():
    """True/False, або None якщо хмара не відповіла."""
    try:
        res = cloud.getconnectstatus(DEVICE_ID)
        if isinstance(res, bool):
            return res
        if isinstance(res, dict):
            return bool(res.get("result", res.get("online")))
    except Exception as e:
        print("Помилка Tuya:", e)
    return None


def fmt(seconds):
    h, m = int(seconds // 3600), int(seconds % 3600 // 60)
    return f"{h} год {m} хв" if h else f"{m} хв"


def load():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return None


def save(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def main():
    cur = is_online()
    if cur is None:
        print("Немає відповіді від Tuya, пропускаю.")
        return

    state = load()
    if state is None:
        save({"online": cur, "since": time.time()})
        print("Перший запуск, стан збережено:", cur)
        return

    if cur == state["online"]:
        print("Без змін:", cur)
        return

    # Стан змінився: перевіряємо ще раз через хвилину, щоб уникнути хибних тривог
    time.sleep(60)
    if is_online() != cur:
        print("Зміна не підтвердилась, пропускаю.")
        return

    now = time.time()
    stamp = datetime.now(TZ).strftime("%H:%M, %d.%m")
    dur = fmt(now - state["since"])
    if cur:
        notify(f"✅ Світло з'явилось, {stamp}\nНе було: {dur}")
    else:
        notify(f"💡 Світло пропало, {stamp}\nБуло: {dur}")
    save({"online": cur, "since": now})


if __name__ == "__main__":
    main()
