"""
Configurações centrais do Bot de Inteligência Comercial.
"""

# Banco de dados
DATABASE_PATH = "database.db"

# Dashboard
DASHBOARD_HOST = "127.0.0.1"
DASHBOARD_PORT = 5000
REGISTROS_POR_PAGINA = 20

# Score — pesos ajustáveis
PESO_NOTA_INVERTIDA = 0.30
PESO_VOLUME_REVIEWS = 0.20
PESO_QUEIXAS = 0.25
PESO_QUEDA_REPUTACAO = 0.15
PESO_SEM_REPLY = 0.10

# Volume de normalização
VOLUME_MAXIMO_NORM = 500

# Queda de reputação
DELTA_QUEDA_MINIMO = 0.2  # Diferença mínima de nota para contar como queda

# Scraping
DELAY_MIN_SEGUNDOS = 3
DELAY_MAX_SEGUNDOS = 6
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

# Apontador — URL base
APONTADOR_BASE_URL = "https://www.apontador.com.br/em/{cidade}-{estado}/{categoria}/"
APONTADOR_BUSCA_URL = "https://www.apontador.com.br/local/search.html?q=&loc={cidade}+{estado}&city={cidade}"

# Classificação por nota
FAIXA_MUITO_BOM = 4.8
FAIXA_MEDIO = 4.5

# Prioridade de lead por score
SCORE_PRIORIDADE_ALTA = 60
SCORE_PRIORIDADE_MEDIA = 35
