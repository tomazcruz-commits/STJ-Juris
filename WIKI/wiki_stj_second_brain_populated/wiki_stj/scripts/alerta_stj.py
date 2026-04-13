#!/usr/bin/env python3
"""
alerta_stj.py — Sistema de Alertas de Novos Julgados
Novoa Prado Maciel Pinheiro Advogados

Faz varredura no portal de jurisprudência do STJ por palavras-chave
relevantes à prática do escritório e gera um digest semanal em Markdown.

Saída: wiki_stj/alertas/digest-AAAA-MM-DD.md
"""

import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

# ─── CONFIGURAÇÃO ─────────────────────────────────────────────────────────────

WIKI_ROOT   = Path("/sessions/elegant-great-clarke/mnt/STJ JURIS/WIKI/wiki_stj_second_brain_populated/wiki_stj")
ALERTAS_DIR = WIKI_ROOT / "alertas"
TODAY       = datetime.today().strftime("%Y-%m-%d")
SEMANA_ATRAS = (datetime.today() - timedelta(days=7)).strftime("%d/%m/%Y")
HOJE_BR     = datetime.today().strftime("%d/%m/%Y")

# ─── TÓPICOS DE INTERESSE ─────────────────────────────────────────────────────
# Organizados por área — editar conforme a prática evolui

TOPICOS = {
    "Bem de família / Impenhorabilidade": [
        "bem de família",
        "impenhorabilidade",
        "Lei 8.009",
        "imóvel residencial único",
        "fiador locação penhora",
    ],
    "Dano moral / Responsabilidade civil": [
        "dano moral quantum",
        "responsabilidade civil empresarial",
        "dano moral pessoa jurídica",
        "dano estético cumulação",
        "nexo causal responsabilidade",
    ],
    "Execução civil / Penhora": [
        "prescrição intercorrente execução",
        "penhora salário",
        "cumprimento de sentença multa",
        "bloqueio BACENJUD SISBAJUD",
        "fraude à execução",
        "desconsideração personalidade jurídica",
    ],
    "Direito do consumidor": [
        "CDC instituição financeira",
        "cláusula abusiva bancária",
        "negativação indevida dano moral",
        "inscrição SPC SERASA indevida",
        "plano de saúde cobertura",
        "previdência privada aberta",
    ],
    "Inadimplemento contratual": [
        "resolução contratual perdas danos",
        "inadimplemento contratual lucros cessantes",
        "cláusula penal redução equitativa",
        "teoria do adimplemento substancial",
    ],
    "Recursos / Admissibilidade": [
        "prequestionamento ficto art. 1.025",
        "Súmula 7 reexame prova exceção",
        "taxatividade mitigada art. 1.015",
        "honorários recursais art. 85 §11",
    ],
    "Recuperação judicial / Falência": [
        "habilitação crédito recuperação",
        "impugnação plano recuperação",
        "trava bancária recuperação judicial",
        "stay period recuperação",
    ],
}

# ─── BUSCA NO STJ ─────────────────────────────────────────────────────────────

STJ_API = "https://processo.stj.jus.br/SCON/pesquisar.jsp"

def buscar_stj(termo: str, data_ini: str, data_fim: str, max_results: int = 5) -> list:
    """
    Busca na API pública do STJ por termo e intervalo de datas.
    Retorna lista de dicts com dados básicos do julgado.
    """
    params = {
        "b": "ACOR",
        "livre": f'"{termo}"',
        "dtde": data_ini,
        "dtat": data_fim,
        "tp": "T",
        "p": "true",
        "l": str(max_results),
        "i": "1",
        "operador": "e",
        "tipo_visualizacao": "RESUMO",
        "formato": "HTML",
    }

    url = STJ_API + "?" + urllib.parse.urlencode(params)
    resultados = []

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; STJ-Monitor/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        # Parser simples — extrai número do processo e ementa
        import re
        # Padrão de número de processo STJ
        processos = re.findall(r'(REsp|AREsp|AgInt|EDcl|RHC|HC|MS)\s+n[ºo°]?\s*[\d.,/-]+', html, re.IGNORECASE)
        ementas_raw = re.findall(r'EMENTA[:\s]+(.{100,500}?)(?:ACÓRDÃO|DECISÃO|Vistos|$)', html, re.IGNORECASE | re.DOTALL)

        for i, proc in enumerate(processos[:max_results]):
            ementa = ementas_raw[i].strip()[:300] if i < len(ementas_raw) else "—"
            ementa = re.sub(r'\s+', ' ', ementa)
            resultados.append({
                "processo": proc,
                "ementa_trecho": ementa,
                "url_busca": url,
            })

    except Exception as e:
        resultados.append({
            "processo": "ERRO",
            "ementa_trecho": f"Falha na consulta: {str(e)[:100]}",
            "url_busca": url,
        })

    return resultados

