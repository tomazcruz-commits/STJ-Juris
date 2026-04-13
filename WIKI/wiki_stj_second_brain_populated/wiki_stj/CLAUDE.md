# CLAUDE.md - Esquema de Manutenção do Second Brain STJ

## ⚡ Início de Sessão — Ler Primeiro

Antes de qualquer tarefa de redação, análise ou estratégia, ler:

1. `about-me/about-me.md` — identidade, prática e metodologia de Tomaz
2. `about-me/anti-ai-writing-style.md` — regras de linguagem: proibições absolutas e checklist
3. `about-me/my-escritorio.md` — contexto estratégico do escritório (ler quando relevante)

Entregáveis vão em `OUTPUTS/`. Scaffolding de peças em `TEMPLATES/`.

---

## Propósito

Este arquivo define como você (Claude) deve estruturar, manter e evoluir o Second Brain de jurisprudência do STJ. Ele é o contrato entre o usuário e você sobre como a wiki deve funcionar.

## Princípios Fundamentais

1. **Você é o dono da wiki.** O usuário cuida das fontes brutas (raw/). Você gera e mantém todo o conteúdo em `wiki/`. O usuário raramente edita a wiki manualmente.

2. **A wiki é um artefato cumulativo.** Cada ingestão, cada consulta, cada descoberta deixa a wiki mais rica. Nada desaparece no histórico de chat.

3. **Imutabilidade das fontes.** Você lê os JSONs em `raw/` mas nunca os modifica. Eles são a fonte de verdade.

4. **Rastreabilidade total.** Todo grande evento (ingestão, lint, descoberta importante) é registrado em `wiki/log.md` com timestamp.

## Estrutura da Wiki

### Diretórios Principais

```
wiki/
├── index.md                 # Catálogo central de tudo
├── log.md                   # Registro cronológico de operações
├── temas/                   # Teses jurídicas por ramo do direito
│   ├── responsabilidade-civil.md
│   ├── direito-de-familia.md
│   ├── direito-contratual.md
│   └── ...
├── relatores/               # Perfis de Ministros
│   ├── moura-ribeiro.md
│   ├── nancy-andrighi.md
│   └── ...
├── orgaos/                  # Análises por Turma/Seção
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
├── classes/                 # Análises por classe processual
│   ├── agravo-em-recurso-especial.md
│   ├── recurso-especial.md
│   ├── mandado-de-seguranca.md
│   └── ...
└── sínteses/                # Análises transversais
    ├── evolucao-jurisprudencia-2025-2026.md
    ├── divergencias-entre-turmas.md
    └── ...
```

### Convenções de Nomenclatura

- **Arquivos temáticos**: Use nomes em kebab-case, descritivos. Ex: `responsabilidade-civil.md`, não `tema1.md`.
- **Frontmatter YAML**: Cada página deve começar com metadados:
  ```yaml
  ---
  title: "Responsabilidade Civil"
  category: "temas"
  created: "2026-04-08"
  updated: "2026-04-08"
  sources: 5
  related: ["direito-contratual", "moura-ribeiro"]
  ---
  ```
- **Links internos**: Use `[[nome-da-pagina]]` para criar referências cruzadas que o Obsidian reconhece.

## Operações Principais

### 1. INGEST - Processar Novos Julgamentos

**Quando**: Após o `coletor_stj.py` baixar novos dados.

**Processo**:

1. Leia os novos arquivos JSON em `raw/ARQUIVOS STJ/[ÓRGÃO]/[DATA].json`.
2. Para cada julgado, extraia: número do processo, classe, relator, data, ementa, decisão.
3. Identifique os **temas jurídicos centrais** (ex: responsabilidade civil, contratos, família).
4. Identifique o **órgão julgador** (turma/seção).
5. Atualize as páginas temáticas correspondentes:
   - Se é a primeira menção de um tema, crie `wiki/temas/novo-tema.md`.
   - Se o tema já existe, adicione o novo julgado à seção de jurisprudência recente.
   - Revise a síntese geral se o novo julgado muda o entendimento consolidado.
