"""
buscar_stj.py
=============
Motor de busca de jurisprudência do STJ com ranking automático pelo
sistema de precedentes judiciais brasileiros.

Uso direto (CLI):
    python buscar_stj.py "impenhorabilidade penhora salário"
    python buscar_stj.py "responsabilidade civil dano moral" --max 8
    python buscar_stj.py "prescrição tributária" --orgao "PRIMEIRA SEÇÃO"
    python buscar_stj.py "alienação fiduciária busca apreensão" --json

Uso como módulo (para integração com Reflexum):
    from buscar_stj import buscar_precedentes, formatar_para_reflexum
    resultados = buscar_precedentes(conn, "impenhorabilidade penhora", max_resultados=10)
    texto = formatar_para_reflexum(resultados)

Saída ranqueada por:
  1. Precedentes obrigatórios: repetitivos (Temas), IAC, uniformização
  2. Órgão julgador: Corte Especial > Seção > Turma > Monocrática
  3. Recência: decisões mais recentes têm maior peso
  4. Qualidade: teseJuridica preenchida, acórdão colegiado
  5. Relevância FTS5 (BM25) quando índice disponível
"""

import os
import re
import sys
import json
import shutil
import sqlite3
import argparse
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(SCRIPT_DIR, "stj_jurisprudencia.db")
DB_MINI    = os.path.join(SCRIPT_DIR, "stj_mini.db")
DB_TMP     = "/tmp/stj_mini.db"   # cópia local usada pelo sandbox


def resolver_banco(db_path_override=None):
    """
    Resolve qual banco usar e garante que está acessível localmente.

    Prioridade:
      1. --db explícito na CLI
      2. stj_mini.db copiado para /tmp (automático, sem restrição FUSE)
      3. stj_jurisprudencia.db (fallback, pode falhar no sandbox)
    """
    if db_path_override:
        return db_path_override

    mini_fonte = DB_MINI

    # Se já existe em /tmp e é recente (< 8h), reutiliza
    if os.path.exists(DB_TMP):
        idade_h = (os.path.getmtime(DB_TMP) - 0)  # placeholder
        import time
        idade_h = (time.time() - os.path.getmtime(DB_TMP)) / 3600
        if idade_h < 8:
            return DB_TMP

    # Tenta copiar o mini banco para /tmp
    if os.path.exists(mini_fonte):
        print("Copiando banco de busca para memória local... ", end="", flush=True)
        try:
            shutil.copy2(mini_fonte, DB_TMP)
            mb = os.path.getsize(DB_TMP) / 1024 / 1024
            print(f"OK ({mb:.0f} MB)")
            return DB_TMP
        except Exception as e:
            print(f"falhou ({e})")

    # Fallback: banco principal (pode falhar no sandbox)
    return DB_PATH

# ─── Constantes de pontuação ──────────────────────────────────────────────────

PONTOS = {
    # Tipo de precedente
    "repetitivo_tema":    1000,   # Tema repetitivo STJ (mais alto)
    "iac":                 900,   # Incidente de Assunção de Competência
    "corte_especial":      600,   # Corte Especial
    "secao":               450,   # 1ª, 2ª ou 3ª Seção
    "turma":               200,   # Turmas (1ª a 6ª)
    "monogratica":           0,   # Decisão monocrática

    # Qualidade do registro
    "tem_tese_juridica":   200,   # teseJuridica preenchida
    "tem_tema":            150,   # campo tema preenchido
    "acordao_colegiado":   100,   # tipoDecisao = ACÓRDÃO

    # Recência
    "ano_2023_mais":       300,
    "ano_2020_2022":       200,
    "ano_2015_2019":       100,
    "ano_2010_2014":        50,
    "antes_2010":            0,
}

# ─── Padrões para identificar precedentes obrigatórios ───────────────────────

PADROES_REPETITIVO = [
    r'\bTEMA\s+\d+\b',
    r'\bRECURSO\s+REPETITIVO\b',
    r'\bREPETITIVO\b',
    r'\bAFETA[ÇC][ÃA]O\b',
    r'\bJULGAMENTO\s+REPETITIVO\b',
    r'\bSISTEMA\s+DE\s+PRECEDENTES\b',
    r'\bTESE\s+FIRMADA\b',
]

