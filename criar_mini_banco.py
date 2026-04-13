"""
criar_mini_banco.py
===================
Gera o 'stj_mini.db' — banco compacto (~200MB) para uso automatizado pelo Claude.

Por que este banco existe:
  O banco principal (stj_jurisprudencia.db) usa WAL mode, que exige arquivos
  de lock (-shm/-wal) não suportados pelo sistema de arquivos montado no Cowork.
  O stj_mini.db usa journal_mode=DELETE, não gera arquivos auxiliares, e pode
  ser copiado para memória local pelo Claude em ~20-30 segundos — permitindo
  que todas as buscas rodem automaticamente, sem intervenção no PowerShell.

Estratégia de tamanho:
  - Tabela 'decisoes_mini': metadados + ementa (400 chars) + tese (400 chars)
  - FTS5 contentless: indexa o texto COMPLETO para qualidade de busca, mas
    não armazena o texto novamente — evita duplicação e mantém o DB pequeno.

Execute uma vez (ou quando o banco principal for atualizado):
    python criar_mini_banco.py

Tempo estimado: 8 a 15 minutos.
Tamanho esperado: 180 a 250 MB.
"""

import os
import json
import sqlite3
import time
from datetime import datetime

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
DB_FULL     = os.path.join(SCRIPT_DIR, "stj_jurisprudencia.db")
DB_MINI     = os.path.join(SCRIPT_DIR, "stj_mini.db")
ARQUIVOS    = os.path.join(SCRIPT_DIR, "ARQUIVOS STJ")

BATCH_SIZE  = 2000
EMENTA_LEN  = 400   # chars para exibição
TESE_LEN    = 400   # chars para exibição
FTS_EMENTA  = 2500  # chars para indexação FTS5 (qualidade de busca)
FTS_TESE    = 1000  # chars para indexação FTS5


def print_header():
    print(f"\n{'='*60}")
    print(f"  STJ JURIS — Criador do Mini Banco")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{'='*60}\n")


def criar_schema(conn):
    conn.executescript("""
        PRAGMA journal_mode = DELETE;
        PRAGMA synchronous  = NORMAL;
        PRAGMA cache_size   = 20000;
        PRAGMA temp_store   = MEMORY;

        CREATE TABLE IF NOT EXISTS decisoes_mini (
            rowid           INTEGER PRIMARY KEY,
            id              TEXT UNIQUE,
            orgao           TEXT,
            processo        TEXT,
            classe          TEXT,
            descricaoClasse TEXT,
            relator         TEXT,
            tipoDecisao     TEXT,
            dataDecisao     TEXT,
            dataPublicacao  TEXT,
            tema            TEXT,
            ementa_curta    TEXT,
            tese_curta      TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_mini_orgao  ON decisoes_mini(orgao);
        CREATE INDEX IF NOT EXISTS idx_mini_data   ON decisoes_mini(dataDecisao);
        CREATE INDEX IF NOT EXISTS idx_mini_classe ON decisoes_mini(classe);
        CREATE INDEX IF NOT EXISTS idx_mini_id     ON decisoes_mini(id);
    """)


def criar_fts_contentless(conn):
    """
    FTS5 contentless: indexa o texto completo para busca de qualidade,
    mas não armazena o conteúdo (evita duplicação — mantém o DB pequeno).
    A busca retorna rowids que são usados para buscar dados em decisoes_mini.
    """
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS decisoes_fts
        USING fts5(
            ementa,
            teseJuridica,
            tema,
            content="",
            tokenize='unicode61 remove_diacritics 0'
        )
    """)
    conn.commit()


def popular_do_banco_principal(conn):
    """Lê do banco principal e popula o mini banco."""

    if not os.path.exists(DB_FULL):
        raise FileNotFoundError(f"Banco principal não encontrado: {DB_FULL}")

    print("Conectando ao banco principal...")
    src = sqlite3.connect(DB_FULL, timeout=60)
    src.row_factory = sqlite3.Row

    total = src.execute("SELECT COUNT(*) FROM decisoes").fetchone()[0]
    print(f"Total de registros: {total:,}\n")

    t0    = time.time()
    count = 0
    fts_batch_meta = []
    fts_batch_text = []

    offset = 0
    while True:
        rows = src.execute(
            """SELECT rowid, id, orgao, processo, classe, descricaoClasse,
                      relator, tipoDecisao, dataDecisao, dataPublicacao,
                      tema, ementa, teseJuridica
               FROM decisoes
               LIMIT ? OFFSET ?""",
            (BATCH_SIZE, offset)
        ).fetchall()

        if not rows:
            break

        meta_batch = []
        for r in rows:
            meta_batch.append((
                r['id'],
                r['orgao'],
                r['processo'],
                r['classe'],
                r['descricaoClasse'],
                r['relator'],
                r['tipoDecisao'],
                r['dataDecisao'],
                r['dataPublicacao'],
                (r['tema'] or '')[:200],
                (r['ementa'] or '')[:EMENTA_LEN],
                (r['teseJuridica'] or '')[:TESE_LEN],
            ))

        conn.executemany("""
            INSERT OR IGNORE INTO decisoes_mini
            (id, orgao, processo, classe, descricaoClasse, relator,
             tipoDecisao, dataDecisao, dataPublicacao, tema, ementa_curta, tese_curta)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, meta_batch)
        conn.commit()

        count  += len(rows)
        offset += BATCH_SIZE
        elapsed = time.time() - t0
        pct     = count / total * 100
        print(f"  {count:>10,} / {total:,}  ({pct:.1f}%)  —  {elapsed:.0f}s")

    src.close()
    print(f"\n  ✓ Metadados inseridos: {count:,}")
    return count