6. Atualize a página do relator em `wiki/relatores/` com o novo julgado.
7. Atualize a página do órgão em `wiki/orgaos/` com o novo julgado.
8. Atualize `wiki/index.md` com novos verbetes ou mudanças.
9. Adicione entrada em `wiki/log.md`:
   ```
   ## [2026-04-08] ingest | Processamento de 50 julgados de março/2026
   - Novos temas criados: 3
   - Temas atualizados: 12
   - Relatores com novos julgados: 8
   ```

**Dica**: Você pode processar lotes (ex: todos os julgados de um mês) de uma vez, ou ingerir fontes uma a uma com mais supervisão do usuário. Documente qual abordagem você está usando.

### 2. QUERY - Responder Consultas

**Quando**: O usuário faz uma pergunta sobre jurisprudência.

**Processo**:

1. Leia `wiki/index.md` para entender o escopo da wiki.
2. Identifique as páginas temáticas, de órgão ou de relator relevantes.
3. Leia essas páginas em profundidade.
4. Sintetize uma resposta com citações de julgados específicos.
5. **Se a resposta é profunda e reutilizável**, crie uma nova página na wiki:
   - Ex: Usuário pergunta "Como o STJ tem decidido sobre responsabilidade de plataformas digitais?" → Você cria `wiki/temas/responsabilidade-plataformas-digitais.md`.
   - Adicione links cruzados para páginas relacionadas.
   - Registre em `wiki/log.md`: `## [2026-04-08] query | Nova página criada: responsabilidade-plataformas-digitais.md`.

**Importante**: Não deixe análises valiosas desaparecerem no histórico de chat. Elas pertencem à wiki.

### 3. LINT - Verificação de Saúde

**Quando**: Periodicamente (ex: mensalmente ou a cada 50 ingestões).

**Processo**:

1. Varre todas as páginas temáticas procurando por:
   - **Contradições**: Duas páginas afirmam coisas opostas? Resolva com julgados mais recentes.
   - **Obsolescência**: Há afirmações que julgados recentes tornaram obsoletas? Atualize com anotação de data.
   - **Órfãos**: Páginas sem links de entrada? Adicione referências cruzadas ou considere mesclar.
   - **Lacunas**: Conceitos frequentemente mencionados mas sem página própria? Crie novas páginas.
   - **Inconsistência**: Diferentes páginas usam terminologia diferente para o mesmo conceito? Padronize.

2. Gere um relatório de lint em `wiki/lint-report-[DATA].md`:
   ```
   # Relatório de Lint - 2026-04-08
   
   ## Contradições Encontradas
   - Página X e Y divergem sobre tema Z. Resolução: Atualizar X com julgado mais recente.
   
   ## Páginas Órfãs
   - `wiki/temas/direito-antigo.md` não tem links de entrada. Sugestão: Mesclar com `direito-contratual.md`.
   
   ## Lacunas Sugeridas
   - Conceito "Boa-fé contratual" é mencionado 15 vezes mas não tem página própria. Criar?
   ```

3. Registre em `wiki/log.md`:
   ```
   ## [2026-04-08] lint | Verificação de saúde completa
   - Contradições resolvidas: 2
   - Páginas órfãs identificadas: 1
   - Novas páginas sugeridas: 3
   ```

## Arquivo index.md

O `index.md` é o mapa da wiki. Deve ser atualizado a cada ingestão. Formato:

```markdown
# Índice da Wiki STJ

## Temas Jurídicos
| Tema | Página | Descrição | Julgados | Última Atualização |
| :--- | :--- | :--- | :--- | :--- |
| Responsabilidade Civil | [[responsabilidade-civil]] | Indenizações, danos morais, culpa | 42 | 2026-04-08 |
| Direito de Família | [[direito-de-familia]] | Divórcio, alimentos, guarda | 28 | 2026-04-07 |

## Relatores
| Relator | Página | Julgados | Especialidade |
| :--- | :--- | :--- | :--- |
| Moura Ribeiro | [[moura-ribeiro]] | 156 | Direito Processual |
| Nancy Andrighi | [[nancy-andrighi]] | 143 | Direito Civil |

## Órgãos Julgadores
| Órgão | Página | Julgados | Tendência |
| :--- | :--- | :--- | :--- |
| Primeira Turma | [[primeira-turma]] | 234 | Conservadora |
| Terceira Turma | [[terceira-turma]] | 189 | Progressista |
```

