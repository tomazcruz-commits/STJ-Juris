#!/usr/bin/env python3
"""
stj_mcp_server.py — Servidor MCP para busca de jurisprudência STJ

Expõe os 638k acórdãos do STJ como ferramentas nativas do Claude via MCP.
Usa fastmcp para criar o servidor em Python puro.

Ferramentas disponíveis:
  - buscar_jurisprudencia: busca híbrida BM25 + semântica
  - buscar_por_tema:       filtra acórdãos por número de tema repetitivo
  - buscar_por_relator:    filtra acórdãos por relator
  - status_banco:          retorna estatísticas do banco

Registro no claude_desktop_config.json:
  {
    "mcpServers": {
      "stj-jurisprudencia": {
        "command": "python",
        "args": ["C:\\...\\stj_mcp_server.py"]
      }
    }
  }
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from fastmcp import FastMCP
from typing import Optional

# ─── Instância MCP ───────────────────────────────────────────────────────────
mcp = FastMCP(
    name="STJ Jurisprudência",
    instructions=(
        "Acesso ao banco de 638.198 acórdãos do Superior Tribunal de Justiça (STJ). "
        "Use buscar_jurisprudencia para pesquisas em linguagem natural sobre temas jurídicos. "
        "Prefira sempre consultar este banco antes de responder perguntas sobre jurisprudência brasileira. "
        "Os resultados incluem ementa, tese, relator, data e classe processual."
    )
)

# Inicialização lazy do motor de busca
_bh = None

def _get_busca():
    global _bh
    if _bh is None:
        from stj_busca_hibrida import BuscaHibrida
        _bh = BuscaHibrida(alpha=0.5)
    return _bh


# ─── FERRAMENTA 1: Busca híbrida ─────────────────────────────────────────────

@mcp.tool()
def buscar_jurisprudencia(
    consulta: str,
    k: int = 10,
    modo: str = "hibrido",
    alpha: float = 0.5,
) -> str:
    """
    Busca acórdãos do STJ por relevância usando busca híbrida (BM25 + semântica).

    Args:
        consulta: Pergunta ou tema jurídico em linguagem natural.
                  Ex: "responsabilidade civil médica erro diagnóstico"
                      "prazo prescricional dano moral consumidor"
                      "bem de família impenhorável fiador locação"
        k:        Número de acórdãos a retornar (1-30). Padrão: 10.
        modo:     Modo de busca:
                  - "hibrido"   → BM25 + semântica (recomendado)
                  - "semantico" → só busca por conceito/significado
                  - "bm25"      → só busca por palavras-chave exatas
        alpha:    Peso da busca semântica (0.0=só BM25, 1.0=só semântico).
                  Padrão 0.5 (equilíbrio). Use 0.7+ para consultas conceituais.

    Returns:
        Lista formatada dos acórdãos mais relevantes com score, classe,
        relator, data, ementa e tese jurídica.
    """
    if not consulta or not consulta.strip():
        return "Erro: forneça uma consulta não vazia."

    k = max(1, min(k, 30))

    try:
        bh = _get_busca()
        bh.alpha = alpha
        resultados = bh.buscar(consulta.strip(), k=k, modo=modo)
    except Exception as e:
        return f"Erro na busca: {e}"

    if not resultados:
        return f"Nenhum acórdão encontrado para: '{consulta}'"

    linhas = [
        f"## Resultados para: \"{consulta}\"",
        f"Modo: {modo} | alpha={alpha} | {len(resultados)} acórdãos\n",
    ]

    for i, r in enumerate(resultados, 1):
        data = _fmt_data(r.get("dataDecisao", ""))
        tema_s = f" | Tema {r['tema']}" if r.get("tema") else ""
        ementa = (r.get("ementa_curta") or "").replace("\n", " ").strip()
        tese   = (r.get("tese_curta") or "").replace("\n", " ").strip()

        linhas.append(f"### {i}. {r.get('classe','')} — {r.get('orgao','')}{tema_s}")
        linhas.append(f"**Relator:** {r.get('relator','')} | **Data:** {data} | **Score:** {r.get('score',0):.5f}")
        linhas.append(f"**Ementa:** {ementa[:400]}")
        if tese:
            linhas.append(f"**Tese:** {tese[:300]}")
        linhas.append("")

    return "\n".join(linhas)


# ─── FERRAMENTA 2: Busca por tema repetitivo ─────────────────────────────────

@mcp.tool()
def buscar_por_tema(
    numero_tema: int,
    k: int = 10,
) -> str:
    """
    Retorna acórdãos do STJ associados a um tema repetitivo específico.

    Args:
        numero_tema: Número do tema repetitivo do STJ.
                     Ex: 1051, 972, 686, 881
        k:           Número de acórdãos a retornar (1-50). Padrão: 10.

    Returns:
        Acórdãos vinculados ao tema, com ementa e tese.
    """
    import sqlite3
    from pathlib import Path

    db = Path(r"C:\Users\tomaz\OneDrive\Área de Trabalho\STJ JURIS\stj_mini.db")
    k  = max(1, min(k, 50))

    try:
        con = sqlite3.connect(str(db), timeout=30)
        cur = con.cursor()
        cur.execute("""
            SELECT rowid, id, classe, orgao, relator, dataDecisao,
                   tema, ementa_curta, tese_curta
            FROM decisoes_mini
            WHERE tema = ?
            LIMIT ?
        """, (str(numero_tema), k))
        rows = cur.fetchall()
        con.close()
    except Exception as e:
        return f"Erro ao consultar banco: {e}"

    if not rows:
        return f"Nenhum acórdão encontrado para o Tema {numero_tema}."

    linhas = [f"## Tema Repetitivo {numero_tema} — {len(rows)} acórdão(s)\n"]
    for i, r in enumerate(rows, 1):
        data = _fmt_data(r[5] or "")
        ementa = (r[7] or "").replace("\n", " ").strip()
        tese   = (r[8] or "").replace("\n", " ").strip()
        linhas.append(f"### {i}. {r[2]} — {r[3]}")
        linhas.append(f"**Relator:** {r[4]} | **Data:** {data}")
        linhas.append(f"**Ementa:** {ementa[:400]}")
        if tese:
            linhas.append(f"**Tese:** {tese[:300]}")
        linhas.append("")

    return "\n".join(linhas)


# ─── FERRAMENTA 3: Busca por relator ─────────────────────────────────────────

@mcp.tool()
def buscar_por_relator(
    nome_relator: str,
    k: int = 10,
    filtro_texto: Optional[str] = None,
) -> str:
    """
    Retorna acórdãos do STJ de um relator específico, com filtro opcional por texto.

    Args:
        nome_relator:  Nome (parcial) do relator. Ex: "Nancy Andrighi", "Luis Felipe"
        k:             Número de resultados (1-50). Padrão: 10.
        filtro_texto:  Palavra-chave opcional para filtrar por ementa.
                       Ex: "dano moral", "prescrição"

    Returns:
        Acórdãos do relator, ordenados por data decrescente.
    """
    import sqlite3
    from pathlib import Path

    db = Path(r"C:\Users\tomaz\OneDrive\Área de Trabalho\STJ JURIS\stj_mini.db")
    k  = max(1, min(k, 50))

    try:
        con = sqlite3.connect(str(db), timeout=30)
        cur = con.cursor()

        if filtro_texto:
            cur.execute("""
                SELECT rowid, id, classe, orgao, relator, dataDecisao,
                       tema, ementa_curta, tese_curta
                FROM decisoes_mini
                WHERE relator LIKE ?
                  AND (ementa_curta LIKE ? OR tese_curta LIKE ?)
                ORDER BY dataDecisao DESC
                LIMIT ?
            """, (f"%{nome_relator}%", f"%{filtro_texto}%", f"%{filtro_texto}%", k))
        else:
            cur.execute("""
                SELECT rowid, id, classe, orgao, relator, dataDecisao,
                       tema, ementa_curta, tese_curta
                FROM decisoes_mini
                WHERE relator LIKE ?
                ORDER BY dataDecisao DESC
                LIMIT ?
            """, (f"%{nome_relator}%", k))

        rows = cur.fetchall()
        con.close()
    except Exception as e:
        return f"Erro ao consultar banco: {e}"

    if not rows:
        return f"Nenhum acórdão encontrado para relator '{nome_relator}'."

    filtro_s = f" com '{filtro_texto}'" if filtro_texto else ""
    linhas = [f"## Acórdãos de {nome_relator}{filtro_s} — {len(rows)} resultado(s)\n"]
    for i, r in enumerate(rows, 1):
        data   = _fmt_data(r[5] or "")
        ementa = (r[7] or "").replace("\n", " ").strip()
        tema_s = f" | Tema {r[6]}" if r[6] else ""
        linhas.append(f"### {i}. {r[2]} — {r[3]}{tema_s}")
        linhas.append(f"**Relator:** {r[4]} | **Data:** {data}")
        linhas.append(f"**Ementa:** {ementa[:400]}")
        linhas.append("")

    return "\n".join(linhas)


# ─── FERRAMENTA 4: Status do banco ───────────────────────────────────────────

@mcp.tool()
def status_banco() -> str:
    """
    Retorna estatísticas do banco de jurisprudência STJ.

    Informa: total de acórdãos, período coberto, classes mais frequentes,
    status do índice semântico e disponibilidade do sistema.
    """
    import sqlite3
    from pathlib import Path

    db      = Path(r"C:\Users\tomaz\OneDrive\Área de Trabalho\STJ JURIS\stj_mini.db")
    emb_dir = Path(r"C:\Users\tomaz\AppData\Local\STJ_embeddings")

    try:
        con = sqlite3.connect(str(db), timeout=30)
        cur = con.cursor()

        cur.execute("SELECT COUNT(*) FROM decisoes_mini")
        total = cur.fetchone()[0]

        cur.execute("SELECT MIN(dataDecisao), MAX(dataDecisao) FROM decisoes_mini")
        dmin, dmax = cur.fetchone()

        cur.execute("""
            SELECT classe, COUNT(*) as n
            FROM decisoes_mini
            GROUP BY classe
            ORDER BY n DESC
            LIMIT 5
        """)
        classes = cur.fetchall()
        con.close()
    except Exception as e:
        return f"Erro ao consultar banco: {e}"

    faiss_ok = (emb_dir / "stj_index.faiss").exists()
    emb_ok   = (emb_dir / "stj_embeddings.bin").exists()

    linhas = [
        "## Status do Banco STJ",
        f"**Total de acórdãos:** {total:,}",
        f"**Período:** {_fmt_data(dmin or '')} a {_fmt_data(dmax or '')}",
        f"**Índice semântico (FAISS):** {'✅ disponível' if faiss_ok else '❌ não encontrado'}",
        f"**Embeddings:** {'✅ disponível' if emb_ok else '❌ não encontrado'}",
        "",
        "**Top 5 classes processuais:**",
    ]
    for cls, n in classes:
        linhas.append(f"  - {cls or 'N/A'}: {n:,}")

    return "\n".join(linhas)


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _fmt_data(d: str) -> str:
    if d and len(d) == 8:
        return f"{d[6:8]}/{d[4:6]}/{d[:4]}"
    return d or "—"


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
