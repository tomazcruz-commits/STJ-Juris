"""
analisar_stj.py
===============
Análise jurisprudencial aberta do banco STJ.

Em vez de retornar uma lista de julgados para citação em peça,
este script recupera um conjunto amplo de decisões sobre um tema e
produz um bloco estruturado para o Claude sintetizar:

  - Posição dominante do STJ
  - Precedentes vinculantes (Repetitivos, IAC, Súmulas referenciadas)
  - Evolução temporal da jurisprudência
  - Divergências entre Turmas/Seções
  - Nuances, exceções e casos especiais
  - Estado atual (decisões mais recentes)

Uso:
    python analisar_stj.py "prescrição intercorrente execução fiscal"
    python analisar_stj.py "responsabilidade civil médica" --max 30
    python analisar_stj.py "bem de família impenhorabilidade" --de 2018 --ate 2025
    python analisar_stj.py "dano moral negativação indevida" --orgao "TERCEIRA TURMA"
"""

import os
import re
import sys
import json
import shutil
import sqlite3
import argparse
from collections import defaultdict
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(SCRIPT_DIR, "stj_jurisprudencia.db")
DB_MINI    = os.path.join(SCRIPT_DIR, "stj_mini.db")
DB_TMP     = "/tmp/stj_mini.db"


def resolver_banco():
    import time
    if os.path.exists(DB_TMP):
        idade_h = (time.time() - os.path.getmtime(DB_TMP)) / 3600
        if idade_h < 8:
            return DB_TMP
    if os.path.exists(DB_MINI):
        print("Copiando banco de busca para memória local... ", end="", flush=True)
        try:
            shutil.copy2(DB_MINI, DB_TMP)
            mb = os.path.getsize(DB_TMP) / 1024 / 1024
            print(f"OK ({mb:.0f} MB)")
            return DB_TMP
        except Exception as e:
            print(f"falhou ({e})")
    return DB_PATH

# ─── Reutiliza helpers do buscar_stj ─────────────────────────────────────────

PADROES_REPETITIVO = [
    r'\bTEMA\s+\d+\b', r'\bRECURSO\s+REPETITIVO\b', r'\bREPETITIVO\b',
    r'\bAFETA[ÇC][ÃA]O\b', r'\bJULGAMENTO\s+REPETITIVO\b', r'\bTESE\s+FIRMADA\b',
]
PADROES_IAC = [
    r'\bIAC\b', r'\bINCIDENTE\s+DE\s+ASSUN[ÇC][ÃA]O\s+DE\s+COMPET[EÊ]NCIA\b',
]
PADROES_SUMULA = [
    r'\bS[ÚU]MULA\s+(?:N[º°.]?\s*)?\d+\b',
]

ORGAOS_CORTE_ESPECIAL = ['CORTE ESPECIAL']
ORGAOS_SECAO = ['1ª SEÇÃO', '2ª SEÇÃO', '3ª SEÇÃO',
                'PRIMEIRA SEÇÃO', 'SEGUNDA SEÇÃO', 'TERCEIRA SEÇÃO',
                '1A SEÇÃO', '2A SEÇÃO', '3A SEÇÃO']


def conectar(db_path=None):
    path = db_path or resolver_banco()
    if not os.path.exists(path):
        raise FileNotFoundError(f"Banco não encontrado: {path}\nExecute: python criar_mini_banco.py")
    conn = sqlite3.connect(path, timeout=120)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only  = ON")
    conn.execute("PRAGMA cache_size  = 20000")
    return conn


def _e_mini_banco(conn):
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='decisoes_mini'"
    )
    return cur.fetchone() is not None


def fts_disponivel(conn):
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='decisoes_fts'"
    )
    return cur.fetchone() is not None


def construir_query_fts(termos):
    if ' AND ' in termos or ' OR ' in termos or ' NOT ' in termos:
        return termos
    frases   = re.findall(r'"([^"]+)"', termos)
    resto    = re.sub(r'"[^"]+"', '', termos)
    palavras = [p.strip() for p in resto.split() if len(p.strip()) >= 3]
    partes   = [f'"{f}"' for f in frases] + [f'"{p}"' for p in palavras]
    return ' AND '.join(partes) if partes else termos


