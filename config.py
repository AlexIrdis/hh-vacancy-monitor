"""Настройки приложения. Всё читается из переменных окружения (.env)."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

API_VACANCIES = "https://api.hh.ru/vacancies"
VK_SEND = "https://api.vk.com/method/messages.send"


@dataclass(frozen=True)
class Settings:
    # hh.ru
    user_agent: str
    access_token: str
    area: str
    professional_role: str
    employment_form: str
    work_format: str
    labels: tuple[str, ...]
    experience: tuple[str, ...]
    period_days: int
    order_by: str
    per_page: int
    fresh_hours: int
    # vk
    vk_token: str
    vk_peer_id: int
    vk_api_version: str
    # режим
    poll_seconds: int
    db_path: str
    seed_on_first_run: bool
    log_file: str

    @classmethod
    def from_env(cls) -> "Settings":
        def req(name: str) -> str:
            value = os.getenv(name, "").strip()
            if not value:
                raise RuntimeError(f"Заполните {name} в файле .env (образец: .env.example)")
            return value

        def split_csv(name: str) -> tuple[str, ...]:
            return tuple(x.strip() for x in os.getenv(name, "").split(",") if x.strip())

        return cls(
            user_agent=os.getenv("HH_USER_AGENT", "hh-monitor/1.0 (unset@mail.invalid)"),
            access_token=os.getenv("HH_ACCESS_TOKEN", "").strip(),
            area=os.getenv("HH_AREA", "113"),
            professional_role=os.getenv("HH_PROFESSIONAL_ROLE", "124"),
            employment_form=os.getenv("HH_EMPLOYMENT_FORM", "FULL"),
            work_format=os.getenv("HH_WORK_FORMAT", "REMOTE"),
            labels=split_csv("HH_LABEL"),
            experience=split_csv("HH_EXPERIENCE"),
            period_days=int(os.getenv("HH_PERIOD_DAYS", "1")),
            order_by=os.getenv("HH_ORDER_BY", "publication_time"),
            per_page=int(os.getenv("HH_PER_PAGE", "100")),
            fresh_hours=int(os.getenv("FRESH_HOURS", "6")),
            vk_token=req("VK_TOKEN"),
            vk_peer_id=int(req("VK_PEER_ID")),
            vk_api_version=os.getenv("VK_API_VERSION", "5.199"),
            poll_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "120")),
            db_path=os.getenv("STATE_DB", "state.db"),
            seed_on_first_run=os.getenv("SEED_ON_FIRST_RUN", "true").lower() == "true",
            log_file=os.getenv("LOG_FILE", "monitor.log"),
        )

    @dataclass(frozen=True)
    class Settings:
        # ... все предыдущие поля ...
        headless: bool = False  # ← добавить в конец

        @classmethod
        def from_env(cls, headless: bool = False) -> "Settings":
            # ... весь предыдущий код ...
            # и в самом return добавьте:
            return cls(
                # ... все поля как были ...
                headless=headless,
            )