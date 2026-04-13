---
title: "TEMPLATES — Scaffolding de Peças Processuais"
category: "sistema"
created: "2026-04-11"
updated: "2026-04-11"
---

# TEMPLATES/

Scaffolding estrutural das peças processuais mais frequentes. Não são modelos prontos — são arquiteturas de argumento: onde vai cada elemento, qual a sequência lógica, quais seções são obrigatórias vs. opcionais.

## Templates disponíveis

| Arquivo | Tipo de peça | Status |
|:---|:---|:---|
| `tpl-edcl.md` | Embargos de declaração | ✅ disponível |
| `tpl-agravo-instrumento.md` | Agravo de instrumento | ✅ disponível |
| `tpl-resp.md` | Recurso especial | ✅ disponível |
| `tpl-contestacao.md` | Contestação | ✅ disponível |
| `tpl-peticao-inicial.md` | Petição inicial cível | ✅ disponível |
| `tpl-apelacao.md` | Apelação cível | 🔜 a criar |
| `tpl-agravo-resp.md` | Agravo em REsp | 🔜 a criar |
| `tpl-impugnacao-execucao.md` | Impugnação ao cumprimento de sentença | 🔜 a criar |

## Como usar

1. Abrir o template do tipo de peça pretendida
2. Preencher os campos marcados com `{{}}` com os dados do caso
3. As seções marcadas com `[OPCIONAL]` só entram se houver conteúdo relevante
4. Nunca usar o template como texto final — é apenas a estrutura; o conteúdo deve ser escrito para o caso concreto

## Como atualizar

Quando uma peça concreta produzir uma solução estrutural boa que difira do template, atualizar o template correspondente e registrar no log.md.