def extrair_ano(data_str):
    try:
        data_clean = re.sub(r'[^0-9]', '', data_str or '')
        if len(data_clean) >= 4:
            return int(data_clean[:4])
    except (ValueError, IndexError):
        pass
    return None


def classificar_orgao(orgao):
    o = (orgao or '').upper()
    if any(x in o for x in ORGAOS_CORTE_ESPECIAL):
        return 'Corte Especial'
    if any(x in o for x in [s.upper() for s in ORGAOS_SECAO]):
        return 'Seção'
    return 'Turma'


def detectar_tipo_precedente(row):
    ementa = (row['ementa'] or '').upper()
    tipo   = (row['tipoDecisao'] or '').upper()
    tema_v = (row['tema'] or '').strip()
    texto  = ementa + ' ' + tipo
    if tema_v or any(re.search(p, texto, re.I) for p in PADROES_REPETITIVO):
        return 'REPETITIVO', tema_v
    if any(re.search(p, texto, re.I) for p in PADROES_IAC):
        return 'IAC', ''
    return 'ORDINARIO', ''


def extrair_sumulas_citadas(texto):
    """Extrai todas as súmulas mencionadas no texto."""
    matches = re.findall(r'S[ÚUúu]mula\s+(?:n[º°.]?\s*)?(\d+)', texto or '', re.I)
    return sorted(set(matches), key=lambda x: int(x))


# ─── Busca ────────────────────────────────────────────────────────────────────

def buscar_decisoes(conn, termos, orgao_filtro=None, ano_de=None, ano_ate=None,
                    max_candidatos=60):
    usa_fts = fts_disponivel(conn)
    query   = construir_query_fts(termos)

    filtros_extra = []
    params_extra  = []

    if orgao_filtro:
        filtros_extra.append("AND d.orgao LIKE ?")
        params_extra.append(f"%{orgao_filtro}%")

    if ano_de:
        filtros_extra.append("AND CAST(SUBSTR(d.dataDecisao, 1, 4) AS INTEGER) >= ?")
        params_extra.append(ano_de)

    if ano_ate:
        filtros_extra.append("AND CAST(SUBSTR(d.dataDecisao, 1, 4) AS INTEGER) <= ?")
        params_extra.append(ano_ate)

    filtros_str = ' '.join(filtros_extra)

    usa_mini   = _e_mini_banco(conn)
    tabela     = "decisoes_mini" if usa_mini else "decisoes"
    col_ementa = "ementa_curta"  if usa_mini else "ementa"
    col_tese   = "tese_curta"    if usa_mini else "teseJuridica"

    if usa_fts:
        sql = f"""
            SELECT d.id, d.orgao, d.processo, d.classe, d.descricaoClasse,
                   d.relator, d.tipoDecisao, d.dataDecisao, d.dataPublicacao,
                   d.tema,
                   d.{col_ementa} AS ementa,
                   d.{col_tese}   AS teseJuridica,
                   fts.rank AS fts_rank
            FROM decisoes_fts fts
            JOIN {tabela} d ON d.rowid = fts.rowid
            WHERE decisoes_fts MATCH ?
            {filtros_str}
            ORDER BY fts.rank
            LIMIT {max_candidatos}
        """
        params = [query] + params_extra
    else:
        palavras = [t.strip('"') for t in termos.split() if len(t.strip('"')) >= 3][:3]
        conds    = " AND ".join(
            f"(d.{col_ementa} LIKE ? OR d.{col_tese} LIKE ? OR d.tema LIKE ?)"
            for _ in palavras
        )
        p = []
        for w in palavras:
            p.extend([f'%{w}%', f'%{w}%', f'%{w}%'])
        sql = f"""
            SELECT d.id, d.orgao, d.processo, d.classe, d.descricaoClasse,
                   d.relator, d.tipoDecisao, d.dataDecisao, d.dataPublicacao,
                   d.tema,
                   d.{col_ementa} AS ementa,
                   d.{col_tese}   AS teseJuridica,
                   0 AS fts_rank
            FROM {tabela} d
            WHERE {conds}
            {filtros_str}
            LIMIT {max_candidatos}
        """
        params = p + params_extra

    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    except sqlite3.OperationalError as e:
        print(f"Erro na busca: {e}", file=sys.stderr)
        return []


