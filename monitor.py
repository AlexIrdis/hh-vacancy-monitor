"""Точка входа: один проход (--once) или бесконечный цикл."""
from __future__ import annotations

import argparse
import logging
import logging.handlers
import sys
import time
from datetime import datetime

import requests

import hh_client
import notifier
from config import Settings
from store import Store

log = logging.getLogger("monitor")


def setup_logging(log_file: str, verbose: bool = False) -> None:
    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)

    rotating = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    rotating.setFormatter(fmt)
    root.addHandler(rotating)


def tick(cfg: Settings, store: Store, session: requests.Session,
         headless: bool = False) -> dict:
    """Один цикл: получить → сравнить → запомнить → отправить."""
    vacancies = hh_client.fetch_vacancies(headless=headless)

    # СТОРОЖ: пустая выборка — это всегда инцидент, а не «новых нет»
    if not vacancies:
        raise RuntimeError(
            "Пустая выборка: 403/капча, протухла сессия или сменилась разметка сайта"
        )

    known = store.known_ids()
    fresh = [v for v in vacancies if v["id"] not in known]

    # Холодный старт: молча запоминаем всю выдачу
    if cfg.seed_on_first_run and store.is_empty():
        store.remember(vacancies, notified=True)
        notifier.send(
            session, cfg,
            f"✅ Мониторинг запущен {datetime.now():%d.%m.%Y %H:%M}\n"
            f"Запомнено вакансий: {len(vacancies)}\n"
            f"Интервал опроса: {cfg.poll_seconds} c\n"
            f"Дальше будут приходить только НОВЫЕ.",
        )
        return {"fetched": len(vacancies), "new": 0, "sent": 0, "seeded": True}

    store.remember(fresh, notified=False)

    sent = 0
    for vacancy in store.unnotified():
        try:
            notifier.send(session, cfg, notifier.format_vacancy(vacancy))
            store.mark_notified(vacancy["id"])
            sent += 1
            log.info("→ отправлено: %s | %s", vacancy["name"], vacancy["url"])
            time.sleep(0.35)
        except notifier.VkError as exc:
            log.error("ВК не принял %s: %s — повторим на следующем тике",
                      vacancy["id"], exc)
            break

    return {"fetched": len(vacancies), "new": len(fresh), "sent": sent, "seeded": False}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Мониторинг новых вакансий hh.ru с уведомлениями в ВК")
    parser.add_argument("--once", action="store_true",
                        help="один проход и выход (для планировщика)")
    parser.add_argument("--headless", action="store_true",
                        help="без окна браузера")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    try:
        cfg = Settings.from_env()
    except RuntimeError as exc:
        print(f"ОШИБКА КОНФИГУРАЦИИ: {exc}", file=sys.stderr)
        return 2

    setup_logging(cfg.log_file, args.verbose)

    store = Store(cfg.db_path)
    session = requests.Session()
    failures = 0

    try:
        while True:
            wait = cfg.poll_seconds
            try:
                stats = tick(cfg, store, session, headless=args.headless)
                if failures:
                    log.info("Связь восстановлена после %s ошибок", failures)
                    try:
                        notifier.send(session, cfg,
                                      f"✅ Мониторинг восстановился после {failures} ошибок")
                    except Exception:
                        pass
                    failures = 0

                if stats["seeded"]:
                    log.info("Первый прогон: запомнено %s без уведомлений",
                             stats["fetched"])
                elif stats["new"]:
                    log.info("НОВЫХ: %s | отправлено: %s", stats["new"], stats["sent"])
                else:
                    log.info("Новых нет (всего %s)", stats["fetched"])

                removed = store.purge_older_than_days(30)
                if removed:
                    log.info("Очистка: -%s старых записей", removed)

            except Exception:
                failures += 1
                log.exception("Ошибка прогона №%s", failures)
                wait = min(cfg.poll_seconds * 3, 600)
                if failures == 3:
                    try:
                        notifier.send(session, cfg,
                                      "🛑 Мониторинг: 3 ошибки подряд. Смотрите monitor.log")
                    except Exception:
                        pass

            if args.once:
                return 0
            time.sleep(wait)

    except KeyboardInterrupt:
        log.info("Остановлено пользователем (Ctrl+C)")
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    sys.exit(main())