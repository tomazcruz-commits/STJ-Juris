# Guia de Setup - Second Brain STJ

## 📋 Resumo Executivo

Este guia orienta você na configuração completa do Second Brain de jurisprudência do STJ, baseado na arquitetura de LLM Wiki de Andrej Karpathy. O sistema transforma seus dados brutos em uma base de conhecimento viva, interconectada e otimizada para consultas com Claude.

## ✅ Pré-requisitos

- Dados STJ já coletados em `/mnt/desktop/STJ JURIS/ARQUIVOS STJ/` (506 arquivos JSON, ~100+ MB)
- Claude API access (via Manus ou OpenAI)
- Obsidian instalado (recomendado para visualização)
- Python 3.11+ (já disponível no sandbox)
- Git (para versionamento da wiki)

## 🚀 Instalação Rápida (5 passos)

### Passo 1: Copiar Arquivos de Configuração

```bash
# Copiar para seu ambiente local
cp /home/ubuntu/CLAUDE.md ~/wiki_stj/
cp /home/ubuntu/STJ_Second_Brain_Architecture.md ~/wiki_stj/
```

### Passo 2: Inicializar a Wiki

```bash
# A wiki já foi inicializada em /home/ubuntu/wiki_stj/
# Estrutura criada:
ls -la ~/wiki_stj/
# Output esperado:
# - temas/
# - relatores/
# - orgaos/
# - classes/
# - sinteses/
# - index.md
# - log.md
# - CLAUDE.md
# - metadata.json
```

### Passo 3: Configurar Obsidian (Opcional mas Recomendado)

1. Instale Obsidian: https://obsidian.md/
2. Abra Obsidian e crie um novo vault apontando para `~/wiki_stj/`
3. Instale plugins recomendados:
   - **Obsidian Web Clipper**: Para capturar artigos web como markdown
   - **Dataview**: Para queries dinâmicas sobre frontmatter
   - **Marp**: Para gerar slides a partir de markdown
   - **Graph View**: Já nativo, mostra conexões entre páginas

4. Configure hotkeys úteis:
   - Ctrl+Shift+D: Download attachments for current file
   - Ctrl+E: Toggle edit/preview mode

### Passo 4: Preparar Dados Brutos

Os dados já estão em `/mnt/desktop/STJ JURIS/ARQUIVOS STJ/`. A estrutura é:

```
ARQUIVOS STJ/
├── 1ª SEÇÃO/          (50 arquivos JSON)
├── 2ª SEÇÃO/          (51 arquivos JSON)
├── 3ª SEÇÃO/          (51 arquivos JSON)
├── CORTE ESPECIAL/    (45 arquivos JSON)
├── PRIMEIRA TURMA/    (63 arquivos JSON)
├── QUARTA TURMA/      (52 arquivos JSON)
├── QUINTA TURMA/      (53 arquivos JSON)
├── SEGUNDA TURMA/     (38 arquivos JSON)
├── SEXTA TURMA/       (52 arquivos JSON)
└── TERCEIRA TURMA/    (51 arquivos JSON)
```

**Total**: 506 arquivos JSON, ~100+ MB, com dados de 2024-01-01 a 2026-03-31

### Passo 5: Primeira Ingestão com Claude

Você está pronto! Agora siga este fluxo com Claude:

```
Usuário: "Processe os dados de março/2026 do STJ seguindo o esquema em CLAUDE.md. 
Crie páginas iniciais para os 10 temas mais comuns, perfis dos 15 Ministros mais ativos,
e páginas para cada Turma/Seção."

Claude: [Lê CLAUDE.md, analisa dados, gera wiki com:
- 10 páginas temáticas
- 15 páginas de relatores
- 10 páginas de órgãos
- index.md atualizado
- log.md com registro de operações]
```

## 📁 Estrutura Final da Wiki

Após a primeira ingestão, sua wiki terá esta estrutura:

```
wiki_stj/
├── CLAUDE.md                           # Esquema de instruções
├── index.md                            # Catálogo central (atualizado)
├── log.md                              # Registro de operações
├── metadata.json                       # Metadados da wiki
│
├── temas/
│   ├── responsabilidade-civil.md
│   ├── direito-de-familia.md
│   ├── direito-contratual.md
│   ├── direito-processual.md
│   └── ... (10+ temas iniciais)
│
├── relatores/
│   ├── moura-ribeiro.md
│   ├── nancy-andrighi.md
│   ├── luis-felipe-salomao.md
│   └── ... (15+ Ministros)
│
├── orgaos/
│   ├── primeira-turma.md
│   ├── segunda-turma.md
│   ├── terceira-turma.md
│   ├── quarta-turma.md
│   ├── quinta-turma.md
│   ├── sexta-turma.md
│   ├── primeira-secao.md
│   ├── segunda-secao.md
│   ├── terceira-secao.md
│   └── corte-especial.md
│
├── classes/
│   ├── recurso-especial.md
│   ├── agravo-em-recurso-especial.md
│   ├── mandado-de-seguranca.md
│   └── ... (5+ classes principais)
│
├── sinteses/
│   └── (preenchido conforme consultas)
│
└── assets/
    └── (imagens e recursos)
```