# ─── Análise estatística ──────────────────────────────────────────────────────

def analisar_conjunto(decisoes):
    """Extrai estatísticas e agrupa o conjunto de decisões para análise."""

    stats = {
        'total': len(decisoes),
        'por_tipo_precedente': defaultdict(list),
        'por_orgao_categoria': defaultdict(list),
        'por_orgao_nome': defaultdict(int),
        'por_ano': defaultdict(int),
        'sumulas_citadas': defaultdict(int),
        'relatores_frequentes': defaultdict(int),
        'teses': [],
        'vinculantes': [],
        'recentes': [],
    }

    for r in decisoes:
        tipo_prec, tema_val = detectar_tipo_precedente(r)
        orgao_cat = classificar_orgao(r['orgao'])
        ano       = extrair_ano(r['dataDecisao'])

        # Agrupamentos
        stats['por_tipo_precedente'][tipo_prec].append(r)
        stats['por_orgao_categoria'][orgao_cat].append(r)
        stats['por_orgao_nome'][r['orgao'] or 'Desconhecido'] += 1
        if ano:
            stats['por_ano'][ano] += 1

        # Súmulas citadas
        todas_sumulas = extrair_sumulas_citadas(r['ementa']) + extrair_sumulas_citadas(r['teseJuridica'])
        for s in todas_sumulas:
            stats['sumulas_citadas'][s] += 1

        # Relator
        if r['relator']:
            stats['relatores_frequentes'][r['relator']] += 1

        # Teses jurídicas preenchidas
        if r['teseJuridica'] and r['teseJuridica'].strip():
            stats['teses'].append(r)

        # Vinculantes
        if tipo_prec in ('REPETITIVO', 'IAC'):
            r['_tipo_precedente'] = tipo_prec
            r['_tema_val'] = tema_val
            stats['vinculantes'].append(r)

    # Recentes: top 5 por data
    com_data = [(extrair_ano(r['dataDecisao']) or 0, r) for r in decisoes]
    com_data.sort(key=lambda x: x[0], reverse=True)
    stats['recentes'] = [r for _, r in com_data[:5]]

    return stats


# ─── Formatação do bloco de análise ──────────────────────────────────────────

