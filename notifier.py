"""Отправка уведомлений в ВК. Работает со словарями {"id","name","url"}."""
from __future__ import annotations

import logging
import random
import time

import requests

from config import VK_SEND, Settings

log = logging.getLogger("monitor.vk")

VK_MESSAGE_LIMIT = 4096
VK_ERR_TOO_MANY = 6          # "слишком много запросов в секунду"
VK_MAX_ATTEMPTS = 4


class VkError(RuntimeError):
    pass


def format_vacancy(v: dict) -> str:
    """Название + ссылка — ровно то, что требуется в ТЗ."""
    lines = [f"🆕 {v.get('name') or '(без названия)'}"]
    if v.get("url"):
        lines.append(v["url"])
    return "\n".join(lines)[:VK_MESSAGE_LIMIT]


def send(session: requests.Session, s: Settings, text: str) -> int:
    payload = {
        "peer_id": s.vk_peer_id,
        "message": text[:VK_MESSAGE_LIMIT],
        # random_id обязателен и уникален: иначе ВК склеит одинаковые сообщения
        "random_id": random.randint(1, 2 ** 31 - 1),
        "access_token": s.vk_token,
        "v": s.vk_api_version,
        "disable_mentions": 1,
    }

    for attempt in range(1, VK_MAX_ATTEMPTS + 1):
        response = session.post(VK_SEND, data=payload, timeout=15)
        try:
            data = response.json()
        except ValueError as exc:
            raise VkError(f"ВК вернул не-JSON (HTTP {response.status_code})") from exc

        if "response" in data:
            return int(data["response"])

        error = data.get("error") or {}
        if error.get("error_code") == VK_ERR_TOO_MANY:
            time.sleep(0.5 * attempt)
            continue
        raise VkError(f"ВК error {error.get('error_code')}: {error.get('error_msg')}")

    raise VkError("ВК: не отправили из-за лимита запросов в секунду")