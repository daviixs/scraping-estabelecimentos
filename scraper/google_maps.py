import random
import re
import time
from typing import Callable, Dict, List, Optional

from playwright.sync_api import Page, sync_playwright

from config import settings


UF_BRASIL = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}
CITY_CONNECTORS = {"da", "das", "de", "do", "dos", "e"}
ProgressCallback = Callable[..., None]
SkipCallback = Callable[[Dict], bool]


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


def _notify(progress_cb: Optional[ProgressCallback], **kwargs) -> None:
    if progress_cb:
        progress_cb(**kwargs)


def _result_key(payload: Dict) -> tuple[str, str]:
    return (
        (payload.get("nome") or "").strip().casefold(),
        (payload.get("cidade") or "").strip().casefold(),
    )


def _extract_city_from_address(address: Optional[str]) -> Optional[str]:
    if not address:
        return None
    normalized = re.sub(r"\s+", " ", address).strip()
    parts = [part.strip() for part in normalized.split(",") if part.strip()]
    for part in reversed(parts):
        match = re.match(r"^([A-Za-zÀ-ÿ' ]+?)\s*-\s*([A-Z]{2})$", part)
        if match:
            city = match.group(1).strip(" -")
            return city or None
    match = re.search(r"([A-Za-zÀ-ÿ' ]+?)\s*-\s*([A-Z]{2})(?:\s*,\s*\d{5}-?\d{3})?$", normalized)
    if match:
        city = match.group(1).strip(" -")
        return city or None
    return None


def _extract_city_from_busca(busca: str) -> Optional[str]:
    tokens = re.findall(r"[A-Za-zÀ-ÿ']+", busca or "")
    if len(tokens) < 2 or tokens[-1].upper() not in UF_BRASIL:
        return None

    city_tokens = []
    has_named_token = False
    for token in reversed(tokens[:-1]):
        token_lower = token.lower()
        if token[:1].isupper():
            has_named_token = True
            city_tokens.append(token)
            continue
        if city_tokens and token_lower in CITY_CONNECTORS:
            city_tokens.append(token)
            continue
        break

    if not city_tokens or not has_named_token:
        return None
    return " ".join(reversed(city_tokens))


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
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)
    except Exception:
        pass
    try:
        card.scroll_into_view_if_needed()
    except Exception:
        pass
    card.click()
    page.wait_for_timeout(1200)
    try:
        page.wait_for_selector("h1.DUwDvf", timeout=5000)
    except Exception:
        return details

    tel_btn = page.query_selector("button[aria-label^='Telefone'], button[aria-label^='Call']")
    if tel_btn:
        details["telefone"] = tel_btn.get_attribute("aria-label").split(":")[-1].strip()

    site_link = page.query_selector("a[data-item-id='authority']") or page.query_selector(
        "a[aria-label^='Site'], a[aria-label^='Website']"
    )
    if site_link:
        details["site"] = site_link.get_attribute("href")

    addr_el = page.query_selector("button[data-item-id='address']")
    if addr_el:
        details["bairro"] = addr_el.inner_text().strip()

    reviews_tab = page.query_selector("button[jsaction*='pane.reviewSummary']")
    if reviews_tab:
        reviews_tab.click()
        page.wait_for_timeout(1200)
        _extract_reviews_from_modal(page, details)
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(250)
        except Exception:
            pass
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


def scrape_google_maps(
    busca: str,
    *,
    target_count: Optional[int] = None,
    should_skip: Optional[SkipCallback] = None,
    progress_cb: Optional[ProgressCallback] = None,
) -> List[Dict]:
    url = f"https://www.google.com/maps/search/{busca.replace(' ', '+')}"
    resultados: List[Dict] = []
    vistos: set[tuple[str, str]] = set()
    cidade_busca = _extract_city_from_busca(busca)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=settings.USER_AGENT, viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded")
        time.sleep(2)

        cards_processados = 0
        pagina_atual = 1
        idle_scrolls = 0

        while True:
            cards = page.query_selector_all("div[role='article']")
            if cards_processados < len(cards):
                _notify(
                    progress_cb,
                    paginas_percorridas=pagina_atual,
                    mensagem=f"Google Maps: explorando resultados ({len(resultados)} novos encontrados).",
                )

            while cards_processados < len(cards):
                if cards_processados >= settings.GOOGLE_MAX_ITENS_INSPECIONADOS:
                    idle_scrolls = settings.GOOGLE_MAX_IDLE_SCROLLS
                    break

                card = cards[cards_processados]
                cards_processados += 1
                _notify(progress_cb, registros_inspecionados=1)

                base = _extract_card_basic(card)
                if not base.get("nome"):
                    continue

                details = _open_details(page, card)
                payload = {
                    "nome": base["nome"],
                    "categoria": base.get("categoria"),
                    "cidade": _extract_city_from_address(details.get("bairro")) or cidade_busca,
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
                key = _result_key(payload)
                if key in vistos:
                    continue
                if should_skip and should_skip(payload):
                    _notify(
                        progress_cb,
                        ignorados_existentes=1,
                        mensagem=f"Google Maps: ignorando {payload['nome']} porque ja existe.",
                    )
                    continue

                vistos.add(key)
                resultados.append(payload)
                _notify(
                    progress_cb,
                    novos_encontrados=len(resultados),
                    mensagem=f"Google Maps: {len(resultados)} novos estabelecimentos encontrados.",
                )
                if target_count and len(resultados) >= target_count:
                    browser.close()
                    return resultados

                time.sleep(random.uniform(settings.DELAY_MIN_SEGUNDOS, settings.DELAY_MAX_SEGUNDOS))

            if target_count and len(resultados) >= target_count:
                break

            total_antes = len(cards)
            page.mouse.wheel(0, 20000)
            time.sleep(1.2)
            total_depois = len(page.query_selector_all("div[role='article']"))
            if total_depois <= total_antes:
                idle_scrolls += 1
            else:
                idle_scrolls = 0
                pagina_atual += 1

            if idle_scrolls >= settings.GOOGLE_MAX_IDLE_SCROLLS:
                break

        browser.close()
    return resultados


if __name__ == "__main__":
    dados = scrape_google_maps("restaurantes Franca SP", target_count=30)
    print(f"Coletados {len(dados)} resultados")
