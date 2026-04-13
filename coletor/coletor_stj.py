import requests
import zipfile
import io
import os
import pandas as pd
import logging
import json

# ==============================
# CONFIGURAÇÃO BASE
# ==============================

CKAN_BASE = "https://dadosabertos.web.stj.jus.br"
DATAJUD_URL = "https://api-publica.datajud.cnj.jus.br/api_publica_stj/_search"
API_KEY = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="

os.makedirs("data", exist_ok=True)

# ==============================
# COLETA CKAN (PORTAL STJ)
# ==============================

def baixar_dados_stj():
    """
    Baixa os CSVs de jurisprudência do portal CKAN do STJ
    e normaliza conforme o dicionário de campos.
    """
    logging.info("📦 Buscando datasets no portal CKAN do STJ...")

    # Dataset principal (jurisprudência)
    dataset_url = f"{CKAN_BASE}/dataset/espelho-do-acordao"
    logging.info(f"🔗 {dataset_url}")

    # Download manual do arquivo ZIP
    resource_url = f"{CKAN_BASE}/storage/f/2024-10-10T14%3A00%3A00.000Z/espelho_acordaos.zip"
    resp = requests.get(resource_url)
    resp.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        csv_file = [f for f in z.namelist() if f.endswith(".csv")][0]
        logging.info(f"📁 Extraindo arquivo: {csv_file}")
        df = pd.read_csv(z.open(csv_file), sep=";", encoding="latin1", dtype=str)

    # Normaliza e salva
    df.columns = df.columns.str.lower().str.strip()
    df.to_csv("data/decisoes_stj_normalizado.csv", index=False, encoding="utf-8-sig")
    logging.info("✅ Base CKAN normalizada e salva em data/decisoes_stj_normalizado.csv")


# ==============================
# COLETA DATAJUD (API CNJ)
# ==============================

def coletar_datajud(query_text="responsabilidade civil", tamanho=200):
    """
    Coleta ementas e metadados de julgados do STJ via API DataJud.
    """
    headers = {
        "Authorization": f"APIKey {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "query": {
            "match": {
                "textoEmenta": query_text
            }
        },
        "size": tamanho
    }

    logging.info(f"🔍 Consultando API DataJud para termo '{query_text}'...")
    resp = requests.post(DATAJUD_URL, headers=headers, json=payload)
    resp.raise_for_status()
    data = resp.json()

    hits = data.get("hits", {}).get("hits", [])
    registros = []
    for h in hits:
        fonte = h.get("_source", {})
        registros.append({
            "numero_processo": fonte.get("dadosBasicos", {}).get("numero"),
            "classe": fonte.get("classeProcessual"),
            "orgao_julgador": fonte.get("orgaoJulgador"),
            "relator": fonte.get("relator"),
            "data_julgamento": fonte.get("dataJulgamento"),
            "ementa": fonte.get("textoEmenta"),
        })

    logging.info(f"✅ {len(registros)} registros coletados via API DataJud.")
    return registros


# ==============================
# INTEGRAÇÃO E SALVAMENTO
# ==============================

def unificar_bases():
    """
    Integra a base CKAN (CSV) e a base DataJud (API),
    normalizando com base no dicionário do STJ.
    """
    logging.info("🔄 Iniciando unificação das bases...")

    df_ckan = pd.read_csv("data/decisoes_stj_normalizado.csv", encoding="utf-8-sig", dtype=str)
    df_dict = pd.read_csv("data/dicionario-espelhodoacordao.csv", sep=";", encoding="utf-8", dtype=str)

    # Renomeia colunas do CKAN conforme dicionário (campo_nome → campo_título)
    mapa = dict(zip(df_dict["Campo"], df_dict["Título"]))
    df_ckan.rename(columns=mapa, inplace=True)

    # Importa resultados da API
    with open("data/datajud_resultados.json", encoding="utf-8") as f:
        datajud = json.load(f)

    df_api = pd.DataFrame(datajud)
    df_final = pd.concat([df_ckan, df_api], ignore_index=True)
    df_final.to_csv("data/jurisprudencia_unificada.csv", index=False, encoding="utf-8-sig")

    logging.info("💾 Base unificada salva em data/jurisprudencia_unificada.csv")


# ==============================
# PIPELINE HÍBRIDO
# ==============================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logging.info("🚀 Iniciando pipeline híbrido STJ + DataJud...")

    try:
        baixar_dados_stj()
    except Exception as e:
        logging.error(f"Erro ao baixar base CKAN: {e}")

    try:
        resultados_api = coletar_datajud("responsabilidade civil", tamanho=100)
        with open("data/datajud_resultados.json", "w", encoding="utf-8") as f:
            json.dump(resultados_api, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Erro ao coletar via API DataJud: {e}")

    try:
        unificar_bases()
    except Exception as e:
        logging.error(f"Erro na unificação: {e}")

    logging.info("🏁 Processo concluído.")
