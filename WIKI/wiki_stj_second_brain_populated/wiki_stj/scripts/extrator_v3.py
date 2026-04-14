#!/usr/bin/env python3
"""
extrator_v3.py — Extração com deduplicação de versões e suporte a PDFs finais

Melhorias em relação à v2:
  1. Detecta grupos de versões da mesma peça (mesmo cliente, tipo, ano, partes)
  2. Para cada grupo, usa o arquivo mais recente (por mtime) como versão principal
  3. Se existir PDF com nome similar na mesma pasta → prefere o PDF como versão final
  4. Marca stubs de versões antigas como "versão anterior — usar [[ID_PRINCIPAL]]"
  5. Gera relatório completo de deduplicação + extração

Uso:
  python3 extrator_v3.py
"""

import io, json, re, os
from pathlib import Path
from collections import defaultdict
from docx import Document

# ─── CONFIG ───────────────────────────────────────────────────────────────────

MACIEL_ROOT  = Path("/sessions/elegant-great-clarke/mnt")
WIKI_ROOT    = Path("/sessions/elegant-great-clarke/mnt/STJ JURIS/WIKI/wiki_stj_second_brain_populated/wiki_stj")
MAPPING_PATH = WIKI_ROOT / "pecas" / "pecas_mapping.json"
TODAY        = "2026-04-11"

TIPOS = {
    "EMBARGOS DE DECLARAÇÃO": "edcl",
    "RECURSO ESPECIAL":       "resp",
    "AGRAVO DE INSTRUMENTO":  "agravo-instrumento",
    "APELAÇÃO":               "apelacao",
    "CONTESTAÇÃO":            "contestacao",
}

# ─── NORMALIZAÇÃO DE PARTES ───────────────────────────────────────────────────

def normalizar_partes(parties: str) -> str:
    """Normaliza o par de partes para deduplicação (ordem não importa)."""
    partes = [p.strip().upper() for p in re.split(r'\s+x\s+', parties, maxsplit=1)]
    return " x ".join(sorted(partes))

# ─── VERIFICAÇÃO DE ACESSIBILIDADE ────────────────────────────────────────────

def arquivo_acessivel(path: Path) -> bool:
    """Verifica se o arquivo está realmente disponível (não é placeholder cloud)."""
    try:
        with open(path, 'rb') as fh:
            fh.read(4)
        return True
    except OSError:
        return False

# ─── LEITURA ROBUSTA ──────────────────────────────────────────────────────────

def ler_docx_robusto(path: Path):
    """Lê DOCX via BytesIO para contornar problemas de path no mount."""
    with open(path, 'rb') as fh:
        data = fh.read()
    doc = Document(io.BytesIO(data))
    paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return paras, '\n'.join(paras)

# ─── DETECÇÃO DE PDF FINAL ────────────────────────────────────────────────────

def encontrar_pdf_final(docx_path: Path) -> Path | None:
    """
    Procura PDF final na mesma pasta do DOCX.
    Estratégia:
      1. PDF com nome idêntico ao DOCX (trocando extensão)
      2. PDF com nome similar (sem sufixos como " - Copia", "v2", números)
      3. PDF mais recente na mesma pasta (último fallback)
    """
    pasta = docx_path.parent
    stem_base = re.sub(r'\s*[-–]\s*(Copia|cópia|v\d+|\(\d+\))$', '', docx_path.stem, flags=re.I).strip()

    # 1. PDF com mesmo stem
    pdf_exato = pasta / f"{docx_path.stem}.pdf"
    if pdf_exato.exists() and arquivo_acessivel(pdf_exato):
        return pdf_exato

    # 2. PDF com stem base (sem sufixo de versão)
    pdf_base = pasta / f"{stem_base}.pdf"
    if pdf_base.exists() and arquivo_acessivel(pdf_base):
        return pdf_base

    # 3. PDF cujo nome contém o stem base
    pdfs_na_pasta = list(pasta.glob("*.pdf"))
    candidatos = [
        p for p in pdfs_na_pasta
        if stem_base.lower() in p.stem.lower() and arquivo_acessivel(p)
    ]
    if candidatos:
        # Retornar o mais recente
        return max(candidatos, key=lambda p: p.stat().st_mtime)

    return None

