import requests
import json

url = "https://api-publica.datajud.cnj.jus.br/api_publica_stj/_search"

headers = {
    "Authorization": "APIKey cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw==",
    "Content-Type": "application/json"
}

query = {
    "query": {
        "match": {
            "textoEmenta": "responsabilidade civil"
        }
    },
    "size": 3
}

response = requests.post(url, headers=headers, json=query)

if response.status_code == 200:
    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
else:
    print("Erro:", response.status_code, response.text)
