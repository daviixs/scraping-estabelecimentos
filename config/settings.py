"""
Configuracoes centrais do Bot de Inteligencia Comercial.
"""

import os


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


# Banco de dados
DATABASE_PATH = _env("DATABASE_PATH", "database.db")

# Dashboard
DASHBOARD_HOST = _env("DASHBOARD_HOST", "127.0.0.1")
DASHBOARD_PORT = _env_int("DASHBOARD_PORT", 5000)
REGISTROS_POR_PAGINA = _env_int("REGISTROS_POR_PAGINA", 20)
VARREDURA_MINIMA_ESTABELECIMENTOS = _env_int("VARREDURA_MINIMA_ESTABELECIMENTOS", 30)

# Score - pesos ajustaveis
PESO_NOTA_INVERTIDA = _env_float("PESO_NOTA_INVERTIDA", 0.30)
PESO_VOLUME_REVIEWS = _env_float("PESO_VOLUME_REVIEWS", 0.20)
PESO_QUEIXAS = _env_float("PESO_QUEIXAS", 0.25)
PESO_QUEDA_REPUTACAO = _env_float("PESO_QUEDA_REPUTACAO", 0.15)
PESO_SEM_REPLY = _env_float("PESO_SEM_REPLY", 0.10)

# Volume de normalizacao
VOLUME_MAXIMO_NORM = _env_int("VOLUME_MAXIMO_NORM", 500)

# Queda de reputacao
DELTA_QUEDA_MINIMO = _env_float("DELTA_QUEDA_MINIMO", 0.2)

# Scraping
DELAY_MIN_SEGUNDOS = _env_int("DELAY_MIN_SEGUNDOS", 3)
DELAY_MAX_SEGUNDOS = _env_int("DELAY_MAX_SEGUNDOS", 6)
GOOGLE_MAX_IDLE_SCROLLS = _env_int("GOOGLE_MAX_IDLE_SCROLLS", 4)
GOOGLE_MAX_ITENS_INSPECIONADOS = _env_int("GOOGLE_MAX_ITENS_INSPECIONADOS", 180)
APONTADOR_MAX_PAGINAS = _env_int("APONTADOR_MAX_PAGINAS", 25)
USER_AGENT = _env(
    "USER_AGENT",
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
)

# Apontador
APONTADOR_BASE_URL = _env(
    "APONTADOR_BASE_URL",
    "https://www.apontador.com.br/em/{cidade}-{estado}/{categoria}/",
)
APONTADOR_BUSCA_URL = _env(
    "APONTADOR_BUSCA_URL",
    "https://www.apontador.com.br/local/search.html?q=&loc={cidade}+{estado}&city={cidade}",
)

# Classificacao por nota
FAIXA_MUITO_BOM = _env_float("FAIXA_MUITO_BOM", 4.8)
FAIXA_MEDIO = _env_float("FAIXA_MEDIO", 4.5)

# Prioridade de lead por score
SCORE_PRIORIDADE_ALTA = _env_int("SCORE_PRIORIDADE_ALTA", 60)
SCORE_PRIORIDADE_MEDIA = _env_int("SCORE_PRIORIDADE_MEDIA", 35)

# Evolution API v3
EVOLUTION_BASE_URL = _env("EVOLUTION_BASE_URL", "http://localhost:8080")
EVOLUTION_API_KEY = _env("EVOLUTION_API_KEY", "sua-api-key-aqui")
EVOLUTION_INSTANCE = _env("EVOLUTION_INSTANCE", "nome-da-instancia")
EVOLUTION_REQUEST_TIMEOUT = _env_int("EVOLUTION_REQUEST_TIMEOUT", 15)

# Disparo WhatsApp
INTERVALO_ENTRE_ENVIOS = _env_int("INTERVALO_ENTRE_ENVIOS", 1800)
LIMITE_DIARIO_ENVIOS = _env_int("LIMITE_DIARIO_ENVIOS", 30)
JANELA_INICIO_HORA = _env_int("JANELA_INICIO_HORA", 9)
JANELA_FIM_HORA = _env_int("JANELA_FIM_HORA", 18)
MAX_TENTATIVAS = _env_int("MAX_TENTATIVAS", 2)
WHATSAPP_HEARTBEAT_SEGUNDOS = _env_int("WHATSAPP_HEARTBEAT_SEGUNDOS", 15)
