#!/usr/bin/env python3
"""
stj_semantic_indexer.py — Geração de embeddings semânticos para o banco STJ

Indexa os 638k acórdãos do banco FTS5 com embeddings vetoriais,
permitindo busca semântica por conceito jurídico.

Uso (PowerShell/CMD no Windows):
    pip install sentence-transformers faiss-cpu numpy tqdm
    python stj_semantic_indexer.py

O script é RESUMÍVEL: se interrompido, continua de onde parou.

Outputs (em AppData/Local — fora do OneDrive):
    stj_embeddings.bin        — embeddings float32 (raw binary, memmap)
    stj_embeddings_ids.bin    — rowids int64 (raw binary, memmap)
    stj_embeddings_meta.json  — metadados (modelo, dimensão, progresso)
    stj_index.faiss           — índice FAISS IVFPQ para busca rápida

Tempo estimado (CPU, sem GPU):
    - 638k docs × batch 128 → ~10-14 horas
    - Progresso salvo a cada 5.000 registros
"""

import os, sys, json, time, sqlite3, shutil
import numpy as np
from pathlib import Path
from datetime import datetime

# ─── CONFIG ──────────────────────────────────────────────────────────────────

STJ_DB  = Path(r"C:\Users\tomaz\OneDrive\Área de Trabalho\STJ JURIS\stj_mini.db")

# Fora do OneDrive → sem interferência de sync no disco
OUT_DIR = Path(r"C:\Users\tomaz\AppData\Local\STJ_embeddings")

MODELO           = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DIM              = 384
BATCH            = 128
CHECKPOINT_CADA  = 5_000   # flush memmap + salvar meta a cada N registros

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def texto_para_emb(row: tuple) -> str:
    _, classe, ementa, tese, tema = row
    partes = []
    if classe:  partes.append(classe.strip())
    if ementa:  partes.append(ementa.strip()[:600])
    if tese:    partes.append(tese.strip()[:400])
    if tema:    partes.append(f"Tema {tema}".strip())
    return " | ".join(partes) if partes else ""


def carregar_progresso(meta_path: Path):
    """Retorna (ultimo_rowid, total_indexado)."""
    if meta_path.exists():
        with open(meta_path) as f:
            meta = json.load(f)
        ultimo = meta.get("ultimo_rowid", 0)
        total  = meta.get("total_indexado", 0)
        print(f"[RETOMANDO] {total:,} registros já indexados, último rowid={ultimo}")
        return ultimo, total
    return 0, 0


def salvar_progresso(meta_path: Path, ultimo_rowid: int, total: int):
    with open(meta_path, 'w') as f:
        json.dump({
            "modelo": MODELO,
            "dim": DIM,
            "ultimo_rowid": ultimo_rowid,
            "total_indexado": total,
            "atualizado": datetime.now().isoformat(),
        }, f, indent=2, ensure_ascii=False)


