# Manual Completo de Operacao do Sistema

Baseado no estado atual do projeto em 09/04/2026.

Este manual explica como usar o seu sistema de ponta a ponta:

- como preparar o ambiente
- como configurar a Evolution API
- como obter as credenciais certas
- como ligar o seu sistema
- como coletar leads
- como usar a dashboard
- como operar a aba `Mensagens`
- como testar por `curl`
- como diagnosticar problemas

O foco aqui e o seu sistema. A Evolution entra como dependencia externa para validacao e envio de WhatsApp.

## 1. O que o seu sistema faz

O seu sistema tem 6 partes principais:

1. `Coleta`
   Busca estabelecimentos em Google Maps, Apontador ou CSV manual.
2. `Processamento`
   Normaliza dados, calcula score de oportunidade, classifica prioridade e resume queixas.
3. `Banco local`
   Salva tudo em `SQLite` no arquivo `database.db`.
4. `Dashboard`
   Interface principal em Flask + Astro/React.
5. `Fila de mensagens`
   Organiza os disparos de WhatsApp com status, tentativas, horarios e erros.
6. `Evolution API`
   Valida se o numero tem WhatsApp e envia a mensagem.

Resumo do fluxo:

```text
coleta -> processamento -> database.db -> dashboard -> fila -> Evolution API -> WhatsApp
```

## 2. Mapa rapido do sistema

### 2.1 O que cada parte faz

- `main.py`
  Entrada principal. Roda coleta por linha de comando ou sobe a dashboard.
- `dashboard.py`
  Servidor Flask. Entrega o frontend e expoe as APIs internas.
- `database/`
  Schema e operacoes do banco.
- `frontend/`
  Interface principal com as abas `Estabelecimentos` e `Mensagens`.
- `whatsapp/validator.py`
  Valida numero no endpoint da Evolution.
- `whatsapp/sender.py`
  Envia mensagem via Evolution.
- `whatsapp/scheduler.py`
  Controla a fila, janela de envio, intervalo e limite diario.

### 2.2 O que a dashboard faz hoje

#### Aba `Estabelecimentos`

Serve para:

- revisar a base coletada
- filtrar por cidade, categoria, score, prioridade, fonte
- aprovar ou remover aprovacao de leads
- exportar em CSV e XLSX

#### Aba `Mensagens`

Serve para:

- selecionar estabelecimentos para envio
- alternar entre `Curadoria manual` e `Automacao apos busca`
- aprovar leads e adicionar a fila
- iniciar e pausar o scheduler
- acompanhar fila, status, erros e enviados

## 3. Pre-requisitos

Voce precisa de:

- Python 3.10 a 3.13 (`python3.12` recomendado)
- `pip`
- Node.js 18 ou superior
- Playwright com Chromium
- acesso a internet
- Evolution API rodando
- um numero de WhatsApp que sera conectado na Evolution

Observacao:
- `Python 3.14` nao e compativel com `playwright==1.44.0` e `greenlet` usados neste projeto.

## 4. Como instalar e subir o seu sistema

### 4.1 Instalar dependencias Python

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
```

### 4.2 Instalar e buildar o frontend principal

```bash
cd frontend
npm install
npm run build
cd ..
```

Sem esse build, a dashboard nao abre.

### 4.3 Rodar a dashboard

```bash
.venv/bin/python main.py --dashboard
```

Abra no navegador:

```text
http://127.0.0.1:5000
```

## 5. Evolution API: o que voce precisa dela

O seu sistema usa 3 informacoes da Evolution:

- `EVOLUTION_BASE_URL`
- `EVOLUTION_API_KEY`
- `EVOLUTION_INSTANCE`

### 5.1 O que significa cada uma

- `EVOLUTION_BASE_URL`
  URL da sua Evolution. Exemplo: `http://localhost:8080`
- `EVOLUTION_API_KEY`
  Chave enviada no header `apikey`
- `EVOLUTION_INSTANCE`
  Nome da instancia do WhatsApp que sera usada para validar numeros e enviar mensagens

### 5.2 Como o seu sistema usa isso na pratica

