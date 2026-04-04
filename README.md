# Bot de Inteligencia Comercial por Avaliacoes

Pipeline local para coletar, analisar e priorizar leads de estabelecimentos com base em avaliacoes publicas, com suporte a Google Maps, Apontador, importacao por CSV e dashboard web.

## O que este projeto faz
- Coleta estabelecimentos do Google Maps e do Apontador.
- Importa listas manuais via CSV.
- Normaliza os dados, calcula score de oportunidade e classifica a prioridade do lead.
- Salva tudo em SQLite local (`database.db`).
- Exibe e exporta os resultados pela dashboard web.
- Ignora estabelecimentos ja existentes nas novas varreduras.
- Nas varreduras da dashboard, tenta encontrar no minimo 30 estabelecimentos novos antes de encerrar, quando a fonte permitir.

## Requisitos
Voce consegue rodar o projeto em Windows, Linux ou macOS. O minimo necessario e:

- Python 3.10 ou superior
- `pip` funcionando
- Chromium do Playwright instalado
- Node.js 18 ou superior para build do frontend moderno (opcional em runtime)

Observacoes:
- Se voce nao gerar o frontend em `frontend/dist`, a aplicacao ainda funciona usando o fallback em `templates/index.html`.
- Para scraping, o computador precisa ter acesso a internet.

## 1. Baixar o projeto
Clone o repositorio ou copie a pasta para a maquina onde voce quer rodar.

Exemplo com Git:

```bash
git clone <url-do-repositorio>
cd scraping-de-numeros
```

Se voce recebeu o projeto em `.zip`, basta extrair e entrar na pasta raiz.

## 2. Criar e ativar um ambiente virtual Python
Este passo e recomendado em qualquer PC.

### Windows PowerShell
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Windows CMD
```bat
py -m venv .venv
.venv\Scripts\activate.bat
```

### Linux / macOS
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Se preferir, voce pode usar `python` no lugar de `py` no Windows, desde que o comando exista na sua maquina.

## 3. Instalar as dependencias Python
Com o ambiente virtual ativo, rode:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m playwright install chromium
```

Dependencias principais do projeto:
- `playwright`
- `beautifulsoup4`
- `requests`
- `openpyxl`
- `flask`
- `lxml`
- `python-dotenv`

Se o comando do Playwright falhar, confirme se o ambiente virtual esta ativo e rode novamente.

## 4. Build opcional do frontend moderno
Se voce quiser a interface Astro/React mais nova da dashboard, faca o build do frontend.

```bash
cd frontend
npm install
npm run build
cd ..
```

Observacoes:
- Isso gera os arquivos estaticos em `frontend/dist`.
- Se voce pular esse passo, a dashboard continua abrindo com o HTML fallback de `templates/index.html`.
- Para desenvolvimento do frontend, os scripts disponiveis sao `npm run dev`, `npm run build` e `npm run preview`.

## 5. Rodar o projeto
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
  python -m playwright install chromium
  python main.py --dashboard
  ```

### 5.1 Abrir apenas a dashboard
```bash
python main.py --dashboard
```

A aplicacao sobe por padrao em:
- URL: `http://127.0.0.1:5000`
- Host: `127.0.0.1`
- Porta: `5000`

Esses valores podem ser alterados em `config/settings.py`.

### 5.2 Rodar uma coleta pelo terminal
#### Google Maps
```bash
python main.py --fonte google_maps --busca "restaurantes Franca SP"
```

#### Apontador
```bash
python main.py --fonte apontador --cidade Franca --estado SP --categoria bares-e-restaurantes/restaurantes
```

#### Importacao por CSV
```bash
python main.py --fonte csv --arquivo lista.csv
```

Saida esperada das varreduras automaticas:
- quantidade de novos inseridos
- quantidade de estabelecimentos ignorados por ja existirem
- paginas percorridas
- status final da varredura

