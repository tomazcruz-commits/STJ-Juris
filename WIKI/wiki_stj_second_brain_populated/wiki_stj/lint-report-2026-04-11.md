---
title: "Relatório de LINT — 2026-04-11"
category: "sistema"
created: "2026-04-11"
tipo: "lint"
---

# Relatório de LINT — 2026-04-11

> Diagnóstico de saúde do vault. Gerado automaticamente + análise manual.

---

## Resumo Executivo

| Métrica | Valor | Status |
|:---|:---|:---|
| Total de arquivos .md | 556 | — |
| Stubs pendentes de preenchimento | 443 | 🟡 Normal — gerados pelo bootstrap |
| Links quebrados detectados | 441 | 🔴 Requer atenção (maioria esperada) |
| Possíveis orphans | 456 | 🟡 Maioria são stubs sem links de entrada ainda |

---

## Análise dos Links Quebrados

### Categoria 1 — Links de exemplo no CLAUDE.md *(ignorar)*
`[[nome-da-pagina]]` e `[[nomes-de-paginas]]` são placeholders nos exemplos do CLAUDE.md. Não são links reais.

**Ação:** Nenhuma.

### Categoria 2 — Páginas de relatores ainda não criadas *(lacuna real)*
O `index.md` referencia páginas de relatores (Moura Ribeiro, Nancy Andrighi, Ricardo Cueva, etc.) que ainda não foram criadas no diretório `relatores/`.

Relatores referenciados mas sem página:
- `[[moura-ribeiro]]`
- `[[nancy-andrighi]]`
- `[[antonio-carlos-ferreira]]`
- `[[maria-isabel-gallotti]]`
- `[[raul-araujo]]`
- `[[joao-otavio-de-noronha]]`
- `[[humberto-martins]]`
- `[[ricardo-villas-boas-cueva]]`

**Ação:** Criar páginas de relatores (Fase 3 — já planejado como parte de ingestão futura).

### Categoria 3 — Links nos stubs de peças *(estrutural — aceitar)*
Os 443 stubs gerados pelo bootstrap têm links para `pecas/<tipo>/index` — esses índices existem. Eventual discrepância é de formatação de wikilink com `\|` de escape.

**Ação:** Verificar no Obsidian se os links resolvem. Se não, ajustar o formato nos templates.

---

## Análise dos Orphans

### Categoria 1 — Stubs de peças sem links de entrada *(esperado)*
As ~443 peças em `pecas/` são orphans porque ainda nenhuma página de tema ou súmula linka para elas. Isso é **normal nesta fase** — os links serão construídos progressivamente conforme os stubs forem preenchidos.

**Ação:** Nenhuma agora. Revisar em próximo LINT após preenchimento dos stubs.

### Categoria 2 — Páginas de sistema sem links de entrada *(aceitar)*
- `web-clipper-workflow.md` — novo, ainda não linkado do índice principal
- `about-me/about-me.md` — arquivo de contexto, não precisa de links de entrada

**Ação:** Adicionar link para `web-clipper-workflow.md` no `index.md` principal.

### Categoria 3 — Páginas de órgãos com encoding quebrado *(bug de nomenclatura)*
Páginas como `orgaos/1a-seção.md` aparecem com encoding corrompido (`1a-se├º├úo.md`) no terminal. Isso é problema de exibição no shell, não nos arquivos reais. Verificar no Obsidian.

**Ação:** Abrir no Obsidian e confirmar se os títulos renderizam corretamente.

---

## Lacunas Identificadas

### 1. Diretório `relatores/` — páginas não criadas
O `index.md` referencia ~15 relatores. Nenhum tem página ainda.
**Prioridade:** Média — criar junto com próxima ingestão de julgados.

### 2. Diretório `sinteses/capturados/` — não existe
O workflow do Web Clipper aponta para `sinteses/capturados/` mas a pasta ainda não existe.
**Prioridade:** Alta — criar antes de usar o Web Clipper.

### 3. Stubs de peças — 443 pendentes de preenchimento
Normal para esta fase. Priorizar os tipos mais frequentes: EDcl (56) e REsp (23).

---

## Recomendações para Próximo LINT

Executar em ~30 dias ou após:
- Ingestão de novos julgados
- Preenchimento de 10+ stubs de peças
- Criação das páginas de relatores

---

## Registro em log
Ver: [[log]]