# ─── GERADOR DE DIGEST ────────────────────────────────────────────────────────

def gerar_digest(resultados_por_topico: dict) -> str:
    total = sum(len(v) for v in resultados_por_topico.values() if isinstance(v, list))

    linhas = [
        f"---",
        f'title: "Digest de Alertas STJ — {TODAY}"',
        f"category: \"alertas\"",
        f"created: \"{TODAY}\"",
        f"periodo: \"{SEMANA_ATRAS} a {HOJE_BR}\"",
        f"total_resultados: {total}",
        f"---",
        "",
        f"# Digest STJ — {TODAY}",
        "",
        f"> Período monitorado: **{SEMANA_ATRAS}** a **{HOJE_BR}**",
        f"> Total de resultados relevantes encontrados: **{total}**",
        "",
        "---",
        "",
    ]

    for topico, resultados in resultados_por_topico.items():
        linhas.append(f"## {topico}")
        linhas.append("")

        if not resultados:
            linhas.append("*Nenhum resultado novo neste período.*")
            linhas.append("")
            continue

        for r in resultados:
            if r.get("processo") == "ERRO":
                linhas.append(f"⚠️ **Erro na consulta:** {r['ementa_trecho']}")
                linhas.append("")
                continue

            linhas.append(f"### {r['processo']}")
            linhas.append("")
            linhas.append(f"> {r['ementa_trecho']}...")
            linhas.append("")
            linhas.append(f"[Buscar no STJ]({r['url_busca']})")
            linhas.append("")

        linhas.append("---")
        linhas.append("")

    linhas += [
        "## Ações sugeridas",
        "",
        "- [ ] Revisar resultados relevantes e clipar acórdãos de interesse ([[web-clipper-workflow]])",
        "- [ ] Verificar impacto nos casos ativos",
        "- [ ] Atualizar páginas de temas se houver mudança de entendimento",
        "",
        f"*Gerado automaticamente em {TODAY}. Ver [[alertas/index]] para histórico.*",
    ]

    return "\n".join(linhas)

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    print(f"🔍 Iniciando varredura STJ — período: {SEMANA_ATRAS} a {HOJE_BR}")

    ALERTAS_DIR.mkdir(parents=True, exist_ok=True)

    resultados_por_topico = {}

    for area, termos in TOPICOS.items():
        print(f"\n📌 {area}")
        area_resultados = []

        for termo in termos:
            print(f"   → '{termo}'", end=" ")
            res = buscar_stj(termo, SEMANA_ATRAS, HOJE_BR, max_results=3)
            # Filtrar erros e deduplicar por número de processo
            processos_vistos = set()
            for r in res:
                if r["processo"] != "ERRO" and r["processo"] not in processos_vistos:
                    area_resultados.append(r)
                    processos_vistos.add(r["processo"])
                    print(f"✓ ({r['processo']})", end=" ")
            print()

        resultados_por_topico[area] = area_resultados[:5]  # máx 5 por área

    # Gerar digest
    digest_path = ALERTAS_DIR / f"digest-{TODAY}.md"
    conteudo = gerar_digest(resultados_por_topico)
    digest_path.write_text(conteudo, encoding="utf-8")

    # Atualizar índice
    _atualizar_indice()

    total = sum(len(v) for v in resultados_por_topico.values())
    print(f"\n✅ Digest gerado: {digest_path}")
    print(f"   {total} resultados em {len(TOPICOS)} áreas monitoradas")

def _atualizar_indice():
    idx_path = ALERTAS_DIR / "index.md"
    digests = sorted(ALERTAS_DIR.glob("digest-*.md"), reverse=True)

    linhas = [
        "---",
        'title: "Alertas STJ — Histórico"',
        'category: "alertas"',
        f'updated: "{TODAY}"',
        "---",
        "",
        "# Alertas STJ — Histórico",
        "",
        "| Data | Arquivo | Período |",
        "|:-----|:--------|:--------|",
    ]

    for d in digests[:20]:
        data = d.stem.replace("digest-", "")
        linhas.append(f"| {data} | [[alertas/{d.stem}]] | Semana anterior |")

    linhas += [
        "",
        "---",
        "",
        "## Tópicos monitorados",
        "",
    ]
    for topico in TOPICOS.keys():
        linhas.append(f"- {topico}")

    linhas += [
        "",
        "---",
        "",
        "Para adicionar ou remover tópicos, editar `scripts/alerta_stj.py` → seção `TOPICOS`.",
    ]

    idx_path.write_text("\n".join(linhas), encoding="utf-8")

if __name__ == "__main__":
    main()
