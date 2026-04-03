import random
import re
import time
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

from playwright.sync_api import sync_playwright

from config import settings


ProgressCallback = Callable[..., None]
SkipCallback = Callable[[Dict], bool]


def _parse_rating(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    match = re.search(r"([0-5](?:[.,]\d)?)", text.replace(",", "."))
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def _parse_count(text: Optional[str]) -> int:
    if not text:
        return 0
    text = text.replace(".", "").replace(",", "")
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else 0


def _notify(progress_cb: Optional[ProgressCallback], **kwargs) -> None:
    if progress_cb:
        progress_cb(**kwargs)


def _scrape_detalhe(context, url: str) -> Dict:
    page = context.new_page()
    detalhe = {"telefone": None, "site": None, "comentarios": [], "dono_responde": False}
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(1200)
        tel_el = page.query_selector("a[href^='tel:'], .phone, .tel")
        if tel_el:
            detalhe["telefone"] = tel_el.inner_text().strip()
        site_el = page.query_selector("a[href^='http'][rel='nofollow'], a.site")
        if site_el:
            detalhe["site"] = site_el.get_attribute("href")

        review_cards = page.query_selector_all(".review, .comment, li[itemprop='review']")
        for card in review_cards[:10]:
            texto_el = card.query_selector("[itemprop='description'], p, .text")
            texto = texto_el.inner_text().strip() if texto_el else ""
            estrelas_el = card.query_selector("[itemprop='ratingValue'], .rating-value")
            estrelas = _parse_rating(estrelas_el.inner_text() if estrelas_el else None)
            owner_el = card.query_selector(".owner-reply, .reply, .resp-empresa")
            if owner_el:
                detalhe["dono_responde"] = True
            detalhe["comentarios"].append({"texto": texto, "estrelas": estrelas})
    finally:
        page.close()
    return detalhe


def scrape_apontador(
    cidade: str,
    estado: str,
    categoria: str,
    *,
    target_count: Optional[int] = None,
    should_skip: Optional[SkipCallback] = None,
    progress_cb: Optional[ProgressCallback] = None,
) -> List[Dict]:
    base_url = settings.APONTADOR_BASE_URL.format(cidade=cidade.lower(), estado=estado.lower(), categoria=categoria)
    resultados: List[Dict] = []
    vistos: set[tuple[str, str]] = set()
    data_coleta = datetime.now(timezone.utc).isoformat()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=settings.USER_AGENT, viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page_num = 1
        while page_num <= settings.APONTADOR_MAX_PAGINAS:
            url = f"{base_url}?page={page_num}"
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(1500)
            cards = page.query_selector_all(".place-card, .place-item, [data-place-id]")
            if not cards:
                break

            _notify(
                progress_cb,
                paginas_percorridas=page_num,
                mensagem=f"Apontador: analisando pagina {page_num} ({len(resultados)} novos encontrados).",
            )

            for card in cards:
                nome_el = card.query_selector("h2.place-name, .card-title, .name")
                nome = nome_el.inner_text().strip() if nome_el else None
                if not nome:
                    continue

                _notify(progress_cb, registros_inspecionados=1)
                key = ((nome or "").strip().casefold(), (cidade or "").strip().casefold())
                if key in vistos:
                    continue
                if should_skip and should_skip({"nome": nome, "cidade": cidade}):
                    _notify(
                        progress_cb,
                        ignorados_existentes=1,
                        mensagem=f"Apontador: ignorando {nome} porque ja existe.",
                    )
                    continue

                categoria_el = card.query_selector(".breadcrumb, .tag, .category")
                cat_val = categoria_el.inner_text().strip() if categoria_el else categoria
                endereco_el = card.query_selector(".address, .place-address, .bairro")
                bairro = endereco_el.inner_text().strip() if endereco_el else None
                nota_el = card.query_selector(".rating-value, .stars-value, [itemprop='ratingValue']")
                nota_media = _parse_rating(nota_el.inner_text() if nota_el else None)
                reviews_el = card.query_selector(".rating-count, .reviews-count")
                total_avaliacoes = _parse_count(reviews_el.inner_text() if reviews_el else None)
                link_el = card.query_selector("a[href*='/local/'], a[href*='/places/'], a")
                link = link_el.get_attribute("href") if link_el else url

                try:
                    detalhe = _scrape_detalhe(context, link)
                except Exception:
                    detalhe = {"telefone": None, "site": None, "comentarios": [], "dono_responde": False}

                resultados.append(
                    {
                        "nome": nome,
                        "categoria": cat_val,
                        "cidade": cidade,
                        "bairro": bairro,
                        "telefone": detalhe.get("telefone"),
                        "site": detalhe.get("site"),
                        "nota_media": nota_media,
                        "total_avaliacoes": total_avaliacoes,
                        "link_origem": link,
                        "fonte": "apontador",
                        "data_coleta": data_coleta,
                        "dono_responde": 1 if detalhe.get("dono_responde") else 0,
                        "comentarios": detalhe.get("comentarios", []),
                    }
                )
                vistos.add(key)
                _notify(
                    progress_cb,
                    novos_encontrados=len(resultados),
                    mensagem=f"Apontador: {len(resultados)} novos estabelecimentos encontrados.",
                )
                if target_count and len(resultados) >= target_count:
                    browser.close()
                    return resultados

            page_num += 1
            time.sleep(random.uniform(settings.DELAY_MIN_SEGUNDOS, settings.DELAY_MAX_SEGUNDOS))
        browser.close()
    return resultados


if __name__ == "__main__":
    dados = scrape_apontador("franca", "sp", "bares-e-restaurantes/restaurantes", target_count=30)
    print(f"Coletados {len(dados)} resultados")
