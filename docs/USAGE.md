# Uso do Bot de Inteligencia Comercial

Este arquivo virou um indice rapido.

## Guias atuais
- `README.md`: setup do projeto, build do frontend e operacao geral
- `docs/USAGE-WHATSAPP.md`: uso detalhado da nova aba `Mensagens`, fila e disparo WhatsApp

## Fluxo resumido
1. Instale dependencias Python e Playwright
2. Rode o build do frontend em `frontend/`
3. Suba a dashboard com `.venv/bin/python main.py --dashboard`
4. Colete leads
5. Aprove leads na aba `Estabelecimentos`
6. Inicie e acompanhe o scheduler na aba `Mensagens`
