#!/usr/bin/env python3
"""
stj_dedup_embeddings.py — Remove vetores duplicados do arquivo de embeddings STJ (IN-PLACE)

Estratégia sem cópia extra:
  - Como os índices únicos são mantidos em ordem crescente, sempre escrevemos
    em posições <= posição de leitura → compactação in-place segura.
  - Requer apenas ~5MB extras (para os IDs na RAM), não ~1GB de cópia.

Passos:
  1. Lê stj_embeddings_ids.bin → encontra índices únicos (última ocorrência)
  2. Compacta stj_embeddings.bin e stj_embeddings_ids.bin in-place
  3. Trunca os arquivos no novo tamanho
  4. Atualiza stj_embeddings_meta.json
  5. Reconstrói índice FAISS

Uso:
    python stj_dedup_embeddings.py
"""

import os, sys, json, shutil, time
import numpy as np
from pathlib import Path
from datetime import datetime

# ─── CONFIG ──────────────────────────────────────────────────────────────────
OUT_DIR   = Path(r"C:\Users\tomaz\AppData\Local\STJ_embeddings")
DIM       = 384
EMB_BYTES = DIM * 4        # bytes por vetor float32
ID_BYTES  = 8              # bytes por id int64
BLOCO     = 10_000         # vetores por bloco de leitura/escrita

emb_path  = OUT_DIR / "stj_embeddings.bin"
ids_path  = OUT_DIR / "stj_embeddings_ids.bin"
meta_path = OUT_DIR / "stj_embeddings_meta.json"
idx_path  = OUT_DIR / "stj_index.faiss"

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    t0 = time.time()
    print("=" * 60)
    print("STJ Deduplicador de Embeddings (in-place)")
    print("=" * 60)

    for p in [emb_path, ids_path]:
        if not p.exists():
            print(f"[ERRO] Arquivo não encontrado: {p}")
            sys.exit(1)

    n_emb = emb_path.stat().st_size // EMB_BYTES
    n_ids = ids_path.stat().st_size // ID_BYTES
    print(f"Vetores no arquivo de embeddings : {n_emb:,}")
    print(f"IDs no arquivo de IDs            : {n_ids:,}")

    n = min(n_emb, n_ids)
    if n_emb != n_ids:
        print(f"[AVISO] Contagens divergem — usando n={n:,}")

    # ── Carregar IDs (apenas ~5MB) ────────────────────────────────────────────
    print(f"\nCarregando {n:,} IDs na RAM...")
    with open(ids_path, 'rb') as f:
        ids = np.frombuffer(f.read(n * ID_BYTES), dtype=np.int64).copy()
    print(f"  IDs: min={ids.min()}, max={ids.max()}")

    # ── Encontrar índices únicos (manter ÚLTIMA ocorrência de cada ID) ────────
    print("Identificando duplicatas...")
    ids_rev = ids[::-1]
    _, idx_unicos_rev = np.unique(ids_rev, return_index=True)
    idx_unicos = np.sort(n - 1 - idx_unicos_rev)   # posições no array original, ordenadas

    n_unico   = len(idx_unicos)
    n_dup     = n - n_unico
    print(f"  Total    : {n:,}")
    print(f"  Únicos   : {n_unico:,}")
    print(f"  Removidos: {n_dup:,}")

    if n_dup == 0:
        print("\nNenhuma duplicata — nada a fazer.")
        _construir_faiss(emb_path, idx_path, n, DIM)
        return

    # ── Compactação in-place ──────────────────────────────────────────────────
    # Como idx_unicos está ordenado e sempre idx_unicos[j] >= j,
    # nunca sobrescrevemos dados ainda não lidos.
    print(f"\nCompactando in-place ({n_unico:,} vetores)...")

    f_emb = open(str(emb_path), 'r+b')
    f_ids = open(str(ids_path), 'r+b')

    write_pos = 0
    for bloco_inicio in range(0, n_unico, BLOCO):
        bloco_idx = idx_unicos[bloco_inicio : bloco_inicio + BLOCO]

        # Ler embeddings nas posições de origem (podem não ser contíguas → loop)
        emb_chunks = []
        ids_chunks = []
        for src_idx in bloco_idx:
            f_emb.seek(src_idx * EMB_BYTES)
            emb_chunks.append(f_emb.read(EMB_BYTES))
            f_ids.seek(src_idx * ID_BYTES)
            ids_chunks.append(f_ids.read(ID_BYTES))

        # Escrever contiguamente na posição de destino
        f_emb.seek(write_pos * EMB_BYTES)
        f_emb.write(b''.join(emb_chunks))
        f_ids.seek(write_pos * ID_BYTES)
        f_ids.write(b''.join(ids_chunks))

        write_pos += len(bloco_idx)
        pct = write_pos / n_unico * 100
        print(f"  [{write_pos:,}/{n_unico:,}] {pct:.1f}%", end='\r')

    print(f"\n  Compactação concluída.")

    # ── Truncar arquivos no novo tamanho ──────────────────────────────────────
    f_emb.truncate(n_unico * EMB_BYTES)
    f_ids.truncate(n_unico * ID_BYTES)
    f_emb.close()
    f_ids.close()
    print(f"  Arquivos truncados para {n_unico:,} vetores.")

    # ── Verificar integridade ─────────────────────────────────────────────────
    n_check = emb_path.stat().st_size // EMB_BYTES
    assert n_check == n_unico, f"Erro: esperado {n_unico}, tamanho={n_check}"
    print(f"  Verificação OK: {n_check:,} vetores únicos.")

    # ── Atualizar metadados ───────────────────────────────────────────────────
    with open(ids_path, 'rb') as f:
        last_id = int(np.frombuffer(f.read()[-ID_BYTES:], dtype=np.int64)[0])
    with open(meta_path, 'w') as f:
        json.dump({
            "modelo": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            "dim": DIM,
            "ultimo_rowid": last_id,
            "total_indexado": n_unico,
            "atualizado": datetime.now().isoformat(),
            "deduplicado": True,
            "duplicatas_removidas": int(n_dup),
        }, f, indent=2, ensure_ascii=False)
    print(f"  Metadados atualizados (último rowid={last_id:,})")

    # ── Reconstruir FAISS ─────────────────────────────────────────────────────
    print(f"\nReconstruindo índice FAISS com {n_unico:,} vetores únicos...")
    _construir_faiss(emb_path, idx_path, n_unico, DIM)

    elapsed = (time.time() - t0) / 60
    print(f"\n{'='*60}")
    print(f"Deduplicação concluída em {elapsed:.1f} minutos.")
    print(f"  Vetores antes : {n:,}")
    print(f"  Vetores depois: {n_unico:,}")
    print(f"  Removidos     : {n_dup:,}")
    print(f"  FAISS         : {idx_path}")
    print(f"{'='*60}")


