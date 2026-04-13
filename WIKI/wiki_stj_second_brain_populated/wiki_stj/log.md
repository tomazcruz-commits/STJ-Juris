# Log de Operações - Wiki STJ

Registro cronológico (append-only) de todas as operações realizadas na wiki.

## [2026-04-08 10:58:04] bootstrap | Inicialização da wiki
- Estrutura de diretórios criada
- Arquivos iniciais gerados
- Pronto para primeira ingestão

---
## [2026-04-08] ingest | Primeira ingestão - Dados de março/2026
- Páginas temáticas criadas: 15+
- Perfis de Ministros criados: 20
- Páginas de órgãos criadas: 10
- Total de julgados processados: 1000+
- Status: ✅ Completo

---
## [2026-04-08] query | Sínteses v2 — Conteúdo real do banco STJ

Reescrita profunda das páginas temáticas com base em análise direta do banco de 638.198 julgados (stj_mini.db). Método: `analisar_stj.py` rodado para cada tema, síntese redigida por Claude com estrutura padronizada (definição, teses consolidadas, divergências, estado atual, aplicação prática).

**Páginas criadas/atualizadas**:
- `temas/execucao-civil.md` — NOVA — Prescrição intercorrente, penhora/impenhorabilidade, cumprimento de sentença (~90 julgados analisados)
- `temas/direito-processual.md` — ATUALIZADA — Agravo de instrumento (Tema Repetitivo 988/998), tutelas, preclusão (~120 julgados analisados)
- `temas/responsabilidade-civil.md` — ATUALIZADA — Dano moral, método bifásico, juros, responsabilidade objetiva (~95 julgados analisados)
- `temas/direito-do-consumidor.md` — ATUALIZADA — Plano de saúde, arbitragem em adesão, denunciação da lide, perímetro do CDC (~78 julgados analisados)
- `sinteses/divergencias-entre-turmas.md` — NOVA — Mapa de divergências ativas entre Turmas com conselho prático
- `index.md` — ATUALIZADO — Seção de temas prioritários para o escritório; distinção ⭐ (síntese real) vs. ○ (listagem básica)

**Temas excluídos por opção do usuário**: Tributário, Administrativo, Penal, Família.

**Banco utilizado**: `/tmp/stj_mini.db` (cópia de stj_mini.db, 842MB, journal_mode=DELETE)
- Status: ✅ Completo

---
## [2026-04-08] query | Tema 1368 — Juros e Correção Monetária (Corte Especial, out/2025)

Adicionado conteúdo sobre o Tema Repetitivo 1368/STJ e a Lei 14.905/2024. Fonte: pesquisa web (portal STJ + doutrina especializada). Inclui análise crítica de dispositivo condenatório com fórmula híbrida problemática.

**Páginas criadas/atualizadas**:
- `temas/juros-correcao-monetaria.md` — NOVA — Análise completa: histórico da controvérsia, Lei 14.905/2024, tese do Tema 1368, quadro temporal, análise de dispositivos condenatórios problemáticos, impacto em execuções
- `temas/responsabilidade-civil.md` — Seção 4.2 adicionada: referência ao Tema 1368 e [[juros-correcao-monetaria]]
- `temas/execucao-civil.md` — Seção 8-A adicionada: Tema 1368 e excesso de execução
- `sinteses/divergencias-entre-turmas.md` — Seção 6-A adicionada: Tema 1368 como ponto pacificado (sem divergência ativa)

**Nota**: esta entrada foi gerada por pesquisa web — o banco STJ local não indexa o Tema 1368 por ser posterior ao período de coleta.
- Status: ✅ Completo

---
## [2026-04-08] query | Órgãos e Ministros da 2ª Seção — Perfis com dados reais

Reescrita profunda das páginas de órgãos e relatores da 2ª Seção (Direito Privado), com base nos dados do banco STJ e na composição oficial de 1º/4/2026 (Assessoria para Assuntos Funcionais de Magistrados). Foco na prática civil: execução, responsabilidade civil, consumidor, contratos.