PADROES_IAC = [
    r'\bIAC\b',
    r'\bINCIDENTE\s+DE\s+ASSUN[ÇC][ÃA]O\s+DE\s+COMPET[EÊ]NCIA\b',
    r'\bUNIFORM\s*IZA[ÇC][ÃA]O\s+DE\s+JURISPRUD[EÊ]NCIA\b',
]

ORGAOS_CORTE_ESPECIAL = ['CORTE ESPECIAL']
ORGAOS_SECAO = ['1ª SEÇÃO', '2ª SEÇÃO', '3ª SEÇÃO',
                 'PRIMEIRA SEÇÃO', 'SEGUNDA SEÇÃO', 'TERCEIRA SEÇÃO',
                 '1A SEÇÃO', '2A SEÇÃO', '3A SEÇÃO']


# ─── Funções de conexão ───────────────────────────────────────────────────────

def conectar(db_path=None):
    path = db_path or resolver_banco()
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Banco não encontrado: {path}\n"
            "Execute: python criar_mini_banco.py"
        )
    conn = sqlite3.connect(path, timeout=120)
    conn.row_factory = sqlite3.Row
    # Não usa WAL para compatibilidade com cópias locais
    conn.execute("PRAGMA query_only  = ON")
    conn.execute("PRAGMA cache_size  = 15000")
    return conn


def _e_mini_banco(conn):
    """Verifica se está usando o mini banco (tabela decisoes_mini)."""
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='decisoes_mini'"
    )
    return cur.fetchone() is not None


def fts_disponivel(conn):
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='decisoes_fts'"
    )
    return cur.fetchone() is not None


# ─── Construção da query FTS5 ─────────────────────────────────────────────────

def construir_query_fts(termos_raw):
    """
    Converte string de entrada para query FTS5 válida.

    Regras:
    - Termos entre aspas → frase exata
    - Múltiplos termos → todos obrigatórios (AND semântico do FTS5)
    - Remove stopwords jurídicas muito genéricas
    - Exemplo: 'impenhorabilidade penhora' → '"impenhorabilidade" AND "penhora"'
    """
    # Se já parece uma query FTS5 estruturada, retornar como está
    if ' AND ' in termos_raw or ' OR ' in termos_raw or ' NOT ' in termos_raw:
        return termos_raw

    # Extrair frases entre aspas
    frases = re.findall(r'"([^"]+)"', termos_raw)
    resto  = re.sub(r'"[^"]+"', '', termos_raw)

    # Tokenizar palavras individuais (mínimo 3 chars para evitar ruído)
    palavras = [p.strip() for p in resto.split() if len(p.strip()) >= 3]

    partes = []
    for frase in frases:
        partes.append(f'"{frase}"')
    for palavra in palavras:
        partes.append(f'"{palavra}"')

    if not partes:
        return termos_raw  # fallback

    return ' AND '.join(partes)


# ─── Scoring / Ranqueamento ───────────────────────────────────────────────────

def calcular_score(row, fts_rank=0.0):
    """
    Calcula pontuação composta para ranqueamento.
    Quanto maior o score, mais prioritário o precedente.
    """
    score = 0
    orgao      = (row['orgao'] or '').upper()
    tipo       = (row['tipoDecisao'] or '').upper()
    ementa     = (row['ementa'] or '').upper()
    tese       = (row['teseJuridica'] or '')
    tema_val   = (row['tema'] or '')
    data_str   = (row['dataDecisao'] or '')

    # ── 1. Tipo de precedente ─────────────────────────────────────────────────

    # Repetitivo: campo tema preenchido OU padrões na ementa/tipoDecisao
    eh_repetitivo = bool(tema_val.strip())
    if not eh_repetitivo:
        texto_check = ementa + ' ' + tipo
        eh_repetitivo = any(
            re.search(p, texto_check, re.IGNORECASE) for p in PADROES_REPETITIVO
        )

    # IAC
    eh_iac = any(
        re.search(p, ementa + ' ' + tipo, re.IGNORECASE) for p in PADROES_IAC
    )

    if eh_repetitivo:
        score += PONTOS['repetitivo_tema']
    elif eh_iac:
        score += PONTOS['iac']

    # ── 2. Órgão julgador ─────────────────────────────────────────────────────
    if any(o in orgao for o in ORGAOS_CORTE_ESPECIAL):
        score += PONTOS['corte_especial']
    elif any(o in orgao for o in [s.upper() for s in ORGAOS_SECAO]):
        score += PONTOS['secao']
    else:
        score += PONTOS['turma']

    # ── 3. Tipo de decisão ────────────────────────────────────────────────────
    if 'ACÓRDÃO' in tipo or 'ACORDAO' in tipo:
        score += PONTOS['acordao_colegiado']

    # ── 4. Qualidade do registro ──────────────────────────────────────────────
    if tese.strip():
        score += PONTOS['tem_tese_juridica']
    if tema_val.strip():
        score += PONTOS['tem_tema']

    # ── 5. Recência ───────────────────────────────────────────────────────────
    try:
        # dataDecisao pode estar em formatos variados: YYYYMMDD, YYYY-MM-DD, DD/MM/YYYY
        data_clean = re.sub(r'[^0-9]', '', data_str)
        if len(data_clean) >= 8:
            ano = int(data_clean[:4])
            if ano >= 2023:
                score += PONTOS['ano_2023_mais']
            elif ano >= 2020:
                score += PONTOS['ano_2020_2022']
            elif ano >= 2015:
                score += PONTOS['ano_2015_2019']
            elif ano >= 2010:
                score += PONTOS['ano_2010_2014']
    except (ValueError, IndexError):
        pass

    # ── 6. Relevância FTS5 ────────────────────────────────────────────────────
    # fts_rank é negativo no SQLite FTS5 (menor = mais relevante), invertemos
    if fts_rank != 0.0:
        score += int(min(500, abs(fts_rank) * 200))

    return score


