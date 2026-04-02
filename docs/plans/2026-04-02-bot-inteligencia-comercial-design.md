# Bot de Inteligência Comercial — Design v1 (2026-04-02)

## Resumo
- Pipeline síncrono acionado via CLI executa: scraper/importador → normalização → NLP → score → persistência SQLite → exportação → dashboard.
- Fontes: Google Maps (scroll infinito), Apontador (?page=N), CSV manual.
- Dashboard: Flask expõe API; frontend Astro consome e exibe filtros, paginação, KPIs.

## Arquitetura
- `main.py` escolhe a fonte e orquestra etapas, inicializando DB quando ausente.
- Scrapers Playwright (`scraper/google_maps.py`, `scraper/apontador.py`) e importador CSV.
- Processamento: normalização, NLP por dicionário, cálculo de score e prioridade, detecção de queda (history).
- Persistência: SQLite em `database.db` com tabelas estabelecimentos, coletas_historico, comentarios, queixas_categorias; upsert por (nome,cidade).
- Dashboard: Flask (`dashboard.py`) + Astro frontend (build servido como estático). API: `/api/estabelecimentos`, `/api/resumo`, `/api/cidades`, `/api/categorias`, `/api/export/csv`, `/api/export/xlsx`.

## Decisões
- Pipeline síncrono para simplicidade local; sem filas/Redis.
- Google Maps sem limite de resultados; risco de bloqueio mitigado por user-agent e tempo de espera entre scrolls.
- Pesos de score, registros por página, delays e limites em `config/settings.py`.
- Astro build fica em `frontend/dist`; Flask serve arquivos estáticos desse diretório.

## Dados e Regras
- Score conforme fórmula fornecida; prioridade: >=60 alta, 35–59 média, abaixo disso baixa.
- Faixa de nota: ≥4.8 muito bom, 4.5–4.7 médio, <4.5 muito ruim.
- NLP: contagem por palavras-chave; resumo como "categoria (n)" separado por vírgula.
- Histórico: ao reprocessar estabelecimento, registrar snapshot em `coletas_historico` e detectar queda (>=0.2).

## Testes
- `scorer`: bordas de componentes e prioridades.
- `nlp_comments`: contagem e resumo com frases sintéticas.
- `db_manager`: upsert e histórico em DB temporário.
- `dashboard` API: paginação/ordenacão/filtros em fixtures mínimas.

## Riscos e Mitigações
- Bloqueio em scraping: delays randômicos, user-agent Chrome, retries leves.
- Variação de DOM: seletores múltiplos e fallback.
- Performance de exportação: usar consultas filtradas e streaming simples.
