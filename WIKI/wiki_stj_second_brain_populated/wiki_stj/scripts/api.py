#!/usr/bin/env python3
"""
api.py — Servidor FastAPI para busca de jurisprudência STJ

Endpoints:
    GET /buscar_juris?q=...&k=15&modo=hibrido&alpha=0.5
    GET /health

Uso:
    python api.py
    # ou
    uvicorn api:app --reload --port 8000
"""

import sys
from pathlib import Path

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).parent))
from stj_busca_hibrida import BuscaHibrida

app = FastAPI(
    title="STJ Jurisprudência API",
    description="Busca híbrida BM25 + Semântica em 638k acórdãos do STJ",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Instância única compartilhada (carregamento lazy na primeira busca)
_bh: BuscaHibrida | None = None

def get_bh() -> BuscaHibrida:
    global _bh
    if _bh is None:
        _bh = BuscaHibrida()
    return _bh


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/buscar_juris")
def buscar_juris(
    q: str = Query(..., description="Consulta em linguagem natural"),
    k: int = Query(15, ge=1, le=100, description="Número de resultados"),
    modo: str = Query("hibrido", pattern="^(hibrido|bm25|semantico)$"),
    alpha: float = Query(0.5, ge=0.0, le=1.0, description="Peso semântico [0-1]"),
):
    """
    Busca acórdãos do STJ por relevância.

    - **q**: consulta em linguagem natural (ex: "penhorabilidade bem de família")
    - **k**: número de resultados (1-100)
    - **modo**: `hibrido` (padrão), `bm25` (só lexical), `semantico` (só vetorial)
    - **alpha**: peso da busca semântica — 0=só BM25, 1=só semântico
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="Parâmetro 'q' não pode ser vazio.")

    try:
        bh = get_bh()
        bh.alpha = alpha
        resultados = bh.buscar(q.strip(), k=k, modo=modo)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "query": q,
        "modo": modo,
        "alpha": alpha,
        "total": len(resultados),
        "resultados": resultados,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