def formatar_bloco_analise(decisoes, termos, stats):
    """
    Monta o bloco de análise estruturada para ser lido e sintetizado pelo Claude.
    """
    linhas = []
    sep    = '═' * 60

    linhas.append(sep)
    linhas.append(f"  ANÁLISE JURISPRUDENCIAL — BANCO STJ LOCAL")
    linhas.append(f"  Tema pesquisado: {termos}")
    linhas.append(f"  Decisões analisadas: {stats['total']}")
    linhas.append(f"  Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    linhas.append(sep)

    # ── Distribuição geral ────────────────────────────────────────────────────
    linhas.append("\n## 1. PANORAMA QUANTITATIVO\n")

    por_ano = stats['por_ano']
    if por_ano:
        anos_sorted = sorted(por_ano.keys())
        periodos = {}
        for ano in anos_sorted:
            decada = f"{(ano//5)*5}-{(ano//5)*5+4}"
            periodos[decada] = periodos.get(decada, 0) + por_ano[ano]
        linhas.append("Distribuição temporal:")
        for periodo, qtd in sorted(periodos.items()):
            linhas.append(f"  {periodo}: {qtd} decisão(ões)")

    linhas.append("\nDistribuição por órgão:")
    for cat, lst in sorted(stats['por_orgao_categoria'].items()):
        linhas.append(f"  {cat}: {len(lst)} decisão(ões)")

    for orgao, qtd in sorted(stats['por_orgao_nome'].items(), key=lambda x: -x[1])[:8]:
        linhas.append(f"    └─ {orgao}: {qtd}")

    v_count = len(stats['vinculantes'])
    linhas.append(f"\nPrecedentes vinculantes identificados: {v_count} "
                  f"({'Repetitivos/IAC' if v_count else 'nenhum — apenas persuasivos'})")

    sumulas = stats['sumulas_citadas']
    if sumulas:
        top_sumulas = sorted(sumulas.items(), key=lambda x: -x[1])[:5]
        linhas.append(f"Súmulas citadas com frequência: " +
                      ', '.join(f"Súmula {n}" for n, _ in top_sumulas))

    # ── Precedentes vinculantes ────────────────────────────────────────────────
    if stats['vinculantes']:
        linhas.append(f"\n{'─'*60}")
        linhas.append("## 2. PRECEDENTES VINCULANTES (Repetitivos e IAC)\n")
        linhas.append("⚠️  Estas são as teses com eficácia obrigatória — ponto de partida da análise.\n")

        # Deduplica por tema/processo
        vistos = set()
        for r in stats['vinculantes']:
            chave = r.get('_tema_val') or r['processo']
            if chave in vistos:
                continue
            vistos.add(chave)

            tipo_label = r.get('_tipo_precedente', '')
            tema_label = f" — {r['_tema_val']}" if r.get('_tema_val') else ''
            linhas.append(f"[{tipo_label}{tema_label}]")
            linhas.append(f"  Processo : {r['processo']}  |  {r['classe']}")
            linhas.append(f"  Relator  : {r['relator']}  |  Órgão: {r['orgao']}")
            linhas.append(f"  Data     : {r['dataDecisao']}")
            if r['teseJuridica'] and r['teseJuridica'].strip():
                linhas.append(f"\n  TESE FIRMADA:")
                linhas.append(f"  {r['teseJuridica'][:1000]}")
            linhas.append(f"\n  EMENTA:")
            linhas.append(f"  {(r['ementa'] or '')[:800]}")
            linhas.append("")

    # ── Teses jurídicas explícitas ────────────────────────────────────────────
    if stats['teses']:
        linhas.append(f"{'─'*60}")
        linhas.append("## 3. TESES JURÍDICAS EXPLÍCITAS NO BANCO\n")
        linhas.append("(Julgados onde o STJ formulou a tese de forma expressa)\n")
        for r in stats['teses'][:10]:
            linhas.append(f"[{r['orgao']} | {r['dataDecisao']} | {r['relator']}]")
            linhas.append(f"  {r['teseJuridica'][:700]}")
            linhas.append("")

    # ── Decisões recentes ─────────────────────────────────────────────────────
    linhas.append(f"{'─'*60}")
    linhas.append("## 4. ESTADO ATUAL — DECISÕES MAIS RECENTES\n")
    for r in stats['recentes']:
        linhas.append(f"[{r['orgao']} | {r['dataDecisao']} | {r['classe']} | {r['relator']}]")
        linhas.append(f"  {(r['ementa'] or '')[:600]}")
        linhas.append("")

    # ── Distribuição por órgão (divergências) ────────────────────────────────
    por_orgao_cat = stats['por_orgao_categoria']
    if len(por_orgao_cat) > 1:
        linhas.append(f"{'─'*60}")
        linhas.append("## 5. DISTRIBUIÇÃO ENTRE ÓRGÃOS\n")
        linhas.append("(Útil para identificar divergências entre Turmas)\n")
        for cat, lst in sorted(por_orgao_cat.items()):
            linhas.append(f"{cat} ({len(lst)} decisões):")
            por_nome = defaultdict(int)
            for r in lst:
                por_nome[r['orgao'] or '?'] += 1
            for nome, qtd in sorted(por_nome.items(), key=lambda x: -x[1]):
                # Pega ementa mais recente desse órgão
                mais_rec = max(
                    [r for r in lst if r['orgao'] == nome],
                    key=lambda x: re.sub(r'[^0-9]', '', x['dataDecisao'] or '0'),
                    default=None
                )
                trecho = (mais_rec['ementa'] or '')[:200] if mais_rec else ''
                linhas.append(f"  └─ {nome} ({qtd}):")
                if trecho:
                    linhas.append(f"     Última decisão: {trecho}...")
            linhas.append("")

    # ── Relator mais frequente ────────────────────────────────────────────────
    relatores = stats['relatores_frequentes']
    if relatores:
        top_rel = sorted(relatores.items(), key=lambda x: -x[1])[:5]
        linhas.append(f"{'─'*60}")
        linhas.append("## 6. RELATORES MAIS FREQUENTES NO TEMA\n")
        for rel, qtd in top_rel:
            linhas.append(f"  {rel}: {qtd} decisão(ões)")
        linhas.append("")

    # ── Instrução final para o Claude ─────────────────────────────────────────
    linhas.append(sep)
    linhas.append("## INSTRUÇÃO PARA SÍNTESE\n")
    linhas.append(
        "Com base nos dados acima, produza uma análise jurisprudencial estruturada contendo:\n"
        "1. POSIÇÃO DOMINANTE: Qual é o entendimento consolidado do STJ sobre o tema?\n"
        "2. PRECEDENTES VINCULANTES: Quais Repetitivos/IAC/Súmulas regem o tema?\n"
        "3. EVOLUÇÃO TEMPORAL: Como a jurisprudência se desenvolveu ao longo do tempo?\n"
        "4. DIVERGÊNCIAS: Há posições conflitantes entre Turmas ou Seções?\n"
        "5. NUANCES E EXCEÇÕES: Quais são os casos especiais ou limites da tese dominante?\n"
        "6. ESTADO ATUAL: Qual é a tendência das decisões mais recentes (2023-2025)?\n"
        "7. APLICAÇÃO PRÁTICA: O que um advogado deve saber sobre este tema para uma peça?\n"
    )
    linhas.append(sep)

    return '\n'.join(linhas)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Análise jurisprudencial aberta do banco STJ",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python analisar_stj.py "prescrição intercorrente execução fiscal"
  python analisar_stj.py "responsabilidade civil médica" --max 30
  python analisar_stj.py "bem de família impenhorabilidade" --de 2019 --ate 2025
  python analisar_stj.py "dano moral negativação" --orgao "TERCEIRA TURMA"
        """
    )
    parser.add_argument('termos',            help='Tema ou pergunta jurídica')
    parser.add_argument('--max',  type=int,  default=25,   help='Máximo de decisões (padrão: 25)')
    parser.add_argument('--de',   type=int,  default=None, help='Ano inicial do filtro temporal')
    parser.add_argument('--ate',  type=int,  default=None, help='Ano final do filtro temporal')
    parser.add_argument('--orgao',           default=None, help='Filtrar por órgão julgador')
    parser.add_argument('--db',              default=None, help='Caminho do banco SQLite')
    parser.add_argument('--json',            action='store_true', help='Exportar decisões brutas em JSON')

    args = parser.parse_args()

    try:
        conn = conectar(args.db or DB_PATH)
    except FileNotFoundError as e:
        print(f"\nERRO: {e}", file=sys.stderr)
        sys.exit(1)

    usa_fts = fts_disponivel(conn)
    if not usa_fts:
        print("⚠️  FTS5 não encontrado — usando busca LIKE (menos precisa).", file=sys.stderr)
        print("   Execute: python setup_fts.py\n", file=sys.stderr)

    print(f"\nBuscando: \"{args.termos}\"...", file=sys.stderr)

    decisoes = buscar_decisoes(
        conn,
        args.termos,
        orgao_filtro=args.orgao,
        ano_de=args.de,
        ano_ate=args.ate,
        max_candidatos=args.max,
    )
    conn.close()

    if not decisoes:
        print("\n⚠️  Nenhuma decisão encontrada para os termos informados.")
        print("Sugestões: tente termos mais amplos ou verifique a grafia.")
        sys.exit(0)

    print(f"  {len(decisoes)} decisões recuperadas. Analisando...\n", file=sys.stderr)

    if args.json:
        print(json.dumps(decisoes, ensure_ascii=False, indent=2))
        return

    stats = analisar_conjunto(decisoes)
    bloco = formatar_bloco_analise(decisoes, args.termos, stats)
    print(bloco)


if __name__ == "__main__":
    main()
