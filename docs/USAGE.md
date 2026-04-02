# Uso do Bot de Inteligência Comercial

## Requisitos
- Python 3.10+ (recomendado 3.11/3.12; evitamos pandas)
- Node 18+ (para build do frontend Astro, opcional em runtime)
- Playwright (Chromium) instalado via `python -m playwright install chromium`

## 1) Instalação (Python)
```bash
py -m pip install -r requirements.txt
python -m playwright install chromium
```

## 2) (Opcional) Build do frontend Astro
Se quiser a UI nova (Tailwind + shadcn + Motion) em vez do HTML fallback:
```bash
cd frontend
npm install
npm run build
cd ..
```

## 3) Rodar coletas
- Apontador:
```bash
python main.py --fonte apontador --cidade Franca --estado SP --categoria bares-e-restaurantes/restaurantes
```
- Google Maps:
```bash
python main.py --fonte google_maps --busca "restaurantes Franca SP"
```
- CSV manual:
```bash
python main.py --fonte csv --arquivo minha_lista.csv
```
Cada execução: normaliza dados, faz NLP de queixas, calcula score, upsert em `database.db` e registra histórico.

## 4) Dashboard
```bash
python main.py --dashboard
```
Acesse http://127.0.0.1:5000.  
Filtros, ordenação, paginação e export (CSV/XLSX) via UI. Se o build Astro existir, ele será servido; caso contrário, usa o fallback `templates/index.html`.

## 5) Configurações
Arquivo: `config/settings.py`
- Pesos do score, limites de volume, delta de queda, registros por página.
- Host/porta da dashboard, user-agent, delays de scraping.

## 6) Estrutura rápida
```
scraper/     # Playwright: google_maps, apontador, csv_importer
processor/   # normalizer, nlp_comments, scorer
database/    # schema.sql, db_manager, history
output/      # csv_exporter, excel_exporter (openpyxl)
frontend/    # Astro + Tailwind/shadcn/motion (dist após build)
templates/   # HTML fallback
main.py      # CLI orquestrador
dashboard.py # Flask API/servidor
database.db  # SQLite (gerado)
```

## 7) Comandos rápidos
- Atualizar deps Python depois de mudanças: `py -m pip install -r requirements.txt`
- Rebuild front após edições: `cd frontend && npm run build`
- Iniciar dashboard: `python main.py --dashboard`
- Recoletar Apontador: `python main.py --fonte apontador --cidade <cidade> --estado <UF> --categoria <slug>`
- Recoletar Google: `python main.py --fonte google_maps --busca "<termo> <cidade> <UF>"`
- Importar CSV: `python main.py --fonte csv --arquivo minha_lista.csv`

## 8) Notas
- Banco: `database.db` na raiz, com constraint UNIQUE (nome, cidade).
- Exportadores usam csv e openpyxl (sem pandas).
- Se faltar Playwright browser: `python -m playwright install chromium`.