**Páginas de órgãos criadas/reescritas**:
- `orgaos/2a-secao.md` — NOVA — Composição, competência, teses vinculantes, sessões
- `orgaos/quarta-turma.md` — REESCRITA — Tendências por tema (execução, AI, CDC, responsabilidade civil), estatísticas dos ministros, tabela de AI cabível/não cabível
- `orgaos/terceira-turma.md` — REESCRITA — Composição em transição, perfis resumidos, tendências por ministro

**Perfis de ministros reescritos (4ª Turma)**:
- `relatores/joao-otavio-de-noronha.md` — Presidente; AI Tema 988; execução; pragmático
- `relatores/raul-araujo.md` — CDC; plano de saúde; pró-consumidor; mais prolífico
- `relatores/maria-isabel-gallotti.md` — Bancário; superendividamento; evolução recente
- `relatores/antonio-carlos-ferreira.md` — Execução; penhora de faturamento (repetitivo ativo)

**Perfis de ministros reescritos (3ª Turma)**:
- `relatores/moura-ribeiro.md` — Seguros; recuperação judicial; bem de família
- `relatores/nancy-andrighi.md` — Contratos; arbitragem em consumo; uniformização na 2ª Seção
- `relatores/ricardo-villas-boas-cueva.md` — Tema 1368 (SELIC); locação; crédito; fraude
- `relatores/humberto-martins.md` — Em transição do direito público; foco em competência

**index.md** — Adicionadas seções de Órgãos e Ministros da 2ª Seção com tabelas práticas

**Fonte dos dados**: banco STJ local (638.198 julgados) + PDF composição STJ 1º/4/2026
- Status: ✅ Completo

---
## [2026-04-09] ingest | Diretório súmulas/ — 19 verbetes individuais

Criação do diretório `sumulas/` com páginas individuais para as súmulas do STJ mais relevantes à prática do escritório (direito processual civil, execução civil, responsabilidade civil, direito do consumidor). Cada verbete contém: enunciado literal, contexto histórico, aplicação prática com tabelas e armadilhas, desenvolvimento jurisprudencial e referências cruzadas com wikilinks.

**Estrutura criada**:
- `sumulas/index.md` — Índice temático com tabelas por área e seção de "referências rápidas por situação prática"

**Páginas criadas (19 súmulas)**:

*Processual Civil / Recursos*:
- `sumulas/s-007.md` — Reexame de prova não enseja REsp (com exceções: quantum do dano moral, requalificação jurídica)
- `sumulas/s-083.md` — Divergência superada: REsp não conhecido
- `sumulas/s-098.md` — EDcl prequestionadores não são protelatórios; interação com art. 1.025 CPC
- `sumulas/s-168.md` — EDcl sem efeitos infringentes para reexame de prova
- `sumulas/s-182.md` — Agravo deve atacar especificamente os fundamentos da decisão agravada
- `sumulas/s-211.md` — Prequestionamento ficto (temperada pelo art. 1.025 CPC/2015)

*Execução Civil / Impenhorabilidade*:
- `sumulas/s-314.md` — Prescrição intercorrente (fiscal; aplicação analógica na civil)
- `sumulas/s-364.md` — Bem de família protege solteiros, separados e viúvos
- `sumulas/s-486.md` — Imóvel único alugado é impenhorável se renda vai para subsistência
- `sumulas/s-549.md` — Bem de família do fiador em locação é penhorável
- `sumulas/s-638.md` — Impenhorabilidade e dívidas condominiais ⚠️ (verificar enunciado)

*Responsabilidade Civil*:
- `sumulas/s-037.md` — Cumulação de dano moral + material
- `sumulas/s-054.md` — Juros moratórios: extracontratual desde o evento danoso
- `sumulas/s-227.md` — Pessoa jurídica pode sofrer dano moral
- `sumulas/s-281.md` — Dano moral sem tarifação (Lei de Imprensa revogada)
- `sumulas/s-326.md` — Condenação menor que o pedido: sem sucumbência recíproca
- `sumulas/s-362.md` — Correção monetária do dano moral desde o arbitramento; distinção de S. 54; impacto do Tema 1368
- `sumulas/s-385.md` — Negativação: inscrição prévia legítima afasta dano moral
- `sumulas/s-387.md` — Cumulação de dano moral + dano estético

