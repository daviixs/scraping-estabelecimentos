# Dashboard v2 — Tailwind + shadcn + Motion (Tema Areia/Vermelho)

## Objetivo
Reestilizar a dashboard Astro/Flask aplicando Tailwind, componentes estilo shadcn/ui e microinterações com Framer Motion, mantendo a mesma API backend. Tema visual: fundo areia claro, acento vermelho profundo, tipografia Geist/Geist Mono.

## Stack & Dependências
- Astro 4 + integração React (`@astrojs/react`)
- Tailwind + PostCSS + autoprefixer + `@astrojs/tailwind`
- shadcn-style UI (componentes locais Button, Card, Badge, Skeleton, etc.)
- Framer Motion para animações (stagger, spring, progress)
- Ícones: `@phosphor-icons/react`
- Fontes: `@fontsource/geist`, `@fontsource/geist-mono`

## Paleta & Tipografia
- Background: `#f9f5f0`
- Superfícies: `#fffaf5`
- Texto principal: `#231f1a` (grafite quente)
- Acento: `#b41632` (vermelho profundo)
- Borda: `#e7dfd6`
- Tipos: Geist (display/body), Geist Mono (números).

## Layout & Componentes
- Header slim com ações de export (ghost/primary) e CTA magnético leve.
- KPIs em bento grid (2x2) com contagem animada e pílula de variação; skeletons no carregamento.
- Painel de filtros lateral: accordions para classificação/prioridade/fonte, selects para cidade/categoria, slider de score; colapsável em mobile.
- Tabela com head sticky, ordenação clicável, badges de prioridade, barra de score animada; empty state e erro state.
- Paginação numérica com micro transição.

## Motion
- Page-load stagger (fade + translate).
- Spring nos botões (tap scale 0.98) e barras de score.
- Stagger na tabela (layout + opacity).
- Skeleton shimmer para KPIs e tabela.

## Responsividade
- Mobile: filtros viram drawer/stack, grid colapsa para 1 coluna, tabela scroll horizontal com sombra.
- Evitar `h-screen`; usar `min-h-[100dvh]`.

## Arquivos a alterar/criar
- `package.json`: dependências React/Tailwind/shadcn/framer/fonts/icons.
- `astro.config.mjs`: add plugins React e Tailwind.
- `tailwind.config.cjs`, `postcss.config.cjs`, `src/styles/tailwind.css`.
- `src/components` (React): `DashboardApp.tsx`, `ui/*`, `lib/utils.ts`.
- Atualizar `src/pages/index.astro` para carregar fontes e montar `<DashboardApp client:load />`.

## Testes/Build
- `npm run build` (frontend) após `npm install`.
- Verificação manual em `astro dev` e com backend Flask ativo.