def flag_precedente(row):
    """Retorna string descritiva do tipo de precedente para exibição."""
    orgao  = (row['orgao'] or '').upper()
    tipo   = (row['tipoDecisao'] or '').upper()
    ementa = (row['ementa'] or '').upper()
    tema_v = (row['tema'] or '').strip()

    if tema_v or any(re.search(p, ementa + tipo, re.I) for p in PADROES_REPETITIVO):
        tema_num = tema_v if tema_v else '?'
        return f"⚖️  REPETITIVO/TEMA {tema_num}"
    if any(re.search(p, ementa + tipo, re.I) for p in PADROES_IAC):
        return "⚖️  IAC"
    if any(o in orgao for o in ORGAOS_CORTE_ESPECIAL):
        return "🔴 CORTE ESPECIAL"
    if any(o in orgao for o in [s.upper() for s in ORGAOS_SECAO]):
        return "🟠 SEÇÃO"
    return "🟡 TURMA"


# ─── Buscas ───────────────────────────────────────────────────────────────────

def buscar_com_fts(conn, query_fts, orgao_filtro=None, max_candidatos=50):
    """
    Busca usando índice FTS5 com ranking BM25.
    Suporta tanto banco principal (tabela decisoes) quanto mini banco (tabela decisoes_mini).
    Retorna lista de (row_dict, fts_rank).
    """
    usa_mini   = _e_mini_banco(conn)
    tabela     = "decisoes_mini" if usa_mini else "decisoes"
    col_ementa = "ementa_curta"  if usa_mini else "ementa"
    col_tese   = "tese_curta"    if usa_mini else "teseJuridica"

    filtro_orgao = ""
    params = [query_fts]
    if orgao_filtro:
        filtro_orgao = "AND d.orgao LIKE ?"
        params.append(f"%{orgao_filtro}%")

    sql = f"""
        SELECT d.id, d.orgao, d.processo, d.classe, d.descricaoClasse,
               d.relator, d.tipoDecisao, d.dataDecisao, d.dataPublicacao,
               d.tema,
               d.{col_ementa}  AS ementa,
               d.{col_tese}    AS teseJuridica,
               fts.rank        AS fts_rank
        FROM decisoes_fts fts
        JOIN {tabela} d ON d.rowid = fts.rowid
        WHERE decisoes_fts MATCH ?
        {filtro_orgao}
        ORDER BY fts.rank
        LIMIT {max_candidatos}
    """
    try:
        rows = conn.execute(sql, params).fetchall()
        return [(dict(r), r['fts_rank']) for r in rows]
    except sqlite3.OperationalError:
        return []