Hoje o seu codigo:

- valida numero em `POST /chat/whatsappNumbers/{instance}`
- envia mensagem em `POST /message/sendText/{instance}`

As duas chamadas usam o header:

```http
apikey: SUA_CHAVE
```

## 6. Como pegar as credenciais da Evolution

Existem dois cenarios.

### Cenario A. Voce mesmo vai subir a Evolution

Nesse caso, a sua credencial principal nasce quando voce sobe a Evolution.

Segundo a documentacao oficial, em instalacao Docker simples a Evolution usa a variavel `AUTHENTICATION_API_KEY`. Essa e a chave que a API espera no header `apikey`.

Observacao:

- em imagens mais novas da Evolution, subir apenas `atendai/evolution-api` com `AUTHENTICATION_API_KEY` pode falhar com `Database provider invalid`
- quando isso acontecer, use uma stack com Postgres e Redis e configure `DATABASE_PROVIDER` e `DATABASE_CONNECTION_URI`

Exemplo de subida local simples com Docker Compose:

```yaml
services:
  evolution_api:
    image: atendai/evolution-api:v2.1.1
    container_name: evolution_api
    restart: always
    ports:
      - "8080:8080"
    depends_on:
      - evolution_postgres
      - evolution_redis
    environment:
      - AUTHENTICATION_API_KEY=troque-por-uma-chave-forte
      - DATABASE_PROVIDER=postgresql
      - DATABASE_CONNECTION_URI=postgresql://postgres:postgres@evolution_postgres:5432/evolution?schema=public
      - DATABASE_CONNECTION_CLIENT_NAME=evolution_local
      - CACHE_REDIS_ENABLED=true
      - CACHE_REDIS_URI=redis://evolution_redis:6379/6

  evolution_postgres:
    image: postgres:15
    container_name: evolution_postgres
    restart: always
    environment:
      - POSTGRES_DB=evolution
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - evolution_postgres_data:/var/lib/postgresql/data

  evolution_redis:
    image: redis:7-alpine
    container_name: evolution_redis
    restart: always
    command: redis-server --appendonly yes
    volumes:
      - evolution_redis_data:/data

volumes:
  evolution_postgres_data:
  evolution_redis_data:
```

Depois suba com:

```bash
docker compose up -d
```

Entao, neste cenario:

- `EVOLUTION_BASE_URL` = `http://localhost:8080`
- `EVOLUTION_API_KEY` = o mesmo valor de `AUTHENTICATION_API_KEY`
- `EVOLUTION_INSTANCE` = o nome da instancia que voce vai criar depois

### Cenario B. A Evolution ja existe e foi entregue para voce

Se outra pessoa ou servidor ja hospeda a Evolution, voce precisa pedir 3 dados:

1. URL base da Evolution
2. chave que funciona no header `apikey`
3. nome da instancia conectada ao WhatsApp

Se a pessoa te entregar mais de uma chave:

- prefira a chave que ja funciona nos endpoints administrativos e de envio
- teste com `GET /instance/fetchInstances`
- depois use a mesma em `EVOLUTION_API_KEY`

### 6.1 Observacao importante sobre a chave

Pela documentacao oficial, a resposta de criacao/listagem de instancia pode exibir uma `apikey` da propria instancia. Ao mesmo tempo, a Evolution tambem usa a chave global de autenticacao definida em `AUTHENTICATION_API_KEY`.

No seu sistema atual existe apenas um campo `EVOLUTION_API_KEY`. Entao a regra pratica e:

- use a chave que realmente funciona no header `apikey` para `fetchInstances`, `whatsappNumbers` e `sendText`
- em instalacao local padrao, isso tende a ser a chave global

Isso e uma inferencia baseada no seu codigo e na documentacao oficial. Se houver duvida no seu ambiente, teste manualmente com os `curl` deste manual antes de gravar a configuracao final.

## 7. Como verificar se a Evolution esta viva

### 7.1 Teste mais simples

Abra no navegador:

```text
http://localhost:8080
```

Em instalacoes padrao, a Evolution costuma responder com uma pagina ou JSON de boas-vindas.