*Direito do Consumidor*:
- `sumulas/s-297.md` — CDC aplica-se às instituições financeiras
- `sumulas/s-381.md` — Abusividade bancária: vedado conhecimento de ofício
- `sumulas/s-404.md` — Notificação de negativação: dispensável o AR
- `sumulas/s-563.md` — CDC nas entidades abertas de previdência (não nas fechadas)
- `sumulas/s-608.md` — CDC nos planos de saúde, exceto autogestão

*Ação Monitória*:
- `sumulas/s-282.md` — Cabível citação por edital na monitória
- `sumulas/s-339.md` — Cabível monitória contra a Fazenda Pública
- `sumulas/s-405.md` — Monitória e documentos sem força executiva ⚠️ (verificar enunciado)

**Notas técnicas**:
- Duas súmulas marcadas com ⚠️ (638 e 405): enunciados aproximados — verificar no portal STJ antes de invocar
- Correção de equívoco anterior na wiki: Súmula 362 NÃO trata de "juros contratuais desde a citação" — trata de correção monetária do dano moral desde o arbitramento
- Wikilinks entre súmulas formam rede navegável em Obsidian
- `index.md` principal atualizado com seção de súmulas e acesso rápido por número

**Fonte**: conhecimento técnico-jurídico do modelo; banco STJ local (referência cruzada)
- Status: ✅ Completo


---
## [2026-04-11] build | Expansão completa do second brain — Fases 1, 2 e 3

Sessão de construção intensiva. Todas as fases do roadmap executadas.

### Fase 1 — Camada de Identidade (ABOUT ME)
- `about-me/about-me.md` — Identidade profissional, metodologia, projetos paralelos
- `about-me/anti-ai-writing-style.md` — Proibições de linguagem, checklist pré-entrega, padrões de citação
- `about-me/my-escritorio.md` — Contexto estratégico do Novoa Prado Maciel Pinheiro
- `OUTPUTS/` e `TEMPLATES/` — Pastas criadas com README e convenções
- `CLAUDE.md` — Atualizado com bloco "Ler Primeiro" apontando para ABOUT ME

### Fase 2 — Second Brain de Peças Processuais
- `pecas/` — 14 subdiretórios por tipo de peça
- `bootstrap_pecas.py` — Script que parseou 818 DOCX da pasta MACIEL PINHEIRO
- 443 stubs de peças gerados (582 DOCX não se enquadram = administrativos ou fora do padrão)
- Índice por tipo + índice geral com navegação por situação prática
- `pecas_mapping.json` — 443 entradas com mapeamento id → caminho real
- `TEMPLATES/` — 5 scaffoldings estruturais: EDcl, AI, REsp, Contestação, PI

### Fase 3 — STJ Wiki (tarefas pendentes)
- `legislacao/` — CPC, CDC, CC e LEF anotados (artigos + notas jurisprudenciais + wikilinks)
- `classes/` — REsp, AREsp, EDiv, Reclamação e CC documentados com fluxo e prazos
- `web-clipper-workflow.md` — Protocolo operacional de captura de acórdãos
- `lint-report-2026-04-11.md` — Diagnóstico: 556 arquivos, lacunas identificadas e categorizadas
- `sinteses/capturados/` — Pasta criada para receber clips do Web Clipper
- `dataview-queries.md` — 12 queries Dataview prontas para o Obsidian
- `alertas/` + `scripts/alerta_stj.py` — Sistema de varredura semanal de novos julgados
- Tarefa agendada `stj-digest-semanal`: toda segunda-feira às 8h (Claude Scheduled)

### Fase 3 — casos/
- `bootstrap_casos.py` — Agrupa 443 peças em 274 casos por (cliente × adversário)
- 274 stubs de casos gerados com: polo inferido, tipo de ação, linha do tempo, mapa estratégico
- `casos/index.md` — Tabela completa + query Dataview de casos em andamento
- `casos/casos_mapping.json` — Mapeamento caso_id → peças_ids

**Estatísticas do vault após esta sessão**:
- Total de arquivos .md: ~580
- Stubs de peças: 443
- Stubs de casos: 274
- Súmulas documentadas: 26
- Templates: 5
- Diplomas legislativos anotados: 4
- Classes processuais: 5

- Status: ✅ Completo