def popular_fts_dos_jsons(conn):
    """
    Popula o FTS5 contentless lendo os JSONs originais para indexar
    o texto completo (ementa + tese) sem aumentar o DB principal.
    """
    print("\nPopulando índice FTS5 a partir dos JSONs originais...")
    print("(Indexa texto completo para qualidade de busca)\n")

    if not os.path.isdir(ARQUIVOS):
        print("  ⚠️  Pasta 'ARQUIVOS STJ' não encontrada.")
        print("  Usando ementas truncadas do banco principal para o FTS5...")
        _popular_fts_do_banco(conn)
        return

    # Mapa id → rowid no mini banco
    print("  Construindo mapa de IDs...")
    id_map = {}
    for rowid, id_val in conn.execute("SELECT rowid, id FROM decisoes_mini"):
        id_map[id_val] = rowid
    print(f"  {len(id_map):,} IDs mapeados.\n")

    orgaos = sorted([d for d in os.listdir(ARQUIVOS)
                     if os.path.isdir(os.path.join(ARQUIVOS, d))])

    total_fts = 0
    t0 = time.time()

    for orgao in orgaos:
        pasta    = os.path.join(ARQUIVOS, orgao)
        arquivos = sorted([f for f in os.listdir(pasta) if f.endswith('.json')])
        print(f"  {orgao} ({len(arquivos)} arquivos)...", end=" ", flush=True)

        batch = []
        cnt   = 0

        for fname in arquivos:
            fpath = os.path.join(pasta, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for item in data:
                    id_val = item.get("id", "")
                    if id_val not in id_map:
                        continue
                    rowid    = id_map[id_val]
                    ementa   = (item.get("ementa") or "")[:FTS_EMENTA]
                    tese     = (item.get("teseJuridica") or "")[:FTS_TESE]
                    tema     = (item.get("tema") or "")[:300]
                    batch.append((rowid, ementa, tese, tema))
                    if len(batch) >= BATCH_SIZE:
                        conn.executemany(
                            "INSERT INTO decisoes_fts(rowid, ementa, teseJuridica, tema) VALUES (?,?,?,?)",
                            batch
                        )
                        cnt   += len(batch)
                        batch  = []
            except Exception:
                pass

        if batch:
            conn.executemany(
                "INSERT INTO decisoes_fts(rowid, ementa, teseJuridica, tema) VALUES (?,?,?,?)",
                batch
            )
            cnt += len(batch)

        conn.commit()
        total_fts += cnt
        print(f"{cnt:,} OK")

    elapsed = time.time() - t0
    print(f"\n  ✓ FTS5 populado: {total_fts:,} registros em {elapsed:.0f}s")


def _popular_fts_do_banco(conn):
    """Fallback: popula FTS5 a partir das ementas já no mini banco."""
    count = 0
    for rowid, ementa, tese, tema in conn.execute(
        "SELECT rowid, ementa_curta, tese_curta, tema FROM decisoes_mini"
    ):
        conn.execute(
            "INSERT INTO decisoes_fts(rowid, ementa, teseJuridica, tema) VALUES (?,?,?,?)",
            (rowid, ementa or '', tese or '', tema or '')
        )
        count += 1
        if count % 50000 == 0:
            conn.commit()
            print(f"    {count:,}...")
    conn.commit()
    print(f"  ✓ FTS5 populado via fallback: {count:,}")


def otimizar(conn):
    print("\nOtimizando FTS5...")
    conn.execute("INSERT INTO decisoes_fts(decisoes_fts) VALUES('optimize')")
    conn.commit()
    # Garante que não há journal pendente (journal_mode=DELETE, não WAL)
    conn.execute("PRAGMA integrity_check(1)")
    print("  ✓ Otimizado.")


def main():
    print_header()

    if os.path.exists(DB_MINI):
        resp = input(f"'{DB_MINI}' já existe. Recriar? (s/N): ").strip().lower()
        if resp != 's':
            print("Nenhuma alteração feita.")
            return
        os.remove(DB_MINI)
        print("  Banco anterior removido.\n")

    t_inicio = time.time()

    conn = sqlite3.connect(DB_MINI, timeout=300)

    print("Criando schema...")
    criar_schema(conn)
    criar_fts_contentless(conn)
    print("  ✓ Schema criado.\n")

    print("Populando metadados e ementas (do banco principal)...")
    total = popular_do_banco_principal(conn)

    popular_fts_dos_jsons(conn)
    otimizar(conn)

    conn.close()

    elapsed  = time.time() - t_inicio
    mini_mb  = os.path.getsize(DB_MINI) / 1024 / 1024

    print(f"\n{'='*60}")
    print(f"  CONCLUÍDO — {datetime.now().strftime('%H:%M:%S')}")
    print(f"  Registros: {total:,}")
    print(f"  Tamanho:   {mini_mb:.0f} MB")
    print(f"  Tempo:     {elapsed/60:.1f} minutos")
    print(f"\n  O Claude agora pode buscar automaticamente.")
    print(f"  Arquivo: stj_mini.db")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
