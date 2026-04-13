"""
setup_fts.py
============
Cria o índice FTS5 (Full-Text Search) no banco stj_jurisprudencia.db,
habilitando buscas de texto rápidas com operadores booleanos e ranking BM25.

Execute UMA VEZ antes de usar buscar_stj.py:
    python setup_fts.py

Tempo estimado: 5 a 20 minutos dependendo do tamanho do banco.
O processo é seguro — não altera a tabela `decisoes` original.
"""

import os
import sqlite3
import time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(SCRIPT_DIR, "stj_jurisprudencia.db")


def print_header():
    print(f"\n{'='*60}")
    print(f"  STJ JURISPRUDÊNCIA — Setup FTS5")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{'='*60}\n")


def fts_ja_existe(conn):
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='decisoes_fts'"
    )
    return cur.fetchone() is not None


def criar_fts(conn):
    """
    Cria tabela virtual FTS5 com conteúdo espelhado de `decisoes`.
    Indexa: ementa, teseJuridica, tema.
    Usa tokenizador unicode61 para lidar corretamente com acentos (português).
    """
    print("Criando tabela virtual FTS5...")
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS decisoes_fts
        USING fts5(
            ementa,
            teseJuridica,
            tema,
            content='decisoes',
            content_rowid='rowid',
            tokenize='unicode61 remove_diacritics 0'
        )
    """)
    conn.commit()
    print("  ✓ Estrutura FTS5 criada.\n")


def popular_fts(conn):
    """
    Popula o índice FTS5 com todos os registros da tabela `decisoes`.
    Esta etapa pode demorar vários minutos em bases grandes.
    """
    print("Populando índice FTS5 (isso pode demorar)...")
    print("  Aguarde — progresso a cada 100.000 registros.\n")

    t0 = time.time()

    # Conta total para estimar progresso
    total = conn.execute("SELECT COUNT(*) FROM decisoes").fetchone()[0]
    print(f"  Total de decisões no banco: {total:,}\n")

    # Insere em lotes usando INSERT SELECT para eficiência
    BATCH = 100_000
    offset = 0
    inseridos = 0

    while True:
        rows = conn.execute(
            """SELECT rowid, ementa, teseJuridica, tema
               FROM decisoes
               LIMIT ? OFFSET ?""",
            (BATCH, offset)
        ).fetchall()

        if not rows:
            break

        conn.executemany(
            "INSERT INTO decisoes_fts(rowid, ementa, teseJuridica, tema) VALUES (?,?,?,?)",
            rows
        )
        conn.commit()

        inseridos += len(rows)
        offset    += BATCH
        elapsed    = time.time() - t0
        pct        = (inseridos / total * 100) if total else 0
        print(f"  {inseridos:>10,} / {total:,}  ({pct:.1f}%)  —  {elapsed:.0f}s")

    conn.commit()
    return inseridos


def otimizar(conn):
    print("\nOtimizando índice FTS5 (merge de segmentos)...")
    conn.execute("INSERT INTO decisoes_fts(decisoes_fts) VALUES('optimize')")
    conn.commit()
    print("  ✓ Otimização concluída.")


def main():
    print_header()

    if not os.path.exists(DB_PATH):
        print(f"ERRO: Banco não encontrado em:\n  {DB_PATH}")
        print("Execute primeiro: python construir_banco_stj.py")
        return

    db_mb = os.path.getsize(DB_PATH) / 1024 / 1024
    print(f"Banco encontrado: stj_jurisprudencia.db ({db_mb:.0f} MB)\n")

    conn = sqlite3.connect(DB_PATH, timeout=300)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous  = NORMAL")
    conn.execute("PRAGMA cache_size   = 20000")
    conn.execute("PRAGMA temp_store   = MEMORY")

    if fts_ja_existe(conn):
        print("Índice FTS5 já existe.")
        resp = input("Deseja recriar do zero? (s/N): ").strip().lower()
        if resp != 's':
            print("Nenhuma alteração feita.")
            conn.close()
            return
        print("\nRemovendo índice anterior...")
        conn.execute("DROP TABLE IF EXISTS decisoes_fts")
        conn.commit()

    t_inicio = time.time()

    criar_fts(conn)
    inseridos = popular_fts(conn)
    otimizar(conn)

    conn.close()

    elapsed = time.time() - t_inicio
    db_mb_final = os.path.getsize(DB_PATH) / 1024 / 1024

    print(f"\n{'='*60}")
    print(f"  SETUP CONCLUÍDO — {datetime.now().strftime('%H:%M:%S')}")
    print(f"  Registros indexados : {inseridos:,}")
    print(f"  Tempo total         : {elapsed/60:.1f} minutos")
    print(f"  Tamanho final do DB : {db_mb_final:.0f} MB")
    print(f"  Próximo passo       : python buscar_stj.py \"seu termo aqui\"")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