# ─── DEDUPLICAÇÃO DE VERSÕES ─────────────────────────────────────────────────

def detectar_grupos_versoes(mapping: dict) -> dict:
    """
    Agrupa peças que são versões da mesma peça.
    Chave: (client_folder, canonical_type, year, partes_normalizadas)

    Retorna: dict { chave → lista de (pid, peca, caminho_real) } para grupos com >1 entrada
    """
    grupos = defaultdict(list)

    for pid, peca in mapping.items():
        # Só tipos prioritários
        if peca.get("canonical_type") not in TIPOS:
            continue

        caminho = MACIEL_ROOT / peca["rel_path"]
        parties_norm = normalizar_partes(peca.get("parties", ""))
        chave = (peca["client_folder"], peca["canonical_type"], peca["year"], parties_norm)
        grupos[chave].append((pid, peca, caminho))

    # Retornar apenas grupos com duplicatas
    return {k: v for k, v in grupos.items() if len(v) > 1}

def escolher_versao_principal(entradas: list) -> tuple:
    """
    Dada uma lista de (pid, peca, caminho), escolhe a versão principal.

    Critérios (em ordem):
      1. PDF final disponível → aquele cujo DOCX tem PDF correspondente
      2. DOCX mais recente (maior mtime) entre os acessíveis
      3. Primeiro da lista (fallback)

    Retorna (pid_principal, peca_principal, caminho_principal, pdf_path_ou_None, ids_versoes_anteriores)
    """
    acessiveis = []
    for pid, peca, caminho in entradas:
        if caminho.exists() and arquivo_acessivel(caminho):
            mtime = caminho.stat().st_mtime
            pdf = encontrar_pdf_final(caminho)
            acessiveis.append((pid, peca, caminho, mtime, pdf))

    if not acessiveis:
        # Nenhum acessível — retornar o primeiro como principal (sem conteúdo)
        pid, peca, caminho = entradas[0]
        versoes_ant = [e[0] for e in entradas[1:]]
        return pid, peca, caminho, None, versoes_ant

    # Preferir entrada com PDF
    com_pdf = [e for e in acessiveis if e[4] is not None]
    if com_pdf:
        # Entre os que têm PDF, pegar o mais recente
        principal = max(com_pdf, key=lambda e: e[3])
    else:
        # Sem PDF, pegar DOCX mais recente
        principal = max(acessiveis, key=lambda e: e[3])

    pid_p, peca_p, cam_p, _, pdf_p = principal
    versoes_ant = [e[0] for e in acessiveis if e[0] != pid_p]
    # Também incluir os não-acessíveis como versões anteriores
    versoes_ant += [e[0] for e in entradas if e[0] != pid_p and e[0] not in versoes_ant]

    return pid_p, peca_p, cam_p, pdf_p, versoes_ant

# ─── EXTRAÇÃO DE JURISPRUDÊNCIA ───────────────────────────────────────────────