## 🔄 Fluxos de Trabalho Contínuos

### Fluxo de Ingestão Mensal

```
1. Coletor STJ baixa novos dados
2. Você avisa Claude: "Processe os julgados de [MÊS/ANO]"
3. Claude:
   - Lê os novos JSONs
   - Atualiza páginas temáticas
   - Atualiza perfis de Ministros
   - Atualiza páginas de órgãos
   - Registra em log.md
   - Atualiza index.md
4. Você revisa as mudanças em Obsidian
```

### Fluxo de Consulta Cumulativa

```
1. Você pergunta ao Claude: "Como o STJ tem decidido sobre X?"
2. Claude:
   - Consulta index.md para encontrar páginas relevantes
   - Lê as páginas temáticas/de órgão
   - Sintetiza resposta com citações
   - Se a resposta é profunda, cria nova página na wiki
   - Registra em log.md
3. Você lê a resposta em Obsidian
4. A wiki fica mais rica para futuras consultas
```

### Fluxo de Manutenção Mensal

```
1. Você avisa Claude: "Execute lint na wiki"
2. Claude:
   - Procura contradições entre páginas
   - Identifica páginas órfãs
   - Sugere novas páginas para conceitos frequentes
   - Gera relatório de lint
3. Você revisa e aprova mudanças
4. Claude executa as correções
```

## 📖 Exemplos de Uso

### Exemplo 1: Pesquisar Jurisprudência

```
Usuário: "Qual é o entendimento consolidado do STJ sobre responsabilidade 
civil de plataformas digitais?"

Claude:
1. Lê wiki/index.md → encontra wiki/temas/responsabilidade-civil.md
2. Lê wiki/temas/responsabilidade-civil.md
3. Lê wiki/relatores/moura-ribeiro.md (se relevante)
4. Sintetiza resposta com 3-5 julgados emblemáticos
5. Se a resposta é nova, cria wiki/temas/responsabilidade-plataformas-digitais.md
6. Registra em log.md
```

### Exemplo 2: Comparar Posições de Ministros

```
Usuário: "Como Moura Ribeiro e Nancy Andrighi divergem em contratos?"

Claude:
1. Lê wiki/relatores/moura-ribeiro.md
2. Lê wiki/relatores/nancy-andrighi.md
3. Cria tabela comparativa
4. Cita julgados onde votaram diferente
5. Cria nova página: wiki/sinteses/divergencia-moura-nancy-contratos.md
```

### Exemplo 3: Analisar Tendência Temporal

```
Usuário: "Como evoluiu o entendimento sobre planos de saúde de 2024 a 2026?"

Claude:
1. Lê wiki/temas/direito-saude.md (ou cria se não existir)
2. Agrupa julgados por ano
3. Identifica mudanças de posição
4. Cria página: wiki/sinteses/evolucao-planos-saude-2024-2026.md
5. Registra em log.md
```

## 🛠️ Troubleshooting

### Problema: Claude não encontra páginas na wiki

**Solução**: Certifique-se de que:
1. O arquivo `index.md` está atualizado com todas as páginas
2. Os links internos usam `[[nome-da-pagina]]` (sintaxe Obsidian)
3. Não há typos nos nomes de arquivo

### Problema: Wiki fica desorganizada

**Solução**: Execute lint regularmente:
```
Usuário: "Execute lint na wiki e gere relatório de inconsistências"
```

### Problema: Consultas retornam respostas genéricas

**Solução**: A wiki ainda é pequena. Continue ingerindo dados e fazendo consultas. 
Após ~50-100 páginas temáticas, as respostas ficarão muito mais específicas.

## 📚 Recursos Adicionais

- **Arquitetura completa**: Leia `STJ_Second_Brain_Architecture.md`
- **Instruções para Claude**: Leia `CLAUDE.md`
- **Referência original**: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

## 🎯 Próximas Ações

1. **Hoje**: Ler este guia e `CLAUDE.md`
2. **Amanhã**: Instalar Obsidian e abrir a wiki
3. **Esta semana**: Fazer primeira ingestão com Claude
4. **Próximas semanas**: Explorar a wiki, fazer consultas, deixar crescer

---

**Criado por**: Manus AI  
**Data**: 2026-04-08  
**Versão**: 1.0