## Arquivo log.md

Registro cronológico append-only. Formato consistente para parsing:

```markdown
# Log de Operações

## [2026-04-08] ingest | Processamento de 50 julgados de março/2026
Novos temas: 3. Temas atualizados: 12. Relatores: 8.

## [2026-04-07] query | Análise de responsabilidade de plataformas digitais
Criada página: `wiki/temas/responsabilidade-plataformas-digitais.md`

## [2026-04-06] lint | Verificação mensal
Contradições resolvidas: 2. Páginas órfãs: 1. Lacunas: 3.
```

## Diretrizes de Conteúdo

### Páginas Temáticas

Uma página temática deve incluir:

1. **Definição**: O que é este conceito jurídico?
2. **Evolução**: Como o STJ tem entendido isso ao longo do tempo?
3. **Jurisprudência Consolidada**: Qual é o entendimento dominante? Com quantos julgados?
4. **Divergências**: Há posições minoritárias? Quais órgãos as adotam?
5. **Julgados Representativos**: Liste 3-5 acórdãos emblemáticos com links para o STJ.
6. **Referências Cruzadas**: Links para temas relacionados e relatores relevantes.
7. **Última Atualização**: Data e número de julgados considerados.

### Páginas de Relatores

Uma página de relator deve incluir:

1. **Perfil**: Nome completo, data de posse, especialidades.
2. **Estatísticas**: Total de julgados, taxa de provimento/desprovimento, temas principais.
3. **Posicionamento Jurídico**: Qual é a linha jurisprudencial deste Ministro? Conservador? Progressista? Pragmático?
4. **Julgados Emblemáticos**: 3-5 acórdãos que definem seu pensamento.
5. **Divergências Conhecidas**: Com quais colegas este Ministro mais diverge?
6. **Evolução Temporal**: Mudou de posição ao longo dos anos?

### Páginas de Órgão

Uma página de órgão julgador deve incluir:

1. **Composição**: Quais Ministros integram esta Turma/Seção?
2. **Competência**: Quais tipos de processos julga?
3. **Estatísticas**: Total de julgados, taxa de provimento, temas principais.
4. **Tendência Geral**: A Turma é mais conservadora ou progressista?
5. **Divergências Internas**: Há divisões dentro da Turma?
6. **Julgados Emblemáticos**: Acórdãos que definem a jurisprudência da Turma.

## Quando Pedir Ajuda

Existem situações em que você deve pausar e pedir orientação do usuário:

1. **Contradição irreconciliável**: Dois julgados recentes contradizem um entendimento consolidado. Qual prevalece?
2. **Classificação ambígua**: Um julgado toca múltiplos temas. Onde deve ser arquivado?
3. **Atualização de schema**: O usuário quer mudar a estrutura da wiki (ex: adicionar novo diretório). Confirme.
4. **Decisão editorial**: Deve-se criar uma página para um conceito que aparece apenas 2 vezes? Ou é muito niche?

## Checklist de Qualidade

Antes de finalizar qualquer operação (ingest, query, lint), verifique:

- [ ] Todos os links internos estão corretos (sem typos em `[[nomes-de-paginas]]`)?
- [ ] O frontmatter YAML está presente e correto?
- [ ] As páginas relacionadas têm referências cruzadas?
- [ ] O `index.md` foi atualizado?
- [ ] O `log.md` foi atualizado com um entry consistente?
- [ ] Não há duplicação de conteúdo entre páginas?
- [ ] As citações de julgados incluem número do processo e data?
- [ ] A linguagem é clara e acessível, mesmo para não-juristas?

## Próximos Passos

1. **Primeira ingestão**: Processe os julgados de março/2026 (últimos dados disponíveis).
2. **Criação de páginas iniciais**: Gere páginas para os 10 temas mais comuns nos dados.
3. **Perfis de relatores**: Crie páginas para os 15 Ministros mais ativos.
4. **Estrutura de órgãos**: Crie páginas para as 10 Turmas/Seções.
5. **Índice inicial**: Gere `wiki/index.md` com tudo que foi criado.
6. **Log inicial**: Inicie `wiki/log.md` com um entry de bootstrap.

Depois disso, a wiki está pronta para operações contínuas de ingestão, consulta e manutenção.
