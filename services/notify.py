# services/notify.py
from __future__ import annotations
import requests

def send_webhook(url: str, text: str, timeout: tuple[float, float] = (3.0, 10.0)) -> bool:
    """
    Posts a simple message to Slack/Discord-compatible webhooks.
    Slack expects {"text": "..."}; Discord expects {"content": "..."}.
    Returns True on 2xx, else False (swallows errors).
    """
    if not url or not text:
        return False

    headers = {"Content-Type": "application/json"}
    # Default Slack payload
    payload = {"text": text}

    u = url.lower()
    if "discord.com/api/webhooks" in u or "discordapp.com/api/webhooks" in u:
        payload = {"content": text}

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=timeout)
        r.raise_for_status()
        return  True
    except Exception:
        return False
