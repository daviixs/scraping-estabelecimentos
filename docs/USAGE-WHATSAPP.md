# Guia de Uso das Novas Alteracoes

Este documento cobre o fluxo novo de aprovacao e envio WhatsApp no projeto.

## 1. O que mudou

O sistema agora tem duas frentes operacionais:

- `Estabelecimentos`: organiza, filtra e aprova a base
- `Mensagens`: seleciona, aprova, enfileira e opera os disparos WhatsApp

No backend, tambem foram adicionados:

- campos `aprovado_disparo` e `status_whatsapp` em `estabelecimentos`
- tabela `fila_disparos`
- tabela `configuracoes_operacionais`
- modulo `whatsapp/` com validacao, envio, geracao de mensagem e scheduler
- novas rotas Flask para aprovacao, fila e controle de disparo

## 2. Preparacao obrigatoria

### 2.1 Dependencias Python
```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
```

### 2.2 Build do frontend principal
```bash
cd frontend
npm install
npm run build
cd ..
```

Sem esse build, a dashboard nao abre.

### 2.3 Configurar Evolution API
Edite `config/settings.py` ou defina variaveis de ambiente:

- `EVOLUTION_BASE_URL`
- `EVOLUTION_API_KEY`
- `EVOLUTION_INSTANCE`

Exemplo local:
```python
EVOLUTION_BASE_URL = "http://localhost:8080"
EVOLUTION_API_KEY = "sua-chave"
EVOLUTION_INSTANCE = "nome-da-instancia"
```

## 3. Como iniciar o sistema

### Rodar a dashboard
```bash
python main.py --dashboard
```

Abra:
```text
http://127.0.0.1:5000
```

## 4. Fluxo completo de uso

### Passo 1. Alimentar a base
Use a dashboard ou a CLI para coletar leads.

Exemplos:
```bash
python main.py --fonte google_maps --busca "restaurantes Franca SP"
python main.py --fonte apontador --cidade Franca --estado SP --categoria bares-e-restaurantes/restaurantes
python main.py --fonte csv --arquivo lista.csv
```

### Passo 2. Revisar na aba `Estabelecimentos`
Na aba principal voce pode:

- filtrar por cidade, categoria, score e fonte
- filtrar por aprovacao
- filtrar por status WhatsApp
- selecionar os cards visiveis
- aprovar ou remover aprovacao em lote

### Passo 3. Operar na aba `Mensagens`
Abra a aba `Mensagens`.

Ela mostra:

- modo `Curadoria manual` ou `Automacao apos busca`
- painel para buscar e selecionar estabelecimentos
- acoes `Aprovar`, `Remover aprovacao` e `Adicionar a fila`
- status do scheduler
- proximo envio
- enviados hoje
- pendentes na fila
- regras operacionais
- lista detalhada da fila

### Passo 4. Escolher o modo de operacao
No topo da aba `Mensagens` existem dois modos:

- `Curadoria manual`: novas varreduras so alimentam a base; voce escolhe quem aprovar e quem entra na fila
- `Automacao apos busca`: novos resultados elegiveis de varredura entram automaticamente em aprovacao e fila

Esse modo fica salvo no banco e continua valendo para as proximas buscas.

### Passo 5. Selecionar e enfileirar manualmente
Na propria aba `Mensagens`:

- use a busca para localizar estabelecimentos
- marque os cards desejados
- clique em `Aprovar` se quiser apenas liberar o contato
- clique em `Adicionar a fila` para aprovar e enfileirar direto

Quando voce adiciona a fila manualmente:

- `aprovado_disparo` vira `1`
- um item e criado em `fila_disparos`
- a origem do item fica registrada como `manual`

### Passo 6. Iniciar o disparo
Clique em `Iniciar disparo`.

O sistema vai:

1. ler a fila ja criada manualmente ou pela automacao
2. gerar mensagem para cada item
3. agendar os envios dentro da janela util
4. validar o numero no WhatsApp antes de enviar
5. disparar via Evolution API

Se o modo `Automacao apos busca` estiver ativo, novos leads de varredura entram na fila com origem `automatico`. Se o scheduler estiver pausado, eles ficam aguardando.

### Passo 7. Pausar quando necessario
Clique em `Pausar disparo` para interromper o scheduler sem perder a fila.

Os itens pendentes continuam no banco e podem ser retomados depois.

## 5. Significado dos status

### `status_whatsapp` no estabelecimento
- `pendente`: ainda nao foi enviado
- `enviado`: mensagem disparada com sucesso
- `sem_whatsapp`: o numero nao existe no WhatsApp
- `erro`: atingiu o maximo de tentativas com falha

### `status` na fila
- `pendente`: item aguardando a hora do envio
- `enviado`: item concluido
- `sem_whatsapp`: validacao reprovou o numero
- `erro`: falha definitiva apos tentativas

## 6. Regras operacionais

O scheduler respeita:

- dias uteis
- horario entre `JANELA_INICIO_HORA` e `JANELA_FIM_HORA`
- `INTERVALO_ENTRE_ENVIOS`
- `LIMITE_DIARIO_ENVIOS`
- `MAX_TENTATIVAS`

Defaults atuais:

- intervalo: 30 minutos
- janela: 09:00-18:00
- limite diario: 30
- tentativas maximas: 2

## 7. Como ler a fila

Cada item da fila exibe:

- nome do estabelecimento
- telefone
- origem do disparo
- status
- tentativas
- data agendada
- data de envio
- mensagem gerada
- erro, quando existir

Uso recomendado:

- `pendente`: deixe o scheduler operar
- `sem_whatsapp`: remova da sua estrategia comercial
- `erro`: revise configuracao, numero ou conectividade
- `enviado`: acompanhe o retorno fora do sistema
- `origem manual`: item escolhido por voce na aba `Mensagens`
- `origem automatico`: item criado automaticamente apos uma varredura, quando esse modo estiver ativo

## 8. Erros comuns

### A dashboard nao abre
Causa provavel:
- frontend sem build

Correcao:
```bash
cd frontend
npm install
npm run build
cd ..
```

### O envio nao sai
Causas comuns:

- `EVOLUTION_BASE_URL` incorreto
- `EVOLUTION_API_KEY` invalida
- instancia desconectada no Evolution
- horario fora da janela util
- limite diario atingido

### Lead vira `sem_whatsapp`
Significa que a validacao do endpoint `whatsappNumbers` retornou que o numero nao existe.

### Lead vira `erro`
Significa que houve falha repetida e o sistema atingiu `MAX_TENTATIVAS`.

## 9. Exportacao e persistencia

Nada mudou na exportacao:

- CSV e XLSX continuam funcionando
- agora os novos campos tambem podem sair na exportacao

Persistencia local:

- base principal em `database.db`
- fila de disparos tambem fica no mesmo banco

## 10. Observacoes de escopo

Esta entrega nao implementa inbound automatico para marcar `respondeu`.

Ou seja:

- o sistema envia e controla fila
- o sistema nao recebe resposta automaticamente da Evolution nesta fase
