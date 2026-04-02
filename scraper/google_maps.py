import random
import re
import time
from typing import Dict, List, Optional

from playwright.sync_api import Page, sync_playwright

from config import settings


def _parse_rating_text(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    match = re.search(r"([0-5](?:[.,]\d)?)", text.replace(",", "."))
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def _parse_reviews_count(text: Optional[str]) -> int:
    if not text:
        return 0
    text = text.replace(".", "").replace(",", "")
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else 0


def _scroll_results(page: Page, max_idle: int = 3):
    idle = 0
    last_height = 0
    while idle < max_idle:
        page.mouse.wheel(0, 20000)
        time.sleep(1.2)
        new_height = page.evaluate("document.querySelector('body').scrollHeight")
        if new_height == last_height:
            idle += 1
        else:
            idle = 0
            last_height = new_height


def _extract_card_basic(card) -> Dict:
    nome = card.get_attribute("aria-label")
    rating_el = card.query_selector("span[aria-label*='estrelas'], span[aria-label*='stars']")
    nota_media = _parse_rating_text(rating_el.get_attribute("aria-label") if rating_el else None)
    reviews_el = card.query_selector("span[aria-label*='avaliação'], span[aria-label*='reviews']")
    total_avaliacoes = _parse_reviews_count(
        reviews_el.get_attribute("aria-label") if reviews_el else (rating_el.inner_text() if rating_el else "")
    )
    categoria_el = card.query_selector("div.fontBodyMedium")
    categoria = categoria_el.inner_text().strip() if categoria_el else None
    return {
        "nome": nome,
        "nota_media": nota_media,
        "total_avaliacoes": total_avaliacoes,
        "categoria": categoria,
    }


def _open_details(page: Page, card) -> Dict:
    details = {
        "telefone": None,
        "site": None,
        "bairro": None,
        "comentarios": [],
        "dono_responde": False,
    }
    card.click()
    page.wait_for_timeout(1200)
    # nome em detalhe
    try:
        page.wait_for_selector("h1.DUwDvf", timeout=5000)
    except Exception:
        return details
    # telefone
    tel_btn = page.query_selector("button[aria-label^='Telefone'], button[aria-label^='Call']")
    if tel_btn:
        details["telefone"] = tel_btn.get_attribute("aria-label").split(":")[-1].strip()
    # site
    site_link = page.query_selector("a[data-item-id='authority']") or page.query_selector(
        "a[aria-label^='Site'], a[aria-label^='Website']"
    )
    if site_link:
        details["site"] = site_link.get_attribute("href")
    # bairro/endereço
    addr_el = page.query_selector("button[data-item-id='address']")
    if addr_el:
        details["bairro"] = addr_el.inner_text().strip()
    # abrir reviews
    reviews_tab = page.query_selector("button[jsaction*='pane.reviewSummary']")
    if reviews_tab:
        reviews_tab.click()
        page.wait_for_timeout(1200)
        _extract_reviews_from_modal(page, details)
    return details


def _extract_reviews_from_modal(page: Page, details: Dict):
    try:
        page.wait_for_selector("div[jstcache][aria-label*='avaliação'], div[aria-label*='review']", timeout=4000)
    except Exception:
        return
    cards = page.query_selector_all("div[jstcache][aria-label*='avaliação'], div[aria-label*='review']")
    for card in cards[:10]:
        texto_el = card.query_selector("span.wiI7pd") or card.query_selector("div.MyEned")
        texto = texto_el.inner_text().strip() if texto_el else ""
        stars_el = card.query_selector("span[aria-label*='estrelas'], span[aria-label*='stars']")
        estrelas = _parse_rating_text(stars_el.get_attribute("aria-label") if stars_el else None)
        owner_reply = card.query_selector("div.dodTBe") or card.query_selector("div.h3YV2d")
        if owner_reply:
            details["dono_responde"] = True
        details["comentarios"].append({"texto": texto, "estrelas": estrelas})


def scrape_google_maps(busca: str) -> List[Dict]:
    url = f"https://www.google.com/maps/search/{busca.replace(' ', '+')}"
    resultados: List[Dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=settings.USER_AGENT, viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded")
        time.sleep(2)
        _scroll_results(page)
        cards = page.query_selector_all("div[role='article']")
        for card in cards:
            base = _extract_card_basic(card)
            if not base.get("nome"):
                continue
            details = _open_details(page, card)
            payload = {
                "nome": base["nome"],
                "categoria": base.get("categoria"),
                "cidade": None,
                "bairro": details.get("bairro"),
                "telefone": details.get("telefone"),
                "site": details.get("site"),
                "nota_media": base.get("nota_media"),
                "total_avaliacoes": base.get("total_avaliacoes"),
                "link_origem": url,
                "fonte": "google_maps",
                "dono_responde": 1 if details.get("dono_responde") else 0,
                "comentarios": details.get("comentarios", []),
            }
            resultados.append(payload)
            # pequeno atraso para reduzir bloqueio
            time.sleep(random.uniform(settings.DELAY_MIN_SEGUNDOS, settings.DELAY_MAX_SEGUNDOS))
        browser.close()
    return resultados


if __name__ == "__main__":
    dados = scrape_google_maps("restaurantes Franca SP")
    print(f"Coletados {len(dados)} resultados")