def _construir_faiss(emb_path: Path, idx_path: Path, n: int, dim: int):
    try:
        import faiss
    except ImportError:
        print("[ERRO] faiss-cpu não instalado. Rode: pip install faiss-cpu")
        return

    if idx_path.exists():
        idx_path.unlink()
        print("  Índice FAISS anterior removido.")

    mat = np.memmap(str(emb_path), dtype='float32', mode='r', shape=(n, dim))

    nlist     = min(256, max(64, n // 1000))
    m         = 48
    quantizer = faiss.IndexFlatIP(dim)
    index     = faiss.IndexIVFPQ(quantizer, dim, nlist, m, 8)

    n_treino = min(n, 50_000)
    print(f"  Treinando com {n_treino:,} amostras...")
    index.train(np.array(mat[:n_treino]))

    print(f"  Adicionando {n:,} vetores em blocos...")
    BLOCO_F = 50_000
    for i in range(0, n, BLOCO_F):
        index.add(np.array(mat[i:i+BLOCO_F]))
        print(f"    {min(i+BLOCO_F,n):,}/{n:,}", end='\r')

    faiss.write_index(index, str(idx_path))
    size_mb = idx_path.stat().st_size / 1e6
    print(f"\n  Índice salvo: {idx_path.name} ({size_mb:.0f}MB)")


if __name__ == "__main__":
    main()
