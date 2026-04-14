---
title: "Dataview Queries — Referência Rápida"
category: "sistema"
created: "2026-04-11"
updated: "2026-04-11"
plugin: "Obsidian Dataview"
---

# Dataview Queries

> Queries prontas para uso no Obsidian com o plugin **Dataview**.
> Instalar: Configurações → Plugins da comunidade → Dataview.
> Copiar o bloco de código para qualquer nota e ele renderiza automaticamente.

---

## PEÇAS PROCESSUAIS

### Todas as peças por tipo e ano

~~~dataview
TABLE ano, polo_ativo, polo_passivo, resultado
FROM "pecas"
WHERE type = "peca"
SORT ano DESC
~~~

### Peças sem resultado preenchido (stubs pendentes)

~~~dataview
TABLE ano, categoria, polo_ativo
FROM "pecas"
WHERE type = "peca" AND resultado = ""
SORT ano DESC
~~~

### REsps interpostos

~~~dataview
TABLE ano, polo_ativo, polo_passivo, resultado
FROM "pecas/resp"
SORT ano DESC
~~~

### Peças de 2025–2026

~~~dataview
TABLE categoria, polo_ativo, polo_passivo
FROM "pecas"
WHERE type = "peca" AND ano >= 2025
SORT ano DESC, categoria ASC
~~~

### Peças com teses específicas preenchidas

~~~dataview
TABLE ano, categoria, teses
FROM "pecas"
WHERE type = "peca" AND length(teses) > 0
SORT ano DESC
~~~

---

## SÚMULAS

### Todas as súmulas por número

~~~dataview
TABLE numero, enunciado
FROM "sumulas"
WHERE type = "sumula"
SORT numero ASC
~~~

### Súmulas marcadas com atenção (⚠️)

~~~dataview
TABLE numero, enunciado, status
FROM "sumulas"
WHERE status = "verificar" OR contains(enunciado, "⚠️")
~~~

---

## TEMAS REPETITIVOS

### Todos os temas por número

~~~dataview
TABLE numero, titulo, status_atual
FROM "temas"
WHERE type = "tema"
SORT numero ASC
~~~

### Temas com status pendente ou em revisão

~~~dataview
TABLE numero, titulo, status_atual
FROM "temas"
WHERE status_atual != "consolidado" AND type = "tema"
~~~

---

## LEGISLAÇÃO

### Diplomas disponíveis

~~~dataview
TABLE diploma, foco
FROM "legislacao"
WHERE category = "legislacao" AND file.name != "index"
~~~

---

## CLASSES PROCESSUAIS

### Classes disponíveis no STJ

~~~dataview
TABLE sigla, file.link AS "Página"
FROM "classes"
WHERE category = "classes" AND file.name != "index"
~~~

---

## LOG DO VAULT

### Últimas 10 entradas do log

~~~dataview
LIST
FROM "."
WHERE file.name = "log"
LIMIT 1
~~~

> **Nota:** O log.md usa formato de cabeçalhos h2 por data — o Dataview não extrai entradas individuais do log. Usar para navegar ao arquivo; a leitura é feita diretamente.

---

## MAPA DE STUBS PRIORITÁRIOS

### EDcl sem contexto preenchido (prioridade — 56 peças)

~~~dataview
TABLE ano, polo_ativo, polo_passivo
FROM "pecas/edcl"
WHERE status = "stub"
SORT ano DESC
LIMIT 20
~~~

### REsps sem resultado (prioridade — 23 peças)

~~~dataview
TABLE ano, polo_ativo, polo_passivo
FROM "pecas/resp"
WHERE status = "stub"
SORT ano DESC
~~~

---

## DASHBOARD GERAL

> Copiar em uma nota chamada `dashboard.md` para ter visão consolidada do vault.

~~~dataview
TABLE WITHOUT ID
  length(rows) AS "Total"
FROM "pecas"
WHERE type = "peca"
GROUP BY categoria
SORT length(rows) DESC
~~~