def buscar_com_like(conn, termos, orgao_filtro=None, max_candidatos=50):
    """Fallback LIKE quando FTS5 não está disponível."""
    palavras = [t.strip('"') for t in termos.split() if len(t.strip('"')) >= 3][:3]
    if not palavras:
        return []

    usa_mini   = _e_mini_banco(conn)
    tabela     = "decisoes_mini" if usa_mini else "decisoes"
    col_ementa = "ementa_curta"  if usa_mini else "ementa"
    col_tese   = "tese_curta"    if usa_mini else "teseJuridica"

    condicoes = " AND ".join(
        f"({col_ementa} LIKE ? OR {col_tese} LIKE ? OR tema LIKE ?)"
        for _ in palavras
    )
    params = []
    for p in palavras:
        params.extend([f'%{p}%', f'%{p}%', f'%{p}%'])

    filtro_orgao = ""
    if orgao_filtro:
        filtro_orgao = "AND orgao LIKE ?"
        params.append(f"%{orgao_filtro}%")

    sql = f"""
        SELECT id, orgao, processo, classe, descricaoClasse, relator,
               tipoDecisao, dataDecisao, dataPublicacao, tema,
               {col_ementa} AS ementa, {col_tese} AS teseJuridica
        FROM {tabela}
        WHERE {condicoes}
        {filtro_orgao}
        LIMIT {max_candidatos}
    """
    try:
        rows = conn.execute(sql, params).fetchall()
        return [(dict(r), 0.0) for r in rows]
    except sqlite3.OperationalError:
        return []


# ─── Função principal de busca ────────────────────────────────────────────────

def buscar_precedentes(conn, termos, orgao_filtro=None, max_resultados=10,
                       db_path=None):
    """
    Busca e ranqueia precedentes do STJ.

    Parâmetros:
        conn           : conexão SQLite aberta (ou None para abrir automaticamente)
        termos         : string com termos de busca (linguagem natural ou FTS5)
        orgao_filtro   : filtrar por órgão específico (ex: "PRIMEIRA SEÇÃO")
        max_resultados : número máximo de resultados retornados
        db_path        : caminho do banco (usado se conn=None)

    Retorna:
        Lista de dicts com os precedentes ranqueados.
    """
    fechar_conn = False
    if conn is None:
        conn = conectar(db_path or DB_PATH)
        fechar_conn = True

    try:
        usa_fts = fts_disponivel(conn)
        query   = construir_query_fts(termos)

        # ── Passagem 1 + 2: busca por texto ──────────────────────────────────
        if usa_fts:
            candidatos = buscar_com_fts(conn, query, orgao_filtro, max_candidatos=80)
        else:
            candidatos = buscar_com_like(conn, termos, orgao_filtro, max_candidatos=80)

        if not candidatos:
            return []

        # ── Passagem 3: re-ranqueamento por sistema de precedentes ────────────
        scored = []
        for row, fts_rank in candidatos:
            score = calcular_score(row, fts_rank)
            scored.append((score, dict(row)))

        scored.sort(key=lambda x: x[0], reverse=True)

        # ── Formatar resultado ────────────────────────────────────────────────
        resultados = []
        for score, row in scored[:max_resultados]:
            tipo = _classificar_tipo(row)
            resultados.append({
                "score":              score,
                "tipo_precedente":    tipo,
                "id":                 row.get('id', ''),
                "orgao":              row.get('orgao', ''),
                "processo":           row.get('processo', ''),
                "classe":             row.get('classe', ''),
                "descricaoClasse":    row.get('descricaoClasse', ''),
                "relator":            row.get('relator', ''),
                "tipoDecisao":        row.get('tipoDecisao', ''),
                "dataDecisao":        row.get('dataDecisao', ''),
                "dataPublicacao":     row.get('dataPublicacao', ''),
                "ementa":             (row.get('ementa') or '')[:1500],
                "teseJuridica":       (row.get('teseJuridica') or '')[:800],
                "tema":               row.get('tema', ''),
                "modo_busca":         "FTS5" if usa_fts else "LIKE (execute setup_fts.py para melhor performance)",
            })

        return resultados

    finally:
        if fechar_conn:
            conn.close()


def _classificar_tipo(row):
    """Classifica o tipo de precedente em texto limpo."""
    orgao  = (row.get('orgao') or '').upper()
    tipo   = (row.get('tipoDecisao') or '').upper()
    ementa = (row.get('ementa') or '').upper()
    tema_v = (row.get('tema') or '').strip()

    if tema_v or any(re.search(p, ementa + tipo, re.I) for p in PADROES_REPETITIVO):
        return "REPETITIVO" + (f" — Tema {tema_v}" if tema_v else "")
    if any(re.search(p, ementa + tipo, re.I) for p in PADROES_IAC):
        return "IAC"
    if any(o in orgao for o in ORGAOS_CORTE_ESPECIAL):
        return "CORTE ESPECIAL"
    if any(o in orgao for o in [s.upper() for s in ORGAOS_SECAO]):
        return "SEÇÃO"
    return "TURMA"


