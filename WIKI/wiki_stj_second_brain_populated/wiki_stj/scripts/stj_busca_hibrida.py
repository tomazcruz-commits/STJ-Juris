#!/usr/bin/env python3
"""
stj_busca_hibrida.py — Busca híbrida BM25 + Semântica no banco STJ

Combina a busca lexical (FTS5/BM25) com busca vetorial (embeddings)
usando Reciprocal Rank Fusion (RRF) para resultar nos acórdãos
mais relevantes para uma consulta em linguagem natural.

Exemplos de consulta:
    "penhorabilidade bem de família execução condomínio"
    "responsabilidade civil banco dados negativação indevida"
    "prazo decadencial plano saúde recusa cobertura"
    "aplicação CDC contratos bancários"

Uso standalone:
    python stj_busca_hibrida.py "sua consulta aqui"
    python stj_busca_hibrida.py "sua consulta" --k 20 --alpha 0.6

Uso como biblioteca:
    from stj_busca_hibrida import BuscaHibrida
    bh = BuscaHibrida()
    resultados = bh.buscar("penhorabilidade bem de família")
    for r in resultados:
        print(r['score'], r['classe'], r['ementa_curta'][:200])
"""

import sqlite3, json, sys
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional

# ─── CONFIG ──────────────────────────────────────────────────────────────────

STJ_DB    = Path(r"C:\Users\tomaz\OneDrive\Área de Trabalho\STJ JURIS\stj_mini.db")
EMB_DIR   = Path(r"C:\Users\tomaz\AppData\Local\STJ_embeddings")
MODELO    = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DIM       = 384

# ─── BUSCA HÍBRIDA ────────────────────────────────────────────────────────────

