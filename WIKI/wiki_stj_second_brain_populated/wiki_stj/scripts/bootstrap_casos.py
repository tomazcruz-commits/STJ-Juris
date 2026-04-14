#!/usr/bin/env python3
"""
bootstrap_casos.py — Gerador de stubs de casos processuais

Lê o pecas_mapping.json e agrupa as peças por (cliente + adversário)
para gerar um stub de caso por litígio identificado.

Saída:
  - wiki_stj/casos/<caso_id>.md     — stub por caso
  - wiki_stj/casos/index.md         — índice geral
  - casos_mapping.json              — mapeamento caso_id → peças
"""

import json
import re
import hashlib
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ─── CONFIG ───────────────────────────────────────────────────────────────────

WIKI_ROOT    = Path("/sessions/elegant-great-clarke/mnt/STJ JURIS/WIKI/wiki_stj_second_brain_populated/wiki_stj")
MAPPING_IN   = WIKI_ROOT / "pecas" / "pecas_mapping.json"
CASOS_DIR    = WIKI_ROOT / "casos"
CASOS_MAP    = CASOS_DIR / "casos_mapping.json"
TODAY        = datetime.today().strftime("%Y-%m-%d")

# Tipos que indicam ação principal (não incidente)
TIPOS_ACAO_PRINCIPAL = {
    "PETIÇÃO INICIAL", "CONTESTAÇÃO", "EMBARGOS DE DECLARAÇÃO",
    "APELAÇÃO", "RECURSO ESPECIAL", "AGRAVO DE INSTRUMENTO",
    "AGRAVO INTERNO", "RÉPLICA", "CONTRARRAZÕES", "CUMPRIMENTO DE SENTENÇA",
    "IMPUGNAÇÃO", "IMPUGNAÇÃO À PENHORA", "MEMORIAL", "RAZÕES FINAIS",
}

# ─── NORMALIZAÇÃO DE ADVERSÁRIO ───────────────────────────────────────────────

def normalizar_adversario(parties: str, cliente: str) -> str:
    """Extrai a parte adversária a partir do par 'CLIENTE x ADVERSÁRIO'."""
    parts = parties.split(" x ", 1)
    if len(parts) < 2:
        return parties.strip()
    # Identificar qual lado é o cliente e qual é o adversário
    lado_a = parts[0].strip().upper()
    lado_b = parts[1].strip().upper()
    cliente_up = cliente.strip().upper()
    # Verificar similaridade com o cliente
    if cliente_up in lado_a or lado_a in cliente_up:
        return lado_b
    return lado_a  # fallback: retornar lado A

def abbrev(nome: str, n: int = 4) -> str:
    return re.sub(r'[^A-Z0-9]', '', nome.upper())[:n]

def caso_id(cliente: str, adversario: str) -> str:
    h = hashlib.md5(f"{cliente}|{adversario}".encode()).hexdigest()[:4].upper()
    return f"CASO-{abbrev(cliente)}-{abbrev(adversario)}-{h}"

# ─── TEMPLATE DE STUB ─────────────────────────────────────────────────────────

def stub_caso(cid, cliente, adversario, pecas_list):
    anos = sorted({p["year"] for p in pecas_list})
    ano_inicio = anos[0] if anos else "—"
    ano_fim    = anos[-1] if anos else "—"
    total      = len(pecas_list)

    # Inferir tipo de ação principal a partir dos tipos de peças
    tipos_presentes = {p["canonical_type"] for p in pecas_list}
    tipo_acao = "—"
    for t in ["CONTESTAÇÃO", "PETIÇÃO INICIAL", "APELAÇÃO", "RECURSO ESPECIAL"]:
        if t in tipos_presentes:
            tipo_acao = t
            break

    # Polo inferido: se tem Contestação ou é réu → passivo
    polo = "passivo" if "CONTESTAÇÃO" in tipos_presentes else "ativo"

    # Links para os stubs de peças
    links_pecas = "\n".join(
        f"| [[pecas/{p['folder']}/{p['id']}\\|{p['id']}]] | {p['year']} | {p['canonical_type']} | {p.get('status', 'stub')} |"
        for p in sorted(pecas_list, key=lambda x: x["year"])
    )

    return f"""---
id: "{cid}"
title: "Caso {cid} — {cliente} x {adversario}"
type: "caso"
cliente: "{cliente}"
adversario: "{adversario}"
polo: "{polo}"
ano_inicio: {ano_inicio}
ano_fim: {ano_fim}
status_caso: "em andamento"
desfecho: ""
created: "{TODAY}"
updated: "{TODAY}"
total_pecas: {total}
---

# Caso {cid}
## {cliente} × {adversario}

> **Status:** stub gerado automaticamente — preencher após análise do processo.
> **Polo:** {polo} | **Período:** {ano_inicio}–{ano_fim} | **Peças indexadas:** {total}

---

## Resumo do Caso

<!-- Descrição em 3–5 linhas: qual é a demanda, o que está em jogo, fase atual -->

**Tipo de ação:** {tipo_acao}
**Tribunal:** <!-- TJPE / TRF5 / STJ -->
**Número do processo:** <!-- preencher -->
**Valor da causa:** <!-- preencher -->

---

## Mapa Estratégico

### Tese do autor
<!-- O que o autor alega e pretende -->

### Tese da defesa
<!-- Os principais argumentos defensivos usados -->

### Pontos controvertidos
<!-- O que está genuinamente em disputa — fático e jurídico -->

### Análise de Nash / Teoria dos Jogos
<!-- [Opcional] Qual é o equilíbrio esperado? Qual a melhor resposta a cada movimento adversário? -->

---

## Linha do Tempo

| Data | Evento | Peça / Decisão |
|:-----|:-------|:---------------|
| | | |

---

## Peças Processuais

| ID | Ano | Tipo | Status |
|:---|:----|:-----|:-------|
{links_pecas}

---

## Jurisprudência Chave

<!-- Súmulas e acórdãos que fundamentam ou impactam este caso -->

| Referência | Aplicação |
|:-----------|:----------|
| | |

---

## Desfecho

<!-- Preencher quando o caso for encerrado -->

**Resultado:** <!-- procedente / improcedente / acordo / em andamento -->
**Data do trânsito:** <!-- -->
**Valor final:** <!-- -->

---

## Lições Aprendidas

<!-- O que este caso ensinou? O que faria diferente? -->

---

*Links: [[casos/index|Índice de Casos]] | Cliente: {cliente}*
"""