### 7.2 Teste real de autenticacao

Use:

```bash
curl --request GET \
  --url "http://localhost:8080/instance/fetchInstances" \
  --header "apikey: SUA_CHAVE"
```

Se funcionar, voce validou ao mesmo tempo:

- a URL base
- a porta
- o header `apikey`
- a conectividade com a Evolution

## 8. Como criar a instancia da Evolution

Pela documentacao oficial, a rota de criacao e:

```text
POST /instance/create
```

Exemplo pratico:

```bash
curl --request POST \
  --url "http://localhost:8080/instance/create" \
  --header "Content-Type: application/json" \
  --header "apikey: SUA_CHAVE" \
  --data "{\"instanceName\":\"bot-comercial\",\"token\":\"\",\"qrcode\":true,\"integration\":\"WHATSAPP-BAILEYS\"}"
```

O mais importante aqui:

- `instanceName`
  nome da sua instancia
- `qrcode: true`
  pede criacao com fluxo de QR
- `integration`
  para uso simples do seu sistema, `WHATSAPP-BAILEYS` e o caminho mais direto

Depois disso, guarde:

- o nome da instancia, por exemplo `bot-comercial`

Esse nome sera o valor de:

```text
EVOLUTION_INSTANCE=bot-comercial
```

## 9. Como conectar a instancia ao WhatsApp

Voce tem duas formas praticas.

### 9.1 Forma mais simples: usar o Manager

A propria Evolution costuma expor uma interface em:

```text
http://localhost:8080/manager
```

No uso manual, essa costuma ser a forma mais simples de:

- ver a instancia
- solicitar QR code
- acompanhar status de conexao

### 9.2 Forma por API

A documentacao oficial mostra:

```text
GET /instance/connect/{instance}
```

Exemplo:

```bash
curl --request GET \
  --url "http://localhost:8080/instance/connect/bot-comercial" \
  --header "apikey: SUA_CHAVE"
```

Em alguns casos a resposta inclui:

- `pairingCode`
- `code`
- `count`

Se quiser tentar pairing code com numero:

```bash
curl --request GET \
  --url "http://localhost:8080/instance/connect/bot-comercial?number=5516999999999" \
  --header "apikey: SUA_CHAVE"
```

## 10. Como confirmar se a instancia esta conectada

Use novamente:

```bash
curl --request GET \
  --url "http://localhost:8080/instance/fetchInstances?instanceName=bot-comercial" \
  --header "apikey: SUA_CHAVE"
```

O que voce quer ver:

- a instancia existe
- o `instanceName` esta certo
- o status esta `open` ou equivalente de conectado

## 11. Como configurar a Evolution no seu sistema

Abra `config/settings.py` e ajuste os campos abaixo, ou defina variaveis de ambiente com os mesmos nomes.

Exemplo:

```python
EVOLUTION_BASE_URL = "http://localhost:8080"
EVOLUTION_API_KEY = "troque-por-sua-chave-real"
EVOLUTION_INSTANCE = "bot-comercial"
EVOLUTION_REQUEST_TIMEOUT = 15

INTERVALO_ENTRE_ENVIOS = 1800
LIMITE_DIARIO_ENVIOS = 30
JANELA_INICIO_HORA = 9
JANELA_FIM_HORA = 18
MAX_TENTATIVAS = 2
```

### 11.1 O que cada parametro de envio faz

- `INTERVALO_ENTRE_ENVIOS`
  intervalo em segundos entre mensagens
- `LIMITE_DIARIO_ENVIOS`
  total maximo por dia
- `JANELA_INICIO_HORA`
  hora inicial permitida
- `JANELA_FIM_HORA`
  hora final permitida
- `MAX_TENTATIVAS`
  numero maximo de tentativas antes de marcar `erro`

## 12. Como usar o seu sistema no dia a dia

## 12.1 Primeiro uso

A ordem correta e:

1. subir a Evolution
2. validar `apikey`
3. criar a instancia
4. conectar o WhatsApp
5. configurar `settings.py`
6. buildar o frontend
7. subir a dashboard
8. coletar leads
9. revisar a base
10. operar a aba `Mensagens`