def extrair_juris(texto):
    refs = set()

    for m in re.finditer(r'[Ss]ú[mn]ula[s]?\s+(?:n[º°oa]?\s*)?(\d+)\s*[/,]?\s*(STJ|STF|TJPE|TRF5?)?', texto):
        tribunal = m.group(2) or "STJ"
        refs.add(f"Súmula {m.group(1)}/{tribunal}")

    for m in re.finditer(r'[Tt]ema\s+(?:[Rr]epetitivo\s+)?(?:n[º°oa]?\s*)?(\d+)', texto):
        refs.add(f"Tema Repetitivo {m.group(1)}/STJ")

    for m in re.finditer(r'\b(REsp|AREsp|AgInt|AgRg|HC|CC)\s+(?:n[º°oa]?\s*)?([\d.,]+(?:[/-]\w+)*)', texto, re.I):
        classe = m.group(1).upper()
        num    = m.group(2)[:15]
        refs.add(f"{classe} {num}")

    diplomas = {
        'Código de Processo Civil': 'CPC/2015',
        'CPC': 'CPC/2015',
        'Código de Defesa do Consumidor': 'CDC',
        'CDC': 'CDC',
        'Código Civil': 'CC/2002',
        'Lei nº 8.009': 'Lei 8.009/90',
        'Lei 8.009': 'Lei 8.009/90',
    }
    for nome, sigla in diplomas.items():
        arts = re.findall(
            rf'art(?:igo)?s?\.\s*(\d+[°º]?(?:\s*,\s*\d+[°º]?)*)[^\n]{{0,20}}{re.escape(nome)}',
            texto, re.I
        )
        for art in arts[:3]:
            refs.add(f"Art. {art.strip()} — {sigla}")

    return sorted(refs)[:20]

# ─── SUMARIZAÇÃO POR TIPO ─────────────────────────────────────────────────────

def sumarizar(paras, tipo):
    texto_upper = '\n'.join(paras).upper()

    marcadores_por_tipo = {
        "EMBARGOS DE DECLARAÇÃO": ['OMISSÃO', 'CONTRADIÇÃO', 'OBSCURIDADE', 'ERRO MATERIAL',
                                    'DEIXOU DE', 'OMITIU', 'NÃO APRECIOU', 'PREQUESTIONAMENTO', 'ART. 1.025'],
        "RECURSO ESPECIAL":       ['VIOLAÇÃO', 'CONTRARIOU', 'NEGOU VIGÊNCIA', 'DIVERGÊNCIA',
                                    'DISSÍDIO', 'ALÍNEA "A"', 'ALÍNEA "C"'],
        "APELAÇÃO":               ['MERECE SER REFORMADA', 'NÃO MERECE PROSPERAR', 'EQUIVOCADA',
                                    'ERROR IN JUDICANDO', 'SENTENÇA', 'ACÓRDÃO RECORRIDO'],
        "CONTESTAÇÃO":            ['IMPROCEDENTE', 'IMPROCEDÊNCIA', 'NÃO MERECE AMPARO',
                                    'DO MÉRITO', 'AUSÊNCIA DE', 'INEXISTÊNCIA DE'],
        "AGRAVO DE INSTRUMENTO":  ['FUMUS', 'PERICULUM', 'URGÊNCIA', 'RISCO', 'ERROR IN',
                                    'DECISÃO AGRAVADA'],
    }

    marcadores = marcadores_por_tipo.get(tipo, [])
    min_len = 60 if tipo == "EMBARGOS DE DECLARAÇÃO" else 80

    for i, p in enumerate(paras):
        if any(m in p.upper() for m in marcadores) and len(p) > min_len:
            trecho = ' '.join(paras[i:i+3 if tipo == "EMBARGOS DE DECLARAÇÃO" else i+4])
            return trecho[:600]

    mid = len(paras) // 3
    return ' '.join(paras[mid:mid+5])[:600]

def detectar_estrutura(texto):
    mapa = {
        'preliminares':      r'(PRELIMINAR|PREJUDICIAL|INCOMPETÊNCIA|ILEGITIMIDADE|PRESCRIÇÃO)',
        'mérito':            r'(DO MÉRITO|NO MÉRITO|MÉRITO|DO DIREITO)',
        'fatos':             r'(DOS FATOS|DO CASO|BREVE RELATO|HISTÓRICO)',
        'tutela':            r'(TUTELA|LIMINAR|EFEITO SUSPENSIVO|URGÊNCIA)',
        'cabimento':         r'(CABIMENTO|TEMPESTIVIDADE|ADMISSIBILIDADE)',
        'prequestionamento': r'(PREQUESTIONAMENTO)',
        'pedidos':           r'(DOS PEDIDOS|ANTE O EXPOSTO|NESTES TERMOS)',
    }
    return [nome for nome, pat in mapa.items() if re.search(pat, texto.upper())]

