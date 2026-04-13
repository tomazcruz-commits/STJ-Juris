import os
import json
import pandas as pd

BASE_DIR = r"C:\Users\tomaz\OneDrive\Área de Trabalho\STJ JURIS\ARQUIVOS STJ"
OUT_FILE = "stj_unificado.csv"

def ler_json(caminho):
    with open(caminho, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            print(f"⚠️ Erro ao ler {caminho}")
            return []

def processar_arquivo(caminho, orgao):
    dados = ler_json(caminho)
    registros = []
    for item in dados:
        registros.append({
            "orgao": orgao,
            "id_acordao": item.get("id_acordao"),
            "processo": item.get("numero_processo"),
            "relator": item.get("relator"),
            "ementa": item.get("ementa"),
            "acordao": item.get("acordao"),
            "data_julgamento": item.get("data_julgamento"),
            "data_publicacao": item.get("data_publicacao"),
            "classe": item.get("classe"),
            "assunto": item.get("assunto"),
            "resultado": item.get("resultado"),
        })
    return registros

def unificar():
    todos = []

    for pasta in os.listdir(BASE_DIR):
        pasta_completa = os.path.join(BASE_DIR, pasta)

        if os.path.isdir(pasta_completa):
            print(f"\n📁 Lendo pasta: {pasta}")

            for arquivo in os.listdir(pasta_completa):
                if arquivo.endswith(".json"):
                    caminho = os.path.join(pasta_completa, arquivo)
                    print(f"   ➜ Processando {arquivo}")

                    registros = processar_arquivo(caminho, pasta)
                    todos.extend(registros)

    df = pd.DataFrame(todos)
    df.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")

    print("\n✅ Arquivo unificado gerado:", OUT_FILE)
    print("📊 Total de registros:", len(df))

if __name__ == "__main__":
    unificar()
