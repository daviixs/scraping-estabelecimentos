# Design: varredura operacional com meta minima e comando livre

## Objetivo

Adicionar uma entrada operacional no dashboard para disparar varreduras por comando livre, garantindo no minimo 30 estabelecimentos novos por execucao quando houver oferta suficiente na fonte.

## Regras validadas

- A varredura deve continuar procurando ate encontrar pelo menos 30 estabelecimentos novos.
- No Google Maps, quando os resultados iniciais nao bastarem, a coleta deve continuar carregando mais resultados.
- Estabelecimentos ja existentes no banco devem ser ignorados por completo e nao contam para a meta minima.
- O frontend deve expor um seletor explicito de site e uma caixa livre para o comando inteiro.
- As fontes operacionais da interface sao Google Maps e Apontador.

## Arquitetura proposta

### Backend

- Criar um servico de varredura reutilizavel pelo CLI e pelo dashboard.
- Introduzir um parser de comando livre para aceitar formatos curtos e o comando estilo terminal.
- Introduzir um parser especifico da dashboard que recebe a fonte pelo seletor da UI.
- Separar a execucao sincrona da varredura da camada HTTP.
- Expor jobs em memoria para o dashboard acompanhar status, progresso e resultado.

### Coleta

- Google Maps passa a operar de forma incremental, consumindo os cards ja carregados, abrindo detalhes, avaliando duplicidade e continuando a carregar mais resultados ate atingir a meta ou esgotar a busca.
- Apontador continua paginando, mas agora para quando atingir a meta de novos estabelecimentos.
- A deduplicacao usa a chave atual do sistema: `nome + cidade`.

### Persistencia

- Antes de inserir, verificar se o estabelecimento ja existe.
- Se existir, ignorar sem atualizar historico, comentarios ou queixas.
- Se for novo, persistir usando o fluxo atual de score, queixas e historico.

### Dashboard

- Adicionar um card no topo com o titulo `Procurar estabelecimentos`.
- O card tera seletor de site, caixa livre para o comando inteiro, exemplos clicaveis e botao de executar.
- Durante a execucao, exibir status, novos encontrados, duplicados ignorados, paginas percorridas e mensagem atual.
- Ao finalizar com sucesso ou parcial, recarregar KPIs, filtros e tabela principal.

## API

- `POST /api/varreduras` inicia um job a partir de `source + command`.
- `GET /api/varreduras/<job_id>` retorna o status detalhado do job.
- `GET /api/varreduras/ativa` retorna o job ativo ou o ultimo job conhecido para restaurar a interface.

## Estados de execucao

- `queued`: job criado e aguardando inicio.
- `running`: job em execucao.
- `completed`: meta minima atingida.
- `partial`: busca esgotada antes da meta minima.
- `error`: falha inesperada na coleta ou no processamento.

## Testes

- Parser do comando livre no CLI e parser especifico da dashboard por fonte.
- Endpoint de criacao e leitura de jobs.
- Persistencia com ignorar existentes.
- Fluxo de UI para disparar e acompanhar a varredura.