# ─── ATUALIZAÇÃO DE STUBS ─────────────────────────────────────────────────────

def marcar_versao_anterior(stub_path: Path, pid_principal: str) -> bool:
    """Marca um stub como versão anterior, redirecionando para o principal."""
    if not stub_path.exists():
        return False

    conteudo = stub_path.read_text(encoding="utf-8")

    if 'status: "preenchido"' in conteudo or 'status: "versão anterior' in conteudo:
        return False

    # Atualizar status no frontmatter
    conteudo = re.sub(
        r'status: "(?:stub|auto-preenchido[^"]*)"',
        'status: "versão anterior"',
        conteudo
    )

    # Adicionar nota no topo do conteúdo
    nota_versao = (
        f"\n> ⚠️ **VERSÃO ANTERIOR** — Esta peça é uma versão não-final.\n"
        f"> Consultar a versão principal: [[pecas/{pid_principal}|{pid_principal}]]\n\n"
    )

    # Inserir após o bloco frontmatter (após o segundo ---)
    partes = conteudo.split('---', 2)
    if len(partes) >= 3:
        conteudo = f"---{partes[1]}---\n{nota_versao}{partes[2]}"

    stub_path.write_text(conteudo, encoding="utf-8")
    return True

def atualizar_stub_v3(stub_path: Path, tese: str, juris: list, estrutura: list,
                      nome_arquivo: str, tem_pdf: bool, pdf_nome: str = "") -> bool:
    """Atualiza stub com conteúdo extraído (versão principal)."""
    conteudo = stub_path.read_text(encoding="utf-8")

    if 'status: "preenchido"' in conteudo:
        return False

    conteudo = conteudo.replace('status: "stub"', 'status: "auto-preenchido — verificar"')
    conteudo = conteudo.replace('status: "versão anterior"', 'status: "auto-preenchido — verificar"')

    # Atualizar data
    conteudo = re.sub(
        r'(status: "auto-preenchido — verificar"\nupdated:)\s*"[^"]*"',
        rf'\1 "{TODAY}"',
        conteudo
    )

    # Nota sobre PDF final
    nota_pdf = ""
    if tem_pdf:
        nota_pdf = f"\n> 📄 **Versão PDF final disponível:** `{pdf_nome}` — usar para protocolo.\n"

    # Tese central
    tese_nova = (
        "## Tese central\n\n"
        "> ⚙️ *Extraído automaticamente do DOCX — revisar e completar.*\n"
        f"{nota_pdf}"
        f"\n{tese}\n"
    )
    conteudo = re.sub(
        r'## Tese central\n+<!-- [^\n]+ -->\n*',
        tese_nova,
        conteudo
    )

    # Jurisprudência
    if juris:
        rows = "\n".join(f"| `{j}` | — |" for j in juris)
        juris_nova = (
            "## Jurisprudência utilizada\n\n"
            "> ⚙️ *Referências detectadas automaticamente — verificar aplicação.*\n\n"
            "| Referência | Aplicação |\n"
            "|:-----------|:----------|\n"
            f"{rows}\n"
        )
        conteudo = re.sub(
            r'## Jurisprudência utilizada\n+<!-- [^\n]+ -->\n+\| Referência.*?\| \| \|\n*',
            juris_nova,
            conteudo,
            flags=re.DOTALL
        )

    # Contexto do caso
    info_estrutura = ", ".join(estrutura) if estrutura else "—"
    conteudo = conteudo.replace(
        '## Contexto do caso\n\n<!-- Descrever brevemente a situação fática e o que motivou esta peça -->',
        f'## Contexto do caso\n\n> ⚙️ **Estrutura detectada:** {info_estrutura}\n> **Arquivo fonte:** `{nome_arquivo}`\n\n<!-- Descrever brevemente a situação fática e o que motivou esta peça -->'
    )

    stub_path.write_text(conteudo, encoding="utf-8")
    return True

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    print("📂 Carregando mapeamento...")
    with open(MAPPING_PATH, encoding="utf-8") as f:
        mapping = json.load(f)

    prioritarias = {pid: p for pid, p in mapping.items() if p.get("canonical_type") in TIPOS}
    print(f"   {len(prioritarias)} peças prioritárias")

    # ── FASE 1: Deduplicação de versões ──────────────────────────────────────
    print("\n🔍 Fase 1 — Detectando grupos de versões...")
    grupos_versoes = detectar_grupos_versoes(prioritarias)
    print(f"   {len(grupos_versoes)} grupos com múltiplas versões detectados")

    # Mapear pid → pid_principal (para quem é versão anterior)
    versao_anterior_de = {}  # pid_antigo → pid_principal

    for chave, entradas in grupos_versoes.items():
        cf, ct, yr, parties = chave
        pid_p, peca_p, cam_p, pdf_p, versoes_ant = escolher_versao_principal(entradas)

        print(f"\n   [{yr}] {cf} — {ct} ({parties[:30]})")
        print(f"   ✓ Principal: {pid_p} ({cam_p.name[:50]})")
        if pdf_p:
            print(f"     📄 PDF final: {pdf_p.name}")
        for vid in versoes_ant:
            versao_anterior_de[vid] = pid_p
            print(f"     ↩ Versão anterior: {vid}")

    print(f"\n   Total versões anteriores: {len(versao_anterior_de)}")

    # ── FASE 2: Marcar versões anteriores ────────────────────────────────────
    print("\n🏷️  Fase 2 — Marcando versões anteriores nos stubs...")
    marcados = 0
    for pid_ant, pid_principal in versao_anterior_de.items():
        peca = prioritarias.get(pid_ant)
        if not peca:
            continue
        folder = TIPOS[peca["canonical_type"]]
        stub_path = WIKI_ROOT / "pecas" / folder / f"{pid_ant}.md"
        if marcar_versao_anterior(stub_path, pid_principal):
            marcados += 1
            print(f"   ↩ {pid_ant} → principal: {pid_principal}")

    # ── FASE 3: Extração de conteúdo das versões principais ──────────────────
    print("\n⚙️  Fase 3 — Extraindo conteúdo das versões principais...")

    ok, skip, erro_leitura, nao_local = 0, 0, 0, 0
    extraidos = []

    # Processar apenas versões que NÃO são "versão anterior"
    ids_versao_anterior = set(versao_anterior_de.keys())

    for pid, peca in sorted(prioritarias.items()):
        # Pular versões anteriores
        if pid in ids_versao_anterior:
            skip += 1
            continue

        tipo   = peca["canonical_type"]
        folder = TIPOS[tipo]
        caminho = MACIEL_ROOT / peca["rel_path"]
        stub_path = WIKI_ROOT / "pecas" / folder / f"{pid}.md"

        if not caminho.exists() or not stub_path.exists():
            nao_local += 1
            continue

        if not arquivo_acessivel(caminho):
            nao_local += 1
            continue

        # Verificar PDF final
        pdf_path = encontrar_pdf_final(caminho)
        tem_pdf  = pdf_path is not None
        pdf_nome = pdf_path.name if pdf_path else ""

        # Tentar ler o conteúdo
        try:
            paras, texto = ler_docx_robusto(caminho)
        except Exception as e:
            erro_leitura += 1
            print(f"   ✗ Erro DOCX {pid}: {str(e)[:60]}")
            continue

        if len(texto) < 200:
            skip += 1
            continue

        tese      = sumarizar(paras, tipo)
        juris     = extrair_juris(texto)
        estrutura = detectar_estrutura(texto)

        atualizado = atualizar_stub_v3(
            stub_path, tese, juris, estrutura,
            caminho.name, tem_pdf, pdf_nome
        )
        if atualizado:
            ok += 1
            extraidos.append({
                "id":          pid,
                "tipo":        tipo,
                "arquivo":     caminho.name,
                "juris_count": len(juris),
                "estrutura":   estrutura,
                "tem_pdf":     tem_pdf,
                "pdf_nome":    pdf_nome,
            })
            pdf_marker = " 📄" if tem_pdf else ""
            print(f"   ✓ [{tipo[:20]}] {caminho.name[:45]}{pdf_marker}")
            print(f"     Juris: {len(juris)} | Estrutura: {estrutura}")
        else:
            skip += 1

    # ── RELATÓRIO ─────────────────────────────────────────────────────────────
    print(f"\n✅ Extração v3 concluída!")
    print(f"   Stubs atualizados:          {ok}")
    print(f"   Versões anteriores marcadas: {marcados}")
    print(f"   Skipped (já ok / curtos):   {skip}")
    print(f"   Não locais (cloud):         {nao_local}")
    print(f"   Erros de leitura:           {erro_leitura}")

    # Salvar relatório
    rel_path = WIKI_ROOT / "alertas" / f"extracao-report-v3-{TODAY}.md"
    rel_path.parent.mkdir(parents=True, exist_ok=True)

    linhas = [
        "---",
        f'title: "Relatório de Extração v3 — {TODAY}"',
        'category: "sistema"',
        f'created: "{TODAY}"',
        "---",
        "",
        f"# Extração Automática de DOCX v3 — {TODAY}",
        "",
        f"**Stubs atualizados:** {ok}",
        f"**Versões anteriores marcadas:** {marcados}",
        f"**Arquivos cloud-only (não processados):** {nao_local}",
        "",
        "## Grupos de versões detectados",
        "",
        f"Foram encontrados **{len(grupos_versoes)} grupos** com múltiplas versões da mesma peça.",
        "",
        "| Grupo | Principal | Versões anteriores |",
        "|:------|:----------|:-------------------|",
    ]

    for chave, entradas in grupos_versoes.items():
        cf, ct, yr, parties = chave
        pid_p, _, _, _, versoes_ant = escolher_versao_principal(entradas)
        ants_str = ", ".join(versoes_ant) if versoes_ant else "—"
        linhas.append(f"| [{yr}] {cf} — {ct[:20]} | {pid_p} | {ants_str} |")

    linhas += [
        "",
        "## Arquivos processados",
        "",
        "| ID | Tipo | Arquivo | Juris. | PDF final |",
        "|:---|:-----|:--------|:-------|:----------|",
    ]
    for e in extraidos:
        pdf_col = f"`{e['pdf_nome'][:35]}`" if e["tem_pdf"] else "—"
        linhas.append(
            f"| {e['id']} | {e['tipo'][:22]} | {e['arquivo'][:40]} | {e['juris_count']} | {pdf_col} |"
        )

    linhas += [
        "",
        "## ⚠️ Arquivos cloud-only — ação necessária",
        "",
        f"{nao_local} arquivos das peças prioritárias estão armazenados apenas no OneDrive.",
        "",
        "**Para processar esses arquivos:**",
        "1. No Windows Explorer, abrir a pasta `MACIEL PINHEIRO` no OneDrive",
        "2. Clicar com o botão direito → **'Sempre manter neste dispositivo'**",
        "3. Aguardar o download completo",
        "4. No Cowork, solicitar: *'Execute novamente a extração v3 de stubs'*",
        "",
        "*Após o download, o extrator_v3.py processará automaticamente os arquivos restantes.*",
    ]

    rel_path.write_text('\n'.join(linhas), encoding='utf-8')
    print(f"\n   Relatório salvo em: alertas/extracao-report-v3-{TODAY}.md")

if __name__ == "__main__":
    main()