# ─── ÍNDICE GERAL ─────────────────────────────────────────────────────────────

def index_casos(casos_list):
    em_andamento = [c for c in casos_list if c["status"] == "em andamento"]
    rows = "\n".join(
        f"| [[casos/{c['id']}\\|{c['id']}]] | {c['cliente']} | {c['adversario']} | {c['polo']} | {c['ano_inicio']}–{c['ano_fim']} | {c['total_pecas']} | {c['status']} |"
        for c in sorted(casos_list, key=lambda x: (-int(x['ano_fim']) if x['ano_fim'] != '—' else 0))
    )

    return f"""---
title: "Casos — Índice Geral"
category: "casos"
created: "{TODAY}"
updated: "{TODAY}"
total_casos: {len(casos_list)}
em_andamento: {len(em_andamento)}
---

# Casos — Índice Geral

> **Nota de privacidade:** Os IDs de caso (CASO-XXXX-YYYY-ZZZZ) são códigos internos.
> Os nomes de clientes e partes adversas são visíveis apenas nesta wiki local, nunca em documentos externos.

**Total de casos:** {len(casos_list)} | **Em andamento:** {len(em_andamento)}

---

## Como usar este diretório

1. Cada página de caso agrega todas as peças de um mesmo litígio
2. Preencher os campos de contexto e estratégia após analisar o processo
3. A linha do tempo deve ser atualizada a cada evento processual relevante
4. O mapa estratégico pode ser enriquecido com análise de teoria dos jogos quando relevante

---

## Todos os Casos

| ID | Cliente | Adversário | Polo | Período | Peças | Status |
|:---|:--------|:-----------|:-----|:--------|------:|:-------|
{rows}

---

## Filtros úteis (Dataview)

Adicionar em uma nota separada:

~~~dataview
TABLE cliente, adversario, polo, ano_inicio, total_pecas, desfecho
FROM "casos"
WHERE type = "caso" AND status_caso = "em andamento"
SORT ano_inicio DESC
~~~

---

*Gerado em {TODAY} via bootstrap_casos.py*
"""

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    print("📂 Lendo pecas_mapping.json...")
    with open(MAPPING_IN, encoding="utf-8") as f:
        pecas = json.load(f)
    print(f"   {len(pecas)} peças carregadas")

    # Agrupar por (cliente, adversário normalizado)
    grupos = defaultdict(list)
    for pid, p in pecas.items():
        cliente = p.get("client_folder", "DESCONHECIDO")
        adversario = normalizar_adversario(p.get("parties", ""), cliente)
        chave = (cliente, adversario)
        grupos[chave].append(p)

    print(f"   {len(grupos)} casos identificados")

    CASOS_DIR.mkdir(parents=True, exist_ok=True)

    casos_index = []
    casos_map   = {}

    for (cliente, adversario), pecas_list in sorted(grupos.items()):
        cid = caso_id(cliente, adversario)

        # Deduplicar IDs em caso de colisão
        base_cid = cid
        sufixo = 1
        while cid in casos_map:
            cid = f"{base_cid}-{sufixo}"
            sufixo += 1

        anos = sorted({p["year"] for p in pecas_list})
        entry = {
            "id": cid,
            "cliente": cliente,
            "adversario": adversario,
            "polo": "passivo" if any(p["canonical_type"] == "CONTESTAÇÃO" for p in pecas_list) else "ativo",
            "ano_inicio": anos[0] if anos else "—",
            "ano_fim": anos[-1] if anos else "—",
            "total_pecas": len(pecas_list),
            "status": "em andamento",
            "pecas_ids": [p["id"] for p in pecas_list],
        }

        casos_index.append(entry)
        casos_map[cid] = entry

        # Criar stub apenas se não existir
        stub_path = CASOS_DIR / f"{cid}.md"
        if not stub_path.exists():
            stub_path.write_text(stub_caso(cid, cliente, adversario, pecas_list), encoding="utf-8")

    # Índice
    (CASOS_DIR / "index.md").write_text(index_casos(casos_index), encoding="utf-8")

    # Mapping
    with open(CASOS_MAP, "w", encoding="utf-8") as f:
        json.dump(casos_map, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Bootstrap concluído!")
    print(f"   {len(casos_index)} casos gerados em casos/")
    print(f"\n📊 Distribuição polo:")
    ativos   = sum(1 for c in casos_index if c["polo"] == "ativo")
    passivos = sum(1 for c in casos_index if c["polo"] == "passivo")
    print(f"   Polo ativo:   {ativos}")
    print(f"   Polo passivo: {passivos}")
    print(f"\n📊 Por volume de peças:")
    por_vol = sorted(casos_index, key=lambda x: -x["total_pecas"])
    for c in por_vol[:10]:
        print(f"   {c['id']:<30} {c['total_pecas']:>3} peças  ({c['cliente']} x {c['adversario'][:20]})")

if __name__ == "__main__":
    main()
