# Bot de Inteligencia Comercial por Avaliacoes

Pipeline local para coletar, qualificar e operar leads de estabelecimentos com base em avaliacoes publicas. O projeto agora cobre coleta, score, dashboard principal com duas abas e disparo WhatsApp via Evolution API v3.

## O que o projeto faz
- Coleta estabelecimentos do Google Maps e do Apontador.
- Importa listas manuais via CSV.
- Normaliza dados, calcula score de oportunidade e classifica prioridade.
- Salva tudo em `SQLite` local (`database.db`).
- Exibe a base em um dashboard Astro/React servido pelo Flask.
- Permite aprovar leads para disparo em lote.
- Mantem fila de disparos WhatsApp com status, tentativas e erros.
- Opera envios via Evolution API respeitando janela util, limite diario e intervalo entre mensagens.

## Requisitos
- Python 3.10 ou superior
- `pip` funcionando
- Chromium do Playwright instalado
- Node.js 18 ou superior

Observacoes:
- O build do frontend principal e obrigatorio para a dashboard abrir.
- Para scraping e envio WhatsApp, o computador precisa ter acesso a internet.

## 1. Instalar dependencias Python
```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m playwright install chromium
```

Dependencias principais:
- `playwright`
- `beautifulsoup4`
- `requests`
- `openpyxl`
- `flask`
- `apscheduler`
- `lxml`
- `python-dotenv`

## 2. Build do frontend principal
```bash
cd frontend
npm install
npm run build
cd ..
```

Isso gera a aplicacao em `frontend/dist`, que passa a ser obrigatoria para o Flask servir a dashboard.

## 3. Rodar a dashboard
```bash
python main.py --dashboard
```

URL padrao:
- `http://127.0.0.1:5000`

## 4. Rodar coletas pelo terminal

### Google Maps
```bash
python main.py --fonte google_maps --busca "restaurantes Franca SP"
```

### Apontador
```bash
python main.py --fonte apontador --cidade Franca --estado SP --categoria bares-e-restaurantes/restaurantes
```

### CSV manual
```bash
python main.py --fonte csv --arquivo lista.csv
```

## 5. Operacao da dashboard

### Aba `Estabelecimentos`
- Visualiza todos os registros coletados.
- Filtra por classificacao, prioridade, fonte, cidade, categoria, score, aprovacao e status WhatsApp.
- Seleciona leads visiveis para aprovar ou remover aprovacao em lote.
- Exporta a base filtrada em CSV ou XLSX.
- Dispara novas varreduras pelo card `Procurar estabelecimentos`.

### Aba `Mensagens`
- Mostra status do scheduler.
- Permite alternar entre `Curadoria manual` e `Automacao apos busca`.
- Permite buscar, selecionar, aprovar e adicionar estabelecimentos a fila sem sair da aba.
- Exibe enviados hoje, pendentes de fila e proximo envio.
- Permite iniciar e pausar disparo.
- Lista fila de disparos com origem, telefone, mensagem, agendamento, envio, tentativas e erro.

## 6. Configurar Evolution API
Arquivo principal: `config/settings.py`

Campos relevantes:
- `EVOLUTION_BASE_URL`
- `EVOLUTION_API_KEY`
- `EVOLUTION_INSTANCE`
- `INTERVALO_ENTRE_ENVIOS`
- `LIMITE_DIARIO_ENVIOS`
- `JANELA_INICIO_HORA`
- `JANELA_FIM_HORA`
- `MAX_TENTATIVAS`

Esses valores tambem podem ser sobrescritos por variaveis de ambiente com o mesmo nome.

## 7. Regras de disparo
- So envia em dias uteis.
- So envia dentro da janela configurada.
- Respeita o intervalo entre envios configurado.
- Respeita o limite diario.
- Marca `sem_whatsapp` quando o numero nao existe no WhatsApp.
- Marca `erro` quando atinge o maximo de tentativas.

## 8. Testes
```bash
pytest -q tests
```

Se o `pytest` nao estiver disponivel:
```bash
python -m pytest -q tests
```

## 9. Guias de uso
- `docs/MANUAL-COMPLETO-SISTEMA.md`: manual completo de operacao, Evolution, chamadas HTTP e troubleshooting.
- `docs/USAGE-WHATSAPP.md`: guia curto focado no fluxo da aba `Mensagens`.

## 10. Estrutura rapida
```text
scraper/        scrapers Playwright e importador CSV
processor/      normalizacao, NLP simples e score
database/       schema SQLite, camada CRUD e fila de disparos
whatsapp/       message_builder, validator, sender e scheduler
output/         exportadores CSV e XLSX
frontend/       dashboard Astro/React principal
config/         configuracoes centrais
main.py         entrada principal por CLI
dashboard.py    servidor Flask e API
database.db     banco SQLite local
```
