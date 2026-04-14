"""
construir_banco_stj.py
Gera o banco SQLite com todas as decisões do STJ a partir dos JSONs locais.

Como usar (no Windows, abra o PowerShell ou Prompt de Comando nesta pasta):
    python construir_banco_stj.py

O arquivo 'stj_jurisprudencia.db' será criado na mesma pasta deste script.
Tempo estimado: 5 a 10 minutos para ~1 milhão de decisões.
"""

import os
import json
import sqlite3
from datetime import datetime

# ── Caminhos (relativos ao script) ───────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR   = os.path.join(SCRIPT_DIR, "ARQUIVOS STJ")
DB_PATH    = os.path.join(SCRIPT_DIR, "stj_jurisprudencia.db")
# ─────────────────────────────────────────────────────────────────────────────

SQL_INSERT = "INSERT OR REPLACE INTO decisoes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"

def setup_db(conn):
    conn.executescript("""
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous  = NORMAL;
        PRAGMA cache_size   = 10000;

        CREATE TABLE IF NOT EXISTS decisoes (
            id              TEXT PRIMARY KEY,
            orgao           TEXT,
            processo        TEXT,
            numeroRegistro  TEXT,
            classe          TEXT,
            descricaoClasse TEXT,
            relator         TEXT,
            tipoDecisao     TEXT,
            dataDecisao     TEXT,
            dataPublicacao  TEXT,
            ementa          TEXT,
            teseJuridica    TEXT,
            tema            TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_orgao    ON decisoes(orgao);
        CREATE INDEX IF NOT EXISTS idx_relator  ON decisoes(relator);
        CREATE INDEX IF NOT EXISTS idx_classe   ON decisoes(classe);
        CREATE INDEX IF NOT EXISTS idx_data     ON decisoes(dataDecisao);
        CREATE INDEX IF NOT EXISTS idx_processo ON decisoes(processo);
    """)

def extrair_linha(item, orgao_pasta):
    return (
        item.get("id", ""),
        item.get("nomeOrgaoJulgador", orgao_pasta),
        item.get("numeroProcesso", ""),
        item.get("numeroRegistro", ""),
        item.get("siglaClasse", ""),
        item.get("descricaoClasse", ""),
        item.get("ministroRelator", ""),
        item.get("tipoDeDecisao", ""),
        item.get("dataDecisao", ""),
        item.get("dataPublicacao", ""),
        (item.get("ementa") or "")[:3000],
        (item.get("teseJuridica") or "")[:1500],
        (item.get("tema") or "")[:500],
    )

def main():
    print(f"\n{'='*58}")
    print(f"  STJ JURISPRUDÊNCIA — Construtor de Banco SQLite")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{'='*58}\n")

    if not os.path.isdir(BASE_DIR):
        print(f"ERRO: Pasta nao encontrada: {BASE_DIR}")
        print("Certifique-se de rodar este script dentro da pasta STJ JURIS.")
        return

    # Remove banco anterior se existir
    if os.path.exists(DB_PATH):
        print(f"Removendo banco anterior...")
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    setup_db(conn)

    orgaos = sorted([d for d in os.listdir(BASE_DIR)
                     if os.path.isdir(os.path.join(BASE_DIR, d))])

    total_inserido = 0
    total_erros    = 0
    BATCH_SIZE     = 500

    for orgao in orgaos:
        pasta    = os.path.join(BASE_DIR, orgao)
        arquivos = sorted([f for f in os.listdir(pasta) if f.endswith('.json')])
        print(f"Processando {orgao} ({len(arquivos)} arquivos)...", end=" ", flush=True)

        batch = []
        cnt   = 0

        for fname in arquivos:
            fpath = os.path.join(pasta, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for item in data:
                    batch.append(extrair_linha(item, orgao))
                    if len(batch) >= BATCH_SIZE:
                        conn.executemany(SQL_INSERT, batch)
                        cnt   += len(batch)
                        batch  = []
            except json.JSONDecodeError:
                total_erros += 1
                print(f"\n  AVISO: JSON invalido ignorado: {fname}")
            except Exception as e:
                total_erros += 1
                print(f"\n  AVISO: Erro em {fname}: {e}")

        if batch:
            conn.executemany(SQL_INSERT, batch)
            cnt += len(batch)

        conn.commit()
        total_inserido += cnt
        print(f"{cnt:,} registros OK  (total: {total_inserido:,})")

    conn.close()

    db_mb = os.path.getsize(DB_PATH) / 1024 / 1024
    print(f"\n{'='*58}")
    print(f"  CONCLUIDO — {datetime.now().strftime('%H:%M:%S')}")
    print(f"  Decisoes indexadas : {total_inserido:,}")
    print(f"  Erros de leitura   : {total_erros}")
    print(f"  Arquivo gerado     : stj_jurisprudencia.db ({db_mb:.0f} MB)")
    print(f"{'='*58}\n")

if __name__ == "__main__":
    main()
