---
title: "OUTPUTS — Entregáveis do Claude"
category: "sistema"
created: "2026-04-11"
updated: "2026-04-11"
---

# OUTPUTS/

Pasta de destino padrão para todos os entregáveis gerados pelo Claude em sessões de trabalho.

## Estrutura

```
OUTPUTS/
├── pecas/          # Peças processuais redigidas
├── pesquisas/      # Relatórios de pesquisa jurisprudencial
├── relatorios/     # Relatórios de análise (LINT, diagnósticos, etc.)
└── outros/         # Demais entregáveis
```

## Convenção de nomenclatura

`AAAA-MM-DD_tipo_descricao-breve.ext`

Exemplos:
- `2026-04-11_peca_apelacao-cliente-x-banco-y.docx`
- `2026-04-11_pesquisa_penhorabilidade-bem-familia.md`
- `2026-04-11_relatorio_lint-vault.md`

## Regra

Todo arquivo gerado pelo Claude que deva ser preservado além da sessão vai para esta pasta — nunca diretamente na raiz da wiki.