## 6. Como usar a dashboard
Depois de executar `python main.py --dashboard`, abra o navegador no endereco informado.

A dashboard permite:
- visualizar os estabelecimentos ja coletados
- filtrar por cidade, categoria, fonte, classificacao e prioridade
- exportar os resultados em CSV ou XLSX
- iniciar novas varreduras pelo card `Procurar estabelecimentos`

### Comando de varredura na dashboard
No card de varredura, voce escolhe a fonte no seletor e digita o comando no campo de texto.

#### Se a fonte for Google Maps
Digite apenas a busca completa. Exemplo:

```text
restaurantes Franca SP
```

#### Se a fonte for Apontador
Digite no formato `cidade UF categoria`. Exemplo:

```text
Franca SP bares-e-restaurantes/restaurantes
```

Regras atuais da dashboard:
- a fonte e escolhida no seletor da interface
- o texto digitado e interpretado dentro da fonte escolhida
- estabelecimentos ja existentes sao ignorados por completo
- a varredura tenta encontrar pelo menos 30 estabelecimentos novos
- se a busca acabar antes disso, o status final pode ser parcial

## 7. Arquivos importantes gerados em runtime
- `database.db`: banco SQLite criado na raiz do projeto
- `output/export.csv`: exportacao CSV da dashboard
- `output/export.xlsx`: exportacao Excel da dashboard
- `frontend/dist`: build estatico do frontend moderno

## 8. Configuracoes que voce pode ajustar
Arquivo principal: `config/settings.py`

Alguns parametros importantes:
- `DATABASE_PATH`: caminho do banco SQLite
- `DASHBOARD_HOST`: host da dashboard
- `DASHBOARD_PORT`: porta da dashboard
- `REGISTROS_POR_PAGINA`: paginacao da interface
- `VARREDURA_MINIMA_ESTABELECIMENTOS`: meta minima de novos por varredura
- `DELAY_MIN_SEGUNDOS` e `DELAY_MAX_SEGUNDOS`: atrasos do scraping
- `GOOGLE_MAX_IDLE_SCROLLS`: limite defensivo de scroll sem novos resultados
- `GOOGLE_MAX_ITENS_INSPECIONADOS`: limite defensivo do Google Maps
- `APONTADOR_MAX_PAGINAS`: limite de paginas no Apontador

## 9. Rodar testes
Se quiser validar o ambiente depois da instalacao:

```bash
pytest
```

Se o `pytest` nao estiver disponivel, rode:

```bash
python -m pytest
```

## 10. Solucao de problemas comuns
### Playwright nao abre ou reclama de browser ausente
Rode novamente:

```bash
python -m playwright install chromium
```

### A dashboard abre, mas a interface moderna nao aparece
Faca o build do frontend:

```bash
cd frontend
npm install
npm run build
cd ..
```

Se mesmo assim nao aparecer, a aplicacao ainda deve funcionar usando o fallback HTML.

### A porta 5000 ja esta ocupada
Altere `DASHBOARD_PORT` em `config/settings.py` e rode a dashboard de novo.

### A varredura encontra poucos resultados
Isso pode acontecer quando:
- a busca tem poucos estabelecimentos disponiveis
- muitos estabelecimentos ja estao no banco e sao ignorados
- a fonte esgota os resultados antes de atingir a meta minima

### O banco precisa ser movido para outro PC
Basta copiar a pasta do projeto inteira, incluindo `database.db`, se voce quiser levar o historico ja coletado.

## 11. Estrutura rapida do projeto
```text
scraper/        scrapers Playwright e importador CSV
processor/      normalizacao, NLP simples e score
database/       schema SQLite e camada CRUD
output/         exportadores CSV e XLSX
frontend/       codigo-fonte Astro/React da dashboard
templates/      fallback HTML caso `frontend/dist` nao exista
config/         configuracoes da aplicacao
main.py         entrada principal por CLI
dashboard.py    servidor Flask da dashboard
```