def checar_espaco(path: Path, necessario_mb: float):
    _, _, livre = shutil.disk_usage(str(path.drive) + "/")
    livre_mb = livre / 1e6
    # Aviso suave se espaço baixo mas ainda suficiente (margem de 50MB)
    if livre_mb < necessario_mb - 50:
        print(f"\n[AVISO] Espaço em disco: {livre_mb:.0f}MB livres (ideal: {necessario_mb:.0f}MB)")
        if livre_mb < 50:
            print(f"[ERRO] Menos de 50MB livres — abortando para evitar corrupção.")
            sys.exit(1)
    else:
        print(f"Espaço em disco: {livre_mb:.0f}MB livres (necessário ~{necessario_mb:.0f}MB) OK\n")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    emb_path  = OUT_DIR / "stj_embeddings.bin"
    ids_path  = OUT_DIR / "stj_embeddings_ids.bin"
    meta_path = OUT_DIR / "stj_embeddings_meta.json"
    idx_path  = OUT_DIR / "stj_index.faiss"

    print("=" * 60)
    print("STJ Semantic Indexer")
    print("=" * 60)
    print(f"Banco:    {STJ_DB}")
    print(f"Output:   {OUT_DIR}")
    print(f"Modelo:   {MODELO}")
    print()

    # ── Verificar espaço (apenas o que ainda falta gerar) ─────────────────────
    emb_ja_gerado = emb_path.stat().st_size if emb_path.exists() else 0
    emb_total     = 638_198 * DIM * 4
    emb_restante  = max(0, emb_total - emb_ja_gerado)
    necessario_mb = (emb_restante / 1e6) + 150  # +150MB para FAISS + margem
    checar_espaco(OUT_DIR, necessario_mb=necessario_mb)

    # ── Imports pesados ───────────────────────────────────────────────────────
    print("Carregando modelo de embeddings...")
    from sentence_transformers import SentenceTransformer
    modelo = SentenceTransformer(MODELO)
    print("Modelo OK.\n")

    # ── Conectar ao banco ─────────────────────────────────────────────────────
    con = sqlite3.connect(str(STJ_DB), timeout=30)
    con.execute("PRAGMA journal_mode=OFF")
    con.execute("PRAGMA synchronous=OFF")
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) FROM decisoes_mini")
    total_db = cur.fetchone()[0]
    print(f"Banco: {total_db:,} acórdãos\n")

    # ── Retomar progresso ─────────────────────────────────────────────────────
    ultimo_rowid, total_indexado = carregar_progresso(meta_path)

    # Determinar offset a partir do arquivo existente (mais confiável que meta)
    if emb_path.exists():
        offset = emb_path.stat().st_size // (DIM * 4)
        if offset != total_indexado:
            print(f"  [AVISO] Meta={total_indexado:,} mas arquivo={offset:,} vetores — usando arquivo.")
        total_indexado = offset
    else:
        offset = 0

    # ── Abrir/criar arquivos memmap de escrita direta ─────────────────────────
    # mode='r+b' se existe, 'w+b' se novo
    emb_mode = 'r+b' if emb_path.exists() and offset > 0 else 'w+b'
    ids_mode = 'r+b' if ids_path.exists() and offset > 0 else 'w+b'

    emb_file = open(str(emb_path), emb_mode)
    ids_file = open(str(ids_path), ids_mode)

    # Posicionar no final para continuar
    emb_file.seek(0, 2)
    ids_file.seek(0, 2)

    print(f"Iniciando a partir do rowid {ultimo_rowid + 1} (offset={offset:,})...\n")

    # ── Processar ─────────────────────────────────────────────────────────────
    query = """
        SELECT rowid, classe, ementa_curta, tese_curta, tema
        FROM decisoes_mini
        WHERE rowid > ?
        ORDER BY rowid
    """

    try:
        from tqdm import tqdm
    except ImportError:
        tqdm = None

    cur.execute(query, (ultimo_rowid,))
    restantes   = total_db - offset
    pbar        = tqdm(total=restantes, unit="doc") if tqdm else None
    t0                  = time.time()
    processados         = 0
    ultimo_id           = ultimo_rowid
    _proximo_checkpoint = CHECKPOINT_CADA

    try:
        while True:
            rows = cur.fetchmany(BATCH)
            if not rows:
                break

            textos = [texto_para_emb(r) for r in rows]
            ids    = [r[0] for r in rows]

            validos = [(t, i) for t, i in zip(textos, ids) if t.strip()]
            if not validos:
                continue
            textos_v, ids_v = zip(*validos)

            embs = modelo.encode(
                list(textos_v),
                batch_size=32,
                show_progress_bar=False,
                normalize_embeddings=True,
            )

            # Escrever direto no arquivo — sem acumular na RAM
            emb_file.write(np.array(embs, dtype=np.float32).tobytes())
            ids_file.write(np.array(ids_v, dtype=np.int64).tobytes())

            n            = len(ids_v)
            processados += n
            offset      += n
            ultimo_id    = ids_v[-1]

            if pbar:
                pbar.update(n)

            # Checkpoint: flush + meta (sem re-escrever embeddings)
            if processados >= _proximo_checkpoint:
                emb_file.flush()
                ids_file.flush()
                salvar_progresso(meta_path, int(ultimo_id), offset)

                elapsed = time.time() - t0
                vel     = processados / elapsed
                eta_h   = (restantes - processados) / vel / 3600 if vel > 0 else 0
                _, _, livre = shutil.disk_usage(str(OUT_DIR.drive) + "/")
                print(f"\n[{offset:,}/{total_db:,}] vel={vel:.0f} doc/s | "
                      f"ETA~{eta_h:.1f}h | disco livre: {livre/1e6:.0f}MB")
                _proximo_checkpoint = processados + CHECKPOINT_CADA

    finally:
        emb_file.flush()
        ids_file.flush()
        emb_file.close()
        ids_file.close()
        if pbar:
            pbar.close()

    salvar_progresso(meta_path, int(ultimo_id), offset)
    print(f"\nEmbeddings gerados: {offset:,} documentos")
    print(f"Tempo total: {(time.time()-t0)/3600:.1f}h")

    # ── Construir índice FAISS ────────────────────────────────────────────────
    print("\nConstruindo índice FAISS IVFPQ...")
    _construir_faiss(emb_path, idx_path, offset, DIM)

    print(f"\nIndexação completa!")
    print(f"  Embeddings: {emb_path}")
    print(f"  IDs:        {ids_path}")
    print(f"  Índice:     {idx_path}")
    print(f"\nPróximo passo: python stj_busca_hibrida.py \"penhorabilidade bem de família\"")

    con.close()


def _construir_faiss(emb_path: Path, idx_path: Path, n: int, dim: int):
    try:
        import faiss
    except ImportError:
        print("faiss-cpu não instalado — pulando índice FAISS.")
        return

    # Lê embeddings via memmap — sem carregar tudo na RAM de uma vez
    mat = np.memmap(str(emb_path), dtype='float32', mode='r', shape=(n, dim))

    nlist = min(256, max(64, n // 1000))
    m     = 48   # 384/48=8 → divisão exata; menor que 96 para economizar RAM

    quantizer = faiss.IndexFlatIP(dim)
    index     = faiss.IndexIVFPQ(quantizer, dim, nlist, m, 8)

    print(f"  Treinando com {min(n, 50_000):,} amostras...")
    train_data = np.array(mat[:50_000]) if n > 50_000 else np.array(mat)
    index.train(train_data)

    print(f"  Adicionando {n:,} vetores...")
    # Adiciona em blocos para não explodir a RAM
    bloco = 50_000
    for i in range(0, n, bloco):
        index.add(np.array(mat[i:i+bloco]))

    faiss.write_index(index, str(idx_path))
    size_mb = idx_path.stat().st_size / 1e6
    print(f"  Índice salvo: {idx_path.name} ({size_mb:.0f}MB)")


if __name__ == "__main__":
    main()