# ─── Formatação para Reflexum ─────────────────────────────────────────────────

def formatar_para_reflexum(resultados, termos_busca=""):
    """
    Formata os resultados para ingestão pelo sistema Reflexum.
    Retorna texto estruturado pronto para Claude usar como Nível 2 de jurisprudência.
    """
    if not resultados:
        return (
            "⚠️  Nenhum precedente encontrado no banco local para os termos informados.\n"
            "Use Nível 1 de jurisprudência (referência genérica) ou refine os termos."
        )

    linhas = [
        "═══════════════════════════════════════════════════════",
        f"  BANCO STJ — Precedentes encontrados",
        f"  Busca: {termos_busca}" if termos_busca else "",
        f"  {len(resultados)} resultado(s) — ranqueados por sistema de precedentes",
        "═══════════════════════════════════════════════════════\n",
    ]

    for i, r in enumerate(resultados, 1):
        tipo = r['tipo_precedente']
        flag_emoji = (
            "⚖️ " if "REPETITIVO" in tipo or "IAC" in tipo
            else "🔴 " if "CORTE ESPECIAL" in tipo
            else "🟠 " if "SEÇÃO" in tipo
            else "🟡 "
        )

        linhas.append(f"{'─'*54}")
        linhas.append(f"[{i}] {flag_emoji}{tipo}")
        linhas.append(f"    Processo : {r['processo']}  |  {r['classe']} — {r['descricaoClasse']}")
        linhas.append(f"    Relator  : {r['relator']}")
        linhas.append(f"    Órgão    : {r['orgao']}")
        linhas.append(f"    Data     : {r['dataDecisao']}  |  Tipo: {r['tipoDecisao']}")

        if r['tema']:
            linhas.append(f"    Tema STJ : {r['tema']}")

        if r['teseJuridica']:
            linhas.append(f"\n    TESE JURÍDICA:")
            linhas.append(f"    {r['teseJuridica'][:400]}")

        linhas.append(f"\n    EMENTA:")
        linhas.append(f"    {r['ementa'][:1400]}")
        linhas.append("")

    linhas.append("═══════════════════════════════════════════════════════")
    linhas.append("INSTRUÇÕES REFLEXUM:")
    linhas.append("Selecione os precedentes mais pertinentes ao caso.")
    linhas.append("Precedentes [⚖️ REPETITIVO/IAC] têm eficácia vinculante — citar prioritariamente.")
    linhas.append("Cite com: processo, relator, órgão e data — Nível 2 verificado.")
    linhas.append("═══════════════════════════════════════════════════════\n")

    return '\n'.join(l for l in linhas if l is not None)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Busca jurisprudência do STJ com ranking por sistema de precedentes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python buscar_stj.py "impenhorabilidade penhora"
  python buscar_stj.py "dano moral banco" --max 5
  python buscar_stj.py "prescrição tributária ICMS" --orgao "PRIMEIRA SEÇÃO"
  python buscar_stj.py "usucapião" --json
        """
    )
    parser.add_argument('termos',           help='Termos de busca')
    parser.add_argument('--max',  type=int, default=8,    help='Máximo de resultados (padrão: 8)')
    parser.add_argument('--orgao',          default=None, help='Filtrar por órgão julgador')
    parser.add_argument('--json',           action='store_true', help='Saída em JSON')
    parser.add_argument('--db',             default=None, help='Caminho do banco SQLite')

    args = parser.parse_args()

    try:
        conn = conectar(args.db or None)
    except FileNotFoundError as e:
        print(f"\nERRO: {e}")
        sys.exit(1)

    usa_fts = fts_disponivel(conn)
    if not usa_fts:
        print("\n⚠️  Índice FTS5 não encontrado.")
        print("   Para melhor performance, execute: python setup_fts.py")
        print("   Usando busca LIKE como fallback...\n")

    resultados = buscar_precedentes(
        conn,
        args.termos,
        orgao_filtro=args.orgao,
        max_resultados=args.max,
    )
    conn.close()

    if args.json:
        print(json.dumps(resultados, ensure_ascii=False, indent=2))
    else:
        print(formatar_para_reflexum(resultados, termos_busca=args.termos))


if __name__ == "__main__":
    main()
