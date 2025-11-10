# Estrutura inicial do projeto STJ-Juris

## Pastas
- **coletor** → scripts para coleta dos dados do STJ (API CKAN)
- **api** → servidor FastAPI para expor /buscar_juris
- **db** → scripts SQL e config do PostgreSQL
- **embeddings** → geração dos vetores semânticos
- **reflexum_connector** → integração entre GPT Jurídico e base STJ
- **data** → datasets e arquivos CSV/JSON brutos baixados

## Objetivo
Sistema local de Jurimetria e Recuperação de Jurisprudência do STJ integrado ao GPT Jurídico Reflexum.