## 12.2 Como coletar leads

### Google Maps

```bash
.venv/bin/python main.py --fonte google_maps --busca "restaurantes Franca SP"
```

### Apontador

```bash
.venv/bin/python main.py --fonte apontador --cidade Franca --estado SP --categoria bares-e-restaurantes/restaurantes
```

### CSV

```bash
.venv/bin/python main.py --fonte csv --arquivo lista.csv
```

## 12.3 Como usar a aba `Estabelecimentos`

Use essa aba para:

- revisar o que entrou
- filtrar por cidade, categoria, score e fonte
- verificar prioridade
- aprovar ou remover aprovacao em lote
- exportar a base

Quando um lead e aprovado:

- `aprovado_disparo` vira `1`
- isso significa que ele esta liberado para contato
- isso nao significa, sozinho, que ele ja esta em fila

## 12.4 Como usar a aba `Mensagens`

Essa e a aba operacional.

Voce tem dois modos:

- `Curadoria manual`
- `Automacao apos busca`

### Curadoria manual

Use quando voce quer decidir manualmente quem sera contatado.

Fluxo:

1. abra a aba `Mensagens`
2. mantenha `Curadoria manual`
3. use a busca para localizar os leads
4. selecione os cards desejados
5. clique em `Aprovar` se quiser apenas liberar
6. clique em `Adicionar a fila` para aprovar e enfileirar
7. clique em `Iniciar disparo` quando quiser processar a fila

### Automacao apos busca

Use quando voce quer que novos resultados elegiveis ja entrem no fluxo.

Fluxo:

1. abra a aba `Mensagens`
2. altere para `Automacao apos busca`
3. execute novas varreduras
4. os novos leads elegiveis entram em aprovacao e fila automaticamente
5. se o scheduler estiver ativo, ele processa no ritmo configurado
6. se o scheduler estiver pausado, eles ficam aguardando

## 12.5 O que significa cada status

### No estabelecimento

- `pendente`
  ainda nao foi enviado
- `enviado`
  mensagem enviada com sucesso
- `sem_whatsapp`
  o numero nao existe no WhatsApp segundo a validacao
- `erro`
  falhou repetidamente ate atingir o limite

### Na fila

- `pendente`
  aguardando horario de envio
- `enviado`
  concluido
- `sem_whatsapp`
  descartado por validacao
- `erro`
  falha definitiva

### Origem da fila

- `manual`
  voce selecionou e enfileirou pela aba `Mensagens`
- `automatico`
  o item veio da automacao apos busca

## 12.6 Como iniciar e pausar o envio

### Iniciar

Na aba `Mensagens`, clique em `Iniciar disparo`.

O scheduler vai:

1. ler a fila
2. respeitar horario util
3. respeitar limite diario
4. validar numero no WhatsApp
5. enviar a mensagem

### Pausar

Clique em `Pausar disparo`.

Isso:

- nao apaga a fila
- nao apaga aprovacoes
- apenas interrompe o processamento

## 12.7 Como exportar

Pela dashboard voce pode exportar a base filtrada em:

- CSV
- XLSX

## 13. Chamadas HTTP da Evolution que o seu sistema usa

## 13.1 Validar numero no WhatsApp

O seu sistema usa:

```text
POST /chat/whatsappNumbers/{instance}
```

Exemplo:

```bash
curl --request POST \
  --url "http://localhost:8080/chat/whatsappNumbers/bot-comercial" \
  --header "Content-Type: application/json" \
  --header "apikey: SUA_CHAVE" \
  --data "{\"numbers\":[\"5516999990000\"]}"
```

No seu codigo, essa chamada e usada para descobrir se o numero existe no WhatsApp antes do envio.

O comportamento esperado no seu sistema:

- se existir, segue para envio
- se nao existir, marca `sem_whatsapp`

## 13.2 Enviar texto

O seu sistema usa:

```text
POST /message/sendText/{instance}
```

Exemplo:

```bash
curl --request POST \
  --url "http://localhost:8080/message/sendText/bot-comercial" \
  --header "Content-Type: application/json" \
  --header "apikey: SUA_CHAVE" \
  --data "{\"number\":\"5516999990000\",\"text\":\"Ola! Esta e uma mensagem de teste.\"}"
```

No seu sistema, essa chamada so acontece depois da validacao.

## 14. Chamadas HTTP internas do seu sistema

Base local padrao:

```text
http://127.0.0.1:5000
```

## 14.1 Consultar estabelecimentos

```bash
curl "http://127.0.0.1:5000/api/estabelecimentos"
```

Com filtros:

```bash
curl "http://127.0.0.1:5000/api/estabelecimentos?cidade=Franca&score_min=60&aprovado_disparo=approved"
```

## 14.2 Resumo geral

```bash
curl "http://127.0.0.1:5000/api/resumo"
```

Retorna KPIs como:

- total
- aprovados
- enviados hoje
- aguardando envio

## 14.3 Aprovar leads

```bash
curl --request POST \
  --url "http://127.0.0.1:5000/api/aprovar" \
  --header "Content-Type: application/json" \
  --data "{\"ids\":[1,2,3]}"
```

## 14.4 Remover aprovacao

```bash
curl --request POST \
  --url "http://127.0.0.1:5000/api/remover-aprovacao" \
  --header "Content-Type: application/json" \
  --data "{\"ids\":[1,2,3]}"
```

## 14.5 Buscar candidatos da aba `Mensagens`

```bash
curl "http://127.0.0.1:5000/api/mensagens/elegiveis?q=restaurante&limit=20"
```

## 14.6 Ler o modo atual da aba `Mensagens`

```bash
curl "http://127.0.0.1:5000/api/mensagens/config"
```

## 14.7 Trocar o modo entre manual e automatico

```bash
curl --request POST \
  --url "http://127.0.0.1:5000/api/mensagens/config" \
  --header "Content-Type: application/json" \
  --data "{\"modo_envio\":\"automatico\"}"
```

Para voltar:

```bash
curl --request POST \
  --url "http://127.0.0.1:5000/api/mensagens/config" \
  --header "Content-Type: application/json" \
  --data "{\"modo_envio\":\"manual\"}"
```

## 14.8 Adicionar selecionados a fila

```bash
curl --request POST \
  --url "http://127.0.0.1:5000/api/disparo/enfileirar" \
  --header "Content-Type: application/json" \
  --data "{\"ids\":[5,6,7]}"
```

## 14.9 Ver a fila

```bash
curl "http://127.0.0.1:5000/api/fila-disparos"
```

## 14.10 Ver status do scheduler

```bash
curl "http://127.0.0.1:5000/api/disparo/status"
```

## 14.11 Iniciar o scheduler

```bash
curl --request POST \
  --url "http://127.0.0.1:5000/api/disparo/iniciar"
```

## 14.12 Pausar o scheduler

```bash
curl --request POST \
  --url "http://127.0.0.1:5000/api/disparo/pausar"
```

## 14.13 Iniciar uma varredura pela API

Google Maps:

```bash
curl --request POST \
  --url "http://127.0.0.1:5000/api/varreduras" \
  --header "Content-Type: application/json" \
  --data "{\"source\":\"google_maps\",\"command\":\"restaurantes Franca SP\"}"
```

## 14.14 Acompanhar varredura

Ultima ou ativa:

```bash
curl "http://127.0.0.1:5000/api/varreduras/ativa"
```

Por ID:

```bash
curl "http://127.0.0.1:5000/api/varreduras/SEU_JOB_ID"
```

## 14.15 Exportar

```bash
curl -OJ "http://127.0.0.1:5000/api/export/csv"
curl -OJ "http://127.0.0.1:5000/api/export/xlsx"
```

## 15. Como testar tudo de ponta a ponta

Use esta sequencia:

1. subir a Evolution
2. validar `fetchInstances`
3. criar a instancia
4. conectar o WhatsApp
5. configurar `settings.py`
6. subir a dashboard
7. rodar uma coleta
8. confirmar que os leads apareceram
9. abrir a aba `Mensagens`
10. selecionar 1 lead
11. adicionar a fila
12. iniciar o scheduler
13. acompanhar `fila-disparos`
14. confirmar `enviado` ou `sem_whatsapp`

