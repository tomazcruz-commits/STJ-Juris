# Como usar a Busca Semântica do STJ

## Pré-requisitos (instalar uma vez)

Abra o PowerShell e rode:

```powershell
pip install sentence-transformers faiss-cpu numpy tqdm
```

---

## Passo 1 — Gerar os embeddings (uma única vez, ~2-4h)

Este passo processa os 638k acórdãos e gera os vetores semânticos.
**Pode ser interrompido e retomado** — ele continua de onde parou.

```powershell
cd "C:\Users\tomaz\OneDrive\Documentos\STJ JURIS\WIKI\wiki_stj_second_brain_populated\wiki_stj\scripts"
python stj_semantic_indexer.py
```

O script vai criar a pasta `STJ JURIS\embeddings\` com:
- `stj_embeddings.npy` — matriz de vetores
- `stj_embeddings_ids.npy` — IDs dos acórdãos
- `stj_embeddings_meta.json` — progresso e metadados
- `stj_index.faiss` — índice FAISS para busca rápida (~61MB)

> 💡 **Dica:** rode à noite e deixe processar. Usa ~1-2GB de RAM durante a indexação.
> Se a máquina for reiniciada, rode novamente — ele retoma do ponto de parada.

---

## Passo 2 — Buscar (após a indexação)

### Via terminal (PowerShell):

```powershell
# Busca híbrida (padrão — combina BM25 + semântica)
python stj_busca_hibrida.py "penhorabilidade bem de família execução condomínio"

# Só semântica (melhor para conceitos abstratos)
python stj_busca_hibrida.py "afastamento penhora imóvel residencial" --modo semantico

# Só BM25 (melhor para termos específicos, números de súmulas)
python stj_busca_hibrida.py "Súmula 364 STJ" --modo bm25

# Mais resultados, com peso maior no semântico
python stj_busca_hibrida.py "responsabilidade objetiva banco" --k 30 --alpha 0.7

# Output JSON para integração com Obsidian
python stj_busca_hibrida.py "prazo decadencial plano saúde" --json > resultado.json
```

### Via Cowork (pedir ao Claude):

Simplesmente descreva o que precisa. Por exemplo:
> *"Busque acórdãos do STJ sobre penhorabilidade de bem de família em execução de cotas condominiais"*

---

## Exemplos de consultas semânticas que só funcionam com embeddings

| Consulta semântica | O que encontra |
|:---|:---|
| `"afastamento penhora imóvel residencial"` | Casos de impenhorabilidade mesmo sem registro formal |
| `"banco cobrou tarifa indevida dano moral"` | Responsabilidade civil bancária por cobranças abusivas |
| `"médico recusou atendimento urgência plano"` | Negativa de cobertura em emergência |
| `"desconsideração personalidade jurídica grupo empresarial"` | Teoria maior e menor da desconsideração |
| `"prescrição interrompida notificação extrajudicial"` | Efeitos de interpelações na prescrição |

Essas consultas **não funcionam bem com BM25** porque os acórdãos usam terminologia diferente da consulta. Com embeddings, o modelo entende que "imóvel residencial" e "bem de família" são semanticamente próximos.

---

## Parâmetros de ajuste fino

| Parâmetro | Valor | Quando usar |
|:---|:---|:---|
| `--alpha 0.3` | Mais peso no BM25 | Consultas com termos técnicos precisos (súmulas, números) |
| `--alpha 0.5` | Equilíbrio (padrão) | Consultas mistas |
| `--alpha 0.7` | Mais peso semântico | Consultas conceituais, linguagem natural |
| `--modo semantico` | 100% semântico | Conceitos jurídicos abstratos |
| `--modo bm25` | 100% lexical | Termos exatos, sem embeddings disponíveis |

---

## Integração com Obsidian

Após uma busca, você pode copiar o output e colar diretamente em uma nota do vault, ou usar o script com `--json` para gerar um arquivo que o Dataview pode indexar.

Exemplo de nota gerada automaticamente:

```markdown
---
query: "penhorabilidade bem de família condomínio"
data_busca: "2026-04-11"
modo: hibrido
---

## Resultados

| # | Classe | Data | Relator | Ementa |
|---|--------|------|---------|--------|
| 1 | REsp | 2023 | Min. X | ... |
```

---

## Arquitetura técnica

```
Consulta do usuário
       │
       ▼
┌──────────────────────────────────────────────┐
│              BuscaHibrida.buscar()            │
│                                              │
│  ┌─────────────┐      ┌───────────────────┐  │
│  │  FTS5/BM25  │      │  Embeddings FAISS  │  │
│  │ (stj_mini.db│      │ (stj_index.faiss)  │  │
│  │  decisoes_  │      │  paraphrase-multi  │  │
│  │   _fts)     │      │   lingual-mpnet    │  │
│  └──────┬──────┘      └────────┬──────────┘  │
│         │ rank_bm25            │ rank_sem     │
│         └──────────┬───────────┘              │
│                    ▼                          │
│           RRF Fusion (α=0.5)                  │
│         score = (1-α)/RRF_bm25               │
│                + α/RRF_sem                    │
└──────────────────────────────────────────────┘
       │
       ▼
Top-K acórdãos rankeados por relevância híbrida
```

**Modelo:** `paraphrase-multilingual-mpnet-base-v2`
- 768 dimensões
- Treinado em 50+ idiomas incluindo português
- Excelente para similaridade semântica de frases jurídicas
- Tamanho: ~275MB (baixado automaticamente na primeira execução)

**Índice:** FAISS IVFPQ
- 638k vetores em ~61MB (Product Quantization 8x)
- Busca approximate nearest neighbor em <100ms
- Roda sem GPU
