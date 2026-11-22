import json
import logging
import threading
import urllib.error
import urllib.request

from app.core.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)


def _post_telegram(req: urllib.request.Request) -> None:
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            response.read()
    except (urllib.error.URLError, TimeoutError) as e:
        logger.error("Failed to send Telegram notification: %s", e)


def send_message(text: str, *, background: bool = False) -> None:
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    if background:
        threading.Thread(target=_post_telegram, args=(req,), daemon=True).start()
    else:
        _post_telegram(req)
