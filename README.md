# Bot de Inteligência Comercial por Avaliações

Pipeline local para coletar, analisar e priorizar leads de estabelecimentos com base em avaliações públicas (Google Maps, Apontador e listas manuais).

## Requisitos
- Python 3.10+
- Playwright (`pip install -r requirements.txt` e `playwright install chromium`)
- Node 18+ (para build do frontend Astro, opcional em runtime)

## Estrutura
```
scraper/        # Playwright scrapers e importador CSV
processor/      # Normalização, NLP simples e cálculo de score
database/       # Schema SQLite e camada CRUD
output/         # Exportadores CSV/XLSX
frontend/       # Fonte Astro (build opcional)
templates/      # HTML estático fallback (serve se dist não existir)
dashboard.py    # Flask API + servidor
main.py         # CLI orquestrador
```

## Uso
```bash
# Apontador
python main.py --fonte apontador --cidade Franca --estado SP --categoria bares-e-restaurantes/restaurantes

# Google Maps
python main.py --fonte google_maps --busca "restaurantes Franca SP"

# Importar CSV manual
python main.py --fonte csv --arquivo lista.csv

# Apenas dashboard
python main.py --dashboard
```

## Dashboard
- Flask em `http://127.0.0.1:5000`
- Rotas: `/api/estabelecimentos`, `/api/resumo`, `/api/cidades`, `/api/categorias`, `/api/export/csv`, `/api/export/xlsx`
- Frontend Astro (Tailwind + shadcn-style + Framer Motion) em `frontend/` (build gera `frontend/dist`); fallback para `templates/index.html` se dist não existir.
- Para o frontend: `cd frontend && npm install && npm run build` (ou `npm run dev` para desenvolvimento).

## Configuração
Edite `config/settings.py` para pesos do score, delays de scraping, host/porta e registros por página.

## Testes
```bash
pytest
```

## Notas
- Score conforme fórmula do prompt: inverso da nota, volume normalizado, queixas, queda de reputação e falta de resposta.
- Duplicidade evitada por `UNIQUE(nome, cidade)` e upsert SQL.
- Exportadores usam csv e openpyxl; não há dependência de pandas.
- Risco de bloqueio em scraping mitigado por user-agent e delays randômicos; Google Maps sem limite de resultados.