class BuscaHibrida:
    """
    Combina FTS5/BM25 (busca lexical) com embeddings (busca semântica)
    usando Reciprocal Rank Fusion (RRF).

    alpha: peso semântico (0=só BM25, 1=só semântico, 0.5=igual)
    k_rrf: constante RRF (60 é padrão da literatura)
    """

    def __init__(self, alpha: float = 0.5, k_rrf: int = 60):
        self.alpha  = alpha
        self.k_rrf  = k_rrf
        self._con   = None
        self._model = None
        self._embs  = None
        self._ids   = None
        self._faiss = None
        self._embeddings_ok = False

    # ── Inicialização lazy ────────────────────────────────────────────────────

    def _get_con(self):
        if self._con is None:
            self._con = sqlite3.connect(str(STJ_DB), timeout=30)
            self._con.execute('PRAGMA journal_mode=OFF')
            self._con.execute('PRAGMA synchronous=OFF')
            self._con.row_factory = sqlite3.Row
        return self._con

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(MODELO)
        return self._model

    def _carregar_embeddings(self):
        """Carrega índice FAISS ou fallback para numpy flat search."""
        if self._embeddings_ok:
            return True

        import os
        emb_path = EMB_DIR / "stj_embeddings.bin"
        ids_path = EMB_DIR / "stj_embeddings_ids.bin"
        idx_path = EMB_DIR / "stj_index.faiss"

        if not emb_path.exists():
            print("[AVISO] Embeddings não encontrados. "
                  "Execute stj_semantic_indexer.py primeiro.")
            return False

        # Carregar IDs (raw int64)
        self._ids = np.fromfile(str(ids_path), dtype=np.int64)
        n = len(self._ids)

        # Tentar FAISS (mais rápido)
        if idx_path.exists():
            try:
                import faiss
                self._faiss = faiss.read_index(str(idx_path))
                self._faiss.nprobe = 32
                print(f"[INFO] Índice FAISS carregado ({n:,} vetores)")
                self._embeddings_ok = True
                return True
            except ImportError:
                print("[AVISO] faiss-cpu não instalado. Usando busca flat (mais lenta).")

        # Fallback: memmap flat (não carrega tudo na RAM)
        self._embs = np.memmap(str(emb_path), dtype='float32', mode='r', shape=(n, DIM))
        print(f"[INFO] Embeddings carregados ({n:,} vetores, busca flat)")
        self._embeddings_ok = True
        return True

    # ── Busca BM25 ───────────────────────────────────────────────────────────

    def _busca_bm25(self, query: str, k: int) -> List[Dict]:
        """Busca lexical via FTS5. Retorna lista de {rowid, rank, score_norm}."""
        con = self._get_con()
        cur = con.cursor()

        # FTS5 com BM25 implícito (rank negativo = mais relevante)
        try:
            cur.execute("""
                SELECT d.rowid, rank,
                       d.id, d.classe, d.orgao, d.relator,
                       d.dataDecisao, d.tema, d.ementa_curta, d.tese_curta
                FROM decisoes_fts f
                JOIN decisoes_mini d ON f.rowid = d.rowid
                WHERE f MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, k * 2))
        except sqlite3.OperationalError:
            # Fallback: busca LIKE simples
            palavras = query.split()
            cond = " AND ".join([f"ementa_curta LIKE '%{p}%'" for p in palavras[:3]])
            cur.execute(f"""
                SELECT rowid, -1 as rank,
                       id, classe, orgao, relator,
                       dataDecisao, tema, ementa_curta, tese_curta
                FROM decisoes_mini
                WHERE {cond}
                LIMIT ?
            """, (k * 2,))

        rows = cur.fetchall()
        resultados = []
        for i, r in enumerate(rows):
            resultados.append({
                "rowid":       r[0],
                "rank_bm25":   i + 1,
                "id":          r[2],
                "classe":      r[3] or "",
                "orgao":       r[4] or "",
                "relator":     r[5] or "",
                "dataDecisao": r[6] or "",
                "tema":        r[7],
                "ementa_curta": r[8] or "",
                "tese_curta":  r[9] or "",
            })
        return resultados

    # ── Busca semântica ──────────────────────────────────────────────────────

    def _busca_semantica(self, query: str, k: int) -> List[Dict]:
        """Busca vetorial por similaridade de cosseno. Retorna lista de {rowid, rank_sem}."""
        if not self._carregar_embeddings():
            return []

        model = self._get_model()
        q_emb = model.encode([query], normalize_embeddings=True).astype(np.float32)

        if self._faiss is not None:
            # FAISS: rápido
            distances, faiss_ids = self._faiss.search(q_emb, k * 2)
            rowids = self._ids[faiss_ids[0]]
            sims   = distances[0]
        else:
            # Numpy flat (mais lento mas funciona sem FAISS)
            sims_all = (self._embs @ q_emb.T).flatten()
            top_idx  = np.argsort(-sims_all)[:k * 2]
            rowids   = self._ids[top_idx]
            sims     = sims_all[top_idx]

        # Buscar metadados dos rowids
        con  = self._get_con()
        cur  = con.cursor()
        placeholder = ",".join(["?"] * len(rowids))
        cur.execute(f"""
            SELECT rowid, id, classe, orgao, relator,
                   dataDecisao, tema, ementa_curta, tese_curta
            FROM decisoes_mini
            WHERE rowid IN ({placeholder})
        """, [int(r) for r in rowids])
        meta = {r[0]: r for r in cur.fetchall()}

        resultados = []
        for rank, (rowid, sim) in enumerate(zip(rowids, sims)):
            m = meta.get(int(rowid))
            if not m:
                continue
            resultados.append({
                "rowid":       int(rowid),
                "rank_sem":    rank + 1,
                "sim":         float(sim),
                "id":          m[1],
                "classe":      m[2] or "",
                "orgao":       m[3] or "",
                "relator":     m[4] or "",
                "dataDecisao": m[5] or "",
                "tema":        m[6],
                "ementa_curta": m[7] or "",
                "tese_curta":  m[8] or "",
            })
        return resultados

    # ── RRF Fusion ───────────────────────────────────────────────────────────

    def _rrf_fusion(self, bm25: List[Dict], sem: List[Dict], k: int) -> List[Dict]:
        """
        Reciprocal Rank Fusion: score = Σ (1 / (k_rrf + rank_i))
        weighted: (1-alpha)*bm25 + alpha*semantico
        """
        scores: Dict[int, float] = {}
        meta:   Dict[int, Dict]  = {}

        for r in bm25:
            rowid = r["rowid"]
            scores[rowid] = scores.get(rowid, 0) + \
                (1 - self.alpha) / (self.k_rrf + r["rank_bm25"])
            meta[rowid] = r

        for r in sem:
            rowid = r["rowid"]
            scores[rowid] = scores.get(rowid, 0) + \
                self.alpha / (self.k_rrf + r["rank_sem"])
            if rowid not in meta:
                meta[rowid] = r

        ordenados = sorted(scores.items(), key=lambda x: -x[1])[:k]
        resultado = []
        for rowid, score in ordenados:
            d = dict(meta[rowid])
            d["score"] = round(score, 6)
            resultado.append(d)
        return resultado

    # ── Interface pública ─────────────────────────────────────────────────────

    def buscar(self, query: str, k: int = 15,
               modo: str = "hibrido") -> List[Dict]:
        """
        Busca acórdãos do STJ.

        Args:
            query: consulta em linguagem natural
            k:     número de resultados
            modo:  "hibrido" | "bm25" | "semantico"

        Returns:
            Lista de dicts com: score, id, classe, orgao, relator,
                                dataDecisao, tema, ementa_curta, tese_curta
        """
        if modo == "bm25":
            res = self._busca_bm25(query, k)
            for i, r in enumerate(res[:k]):
                r["score"] = round(1 / (self.k_rrf + i + 1), 6)
            return res[:k]

        elif modo == "semantico":
            res = self._busca_semantica(query, k)
            for i, r in enumerate(res[:k]):
                r["score"] = r.get("sim", 0)
            return res[:k]

        else:  # hibrido
            bm25 = self._busca_bm25(query, k)
            sem  = self._busca_semantica(query, k)
            if not sem:
                # Sem embeddings: usar só BM25
                for i, r in enumerate(bm25[:k]):
                    r["score"] = round(1 / (self.k_rrf + i + 1), 6)
                return bm25[:k]
            return self._rrf_fusion(bm25, sem, k)

    def fechar(self):
        if self._con:
            self._con.close()


# ─── CLI ─────────────────────────────────────────────────────────────────────

def _formatar_data(d: str) -> str:
    if d and len(d) == 8:
        return f"{d[6:8]}/{d[4:6]}/{d[:4]}"
    return d or "—"

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Busca híbrida STJ")
    parser.add_argument("query", nargs="+", help="Consulta em linguagem natural")
    parser.add_argument("--k",     type=int,   default=15,      help="Nº de resultados")
    parser.add_argument("--alpha", type=float, default=0.5,     help="Peso semântico [0-1]")
    parser.add_argument("--modo",  type=str,   default="hibrido",
                        choices=["hibrido", "bm25", "semantico"],
                        help="Modo de busca")
    parser.add_argument("--json",  action="store_true",          help="Output JSON")
    args = parser.parse_args()

    query = " ".join(args.query)
    print(f'\n🔍 Query: "{query}"')
    print(f"   Modo: {args.modo} | alpha={args.alpha} | k={args.k}\n")

    bh = BuscaHibrida(alpha=args.alpha)
    resultados = bh.buscar(query, k=args.k, modo=args.modo)

    if args.json:
        print(json.dumps(resultados, ensure_ascii=False, indent=2))
        return

    print(f"{'#':>3}  {'SCORE':>8}  {'CLASSE':>6}  {'DATA':>10}  RELATOR / EMENTA")
    print("─" * 90)
    for i, r in enumerate(resultados, 1):
        ementa = r["ementa_curta"].replace("\n", " ")[:60]
        tema_s = f" [Tema {r['tema']}]" if r.get("tema") else ""
        print(f"{i:>3}. [{r['score']:.5f}] "
              f"{r['classe']:>6} | {_formatar_data(r['dataDecisao'])} | "
              f"{r['relator'][:20]:<20}")
        print(f"      {ementa}{tema_s}")
        if r.get("tese_curta"):
            print(f"      TESE: {r['tese_curta'][:80]}...")
        print()

    bh.fechar()


if __name__ == "__main__":
    main()
