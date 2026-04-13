"""
atualizar_banco_stj.py
Atualiza o banco SQLite com os arquivos JSON novos (baixados mensalmente).

Como usar:
1. Baixe os novos arquivos JSON do portal e coloque nas pastas em ARQUIVOS STJ
2. Abra o PowerShell nesta pasta e execute:
       python atualizar_banco_stj.py

O script verifica quais arquivos já foram processados e insere apenas os novos.
"""

import os
import json
import sqlite3
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR   = os.path.join(SCRIPT_DIR, "ARQUIVOS STJ")
DB_PATH    = os.path.join(SCRIPT_DIR, "stj_jurisprudencia.db")
LOG_PATH   = os.path.join(SCRIPT_DIR, "arquivos_processados.txt")

SQL_INSERT = "INSERT OR REPLACE INTO decisoes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"

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

def carregar_log():
    if not os.path.exists(LOG_PATH):
        return set()
    with open(LOG_PATH, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip())

def salvar_log(processados):
    with open(LOG_PATH, 'w', encoding='utf-8') as f:
        for p in sorted(processados):
            f.write(p + "\n")

def main():
    print(f"\n{'='*58}")
    print(f"  STJ JURISPRUDÊNCIA — Atualizador Incremental")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{'='*58}\n")

    if not os.path.exists(DB_PATH):
        print("ERRO: Banco nao encontrado. Execute primeiro o construir_banco_stj.py")
        return

    ja_processados = carregar_log()
    print(f"Arquivos ja processados anteriormente: {len(ja_processados)}\n")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous  = NORMAL")

    orgaos = sorted([d for d in os.listdir(BASE_DIR)
                     if os.path.isdir(os.path.join(BASE_DIR, d))])

    total_novos = 0
    total_erros = 0
    novos_processados = set()
    BATCH_SIZE = 500

    for orgao in orgaos:
        pasta    = os.path.join(BASE_DIR, orgao)
        arquivos = sorted([f for f in os.listdir(pasta) if f.endswith('.json')])

        # Filtra só os arquivos novos
        novos = [f for f in arquivos
                 if os.path.join(orgao, f) not in ja_processados]

        if not novos:
            print(f"  {orgao}: sem arquivos novos")
            continue

        print(f"Processando {orgao}: {len(novos)} arquivo(s) novo(s)...", end=" ", flush=True)
        batch = []
        cnt   = 0

        for fname in novos:
            fpath = os.path.join(pasta, fname)
            chave = os.path.join(orgao, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for item in data:
                    batch.append(extrair_linha(item, orgao))
                    if len(batch) >= BATCH_SIZE:
                        conn.executemany(SQL_INSERT, batch)
                        cnt   += len(batch)
                        batch  = []
                novos_processados.add(chave)
            except json.JSONDecodeError:
                total_erros += 1
                print(f"\n  AVISO: JSON invalido: {fname}")
            except Exception as e:
                total_erros += 1
                print(f"\n  AVISO: Erro em {fname}: {e}")

        if batch:
            conn.executemany(SQL_INSERT, batch)
            cnt += len(batch)

        conn.commit()
        total_novos += cnt
        print(f"{cnt:,} registros inseridos")

    conn.close()

    # Atualiza log
    todos = ja_processados | novos_processados
    salvar_log(todos)

    print(f"\n{'='*58}")
    print(f"  ATUALIZACAO CONCLUIDA — {datetime.now().strftime('%H:%M:%S')}")
    print(f"  Novos registros inseridos : {total_novos:,}")
    print(f"  Erros                     : {total_erros}")
    print(f"  Total arquivos no log     : {len(todos)}")
    print(f"{'='*58}\n")

if __name__ == "__main__":
    main()
