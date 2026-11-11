import os
import re
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

SEARCH_URL = ("https://hh.ru/search/vacancy?"
              "area=113&professional_role=124&employment_form=FULL&work_format=REMOTE"
              "&experience=between1And3&experience=between3And6"
              "&label=accept_labor_contract&search_period=1&order_by=publication_time")

ID_RE = re.compile(r"/vacancy/(\d+)")


def cookies_from_env():
    out = []
    for part in os.getenv("HH_COOKIE", "").split("; "):
        if "=" in part:
            name, value = part.split("=", 1)
            out.append({"name": name.strip(), "value": value.strip(),
                        "domain": ".hh.ru", "path": "/"})
    return out


def fetch_vacancies(headless=False) -> list[dict]:
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir="hh_profile", headless=headless)
        ctx.add_cookies(cookies_from_env())
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        page.goto(SEARCH_URL, wait_until="domcontentloaded")
        # Ждём ПЕРВУЮ ссылку на вакансию вместо фиксированной паузы
        page.wait_for_selector('a[href*="/vacancy/"]', timeout=30000)
        page.wait_for_timeout(2000)   # дождаться дорисовки остальных

        links = page.query_selector_all('a[href*="/vacancy/"]')
        print(f"[DEBUG] ссылок на вакансии в DOM: {len(links)}")

        vacancies, seen = [], set()
        for a in links:
            href = a.get_attribute("href") or ""
            name = (a.inner_text() or "").strip().replace("\n", " ")
            m = ID_RE.search(href)
            if not m or not name or len(name) < 4:
                continue
            vid = m.group(1)
            if vid in seen:
                continue
            seen.add(vid)
            vacancies.append({
                "id": vid,
                "name": name,
                "url": href if href.startswith("http") else f"https://hh.ru{href}",
            })

        ctx.close()
    return vacancies


if __name__ == "__main__":
    data = fetch_vacancies(headless=False)
    print(f"Спарсено вакансий: {len(data)}")
    for v in data[:5]:
        print(f"  - {v['id']} | {v['name']} | {v['url']}")