## 16. Troubleshooting

## 16.1 A dashboard nao abre

Causas comuns:

- frontend sem build
- porta ocupada

Como corrigir:

```bash
cd frontend
npm install
npm run build
cd ..
.venv/bin/python main.py --dashboard
```

## 16.2 A Evolution nao responde

Teste:

```bash
curl "http://localhost:8080"
```

Se nao responder:

- a Evolution nao subiu
- a porta esta errada
- a URL base esta errada

## 16.3 `apikey` invalida

Teste:

```bash
curl --request GET \
  --url "http://localhost:8080/instance/fetchInstances" \
  --header "apikey: SUA_CHAVE"
```

Se falhar:

- a chave esta errada
- voce esta usando a chave errada do ambiente
- a Evolution foi configurada com outro valor de `AUTHENTICATION_API_KEY`

## 16.4 A instancia nao conecta

Verifique:

- se o nome da instancia esta correto
- se o WhatsApp foi realmente pareado
- se `fetchInstances` mostra status conectado
- se o numero usado no pairing esta em formato internacional

## 16.5 O seu sistema nao envia

Verifique:

- `EVOLUTION_BASE_URL`
- `EVOLUTION_API_KEY`
- `EVOLUTION_INSTANCE`
- status da instancia
- se o scheduler esta `Ativo`
- se esta dentro da janela util
- se o limite diario nao foi atingido

## 16.6 O lead cai em `sem_whatsapp`

Significa que a validacao em `/chat/whatsappNumbers/{instance}` nao confirmou o numero.

Causas comuns:

- telefone incorreto
- telefone sem DDI
- numero inexistente no WhatsApp

## 16.7 O lead cai em `erro`

Significa que o envio falhou repetidamente ate atingir `MAX_TENTATIVAS`.

Causas comuns:

- instancia desconectada
- problema de autenticacao
- Evolution indisponivel
- payload rejeitado

## 16.8 A fila nao anda

Verifique:

- se o scheduler esta iniciado
- se o horario atual esta dentro da janela
- se existem itens `pendente`
- se o limite diario nao foi atingido
- se a instancia esta conectada

## 17. Checklist final

Use esta lista para confirmar que tudo esta pronto:

- Evolution responde em `http://localhost:8080`
- `fetchInstances` responde com sua `apikey`
- a instancia existe
- a instancia esta conectada ao WhatsApp
- `settings.py` aponta para a Evolution certa
- a dashboard abre em `http://127.0.0.1:5000`
- a coleta insere leads
- a aba `Estabelecimentos` mostra os registros
- a aba `Mensagens` mostra candidatos e fila
- voce consegue aprovar e enfileirar
- o scheduler inicia
- o envio de teste funciona

## 18. Limites atuais do seu sistema

Hoje o seu sistema:

- envia mensagens
- valida numeros
- controla fila
- pausa e retoma scheduler

Hoje ele ainda nao:

- marca resposta recebida automaticamente
- processa inbound da Evolution
- atualiza `respondeu` por webhook

## 19. Referencias oficiais da Evolution

Conferidas em 09/04/2026:

- Portal principal:
  https://doc.evolution-api.com
- Instalacao com Docker:
  https://doc.evolution-api.com/v2/en/install/docker
- Variaveis de ambiente:
  https://doc.evolution-api.com/v1/en/env
- Criar instancia:
  https://doc.evolution-api.com/v1/api-reference/instance-controller/create-instance-basic
- Conectar instancia:
  https://doc.evolution-api.com/v2/api-reference/instance-controller/instance-connect
- Listar instancias:
  https://doc.evolution-api.com/v2/api-reference/instance-controller/fetch-instances
- Validar numero no WhatsApp:
  https://doc.evolution-api.com/v2/api-reference/chat-controller/check-is-whatsapp
- Enviar texto:
  https://doc.evolution-api.com/v2/api-reference/message-controller/send-text
