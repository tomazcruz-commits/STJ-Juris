---
title: "Web Clipper — Workflow de Captura de Acórdãos"
category: "sistema"
created: "2026-04-11"
updated: "2026-04-11"
---

# Web Clipper — Workflow de Captura de Acórdãos

> Como capturar um acórdão relevante do STJ (ou TJPE) e integrá-lo na wiki
> de forma estruturada, sem retrabalho.

---

## Ferramentas necessárias

1. **Obsidian Web Clipper** — extensão de browser (Chrome/Firefox)
   - Instalar em: `obsidian://` → Configurações → Web Clipper
   - Ou diretamente: [obsidian.md/clipper](https://obsidian.md/clipper)

2. **Template de captura** (configurar no Web Clipper — ver seção abaixo)

3. **Pasta de destino:** `wiki_stj/temas/` ou `wiki_stj/sinteses/` conforme o caso

---

## Configuração do Template no Web Clipper

No Web Clipper, criar um template chamado **"Acórdão STJ"** com o seguinte conteúdo:

```markdown
---
title: "{{title}}"
source: "{{url}}"
captured: "{{date}}"
tribunal: ""
classe: ""
numero: ""
relator: ""
orgao: ""
data_julgamento: ""
temas: []
sumulas: []
type: "acordao-capturado"
status: "para-revisar"
---

# {{title}}

**Fonte:** {{url}}
**Capturado em:** {{date}}

---

## Ementa

{{selection}}

---

## Notas de análise

<!-- O que este acórdão resolve? Qual a tese? Como se encaixa na wiki? -->

---

## Links para a wiki

- Tema relacionado: [[temas/]]
- Súmulas aplicadas: [[sumulas/]]

```

**Pasta de destino padrão:** `wiki_stj/sinteses/capturados/`

---

## Workflow passo a passo

### Passo 1 — Encontrar o acórdão

**No site do STJ** (stj.jus.br):
1. Pesquisar no campo de jurisprudência
2. Abrir o acórdão que interessa
3. Selecionar o trecho da ementa (ou o texto completo, se curto)

**No TJPE** (tjpe.jus.br):
1. Mesma lógica — selecionar o trecho relevante antes de clipar

### Passo 2 — Clipar

1. Clicar no ícone do Web Clipper no browser
2. Selecionar o template **"Acórdão STJ"**
3. Verificar se o texto selecionado está correto no campo `{{selection}}`
4. Salvar → vai para `wiki_stj/sinteses/capturados/`

### Passo 3 — Revisar e integrar (pode ser feito com Claude)

Abrir o arquivo capturado e:

1. Preencher os campos do frontmatter: classe, número, relator, órgão, data de julgamento
2. Identificar o(s) tema(s) jurídico(s) do acórdão
3. Verificar se existe página de tema correspondente em `temas/` — se sim, adicionar referência cruzada
4. Verificar se há súmulas aplicadas — adicionar links para `sumulas/`
5. Escrever as **Notas de análise**: o que o acórdão decide, qual a relevância para a prática

### Passo 4 — Decidir onde arquivar

| Situação | Destino |
|:---|:---|
| Acórdão confirma/aprofunda tema já existente | Adicionar à página do tema em `temas/` |
| Acórdão é pioneiro ou muda entendimento | Criar nova página em `temas/` + link da captura |
| Acórdão é relevante para um caso específico | Adicionar ao stub da peça em `pecas/` |
| Acórdão é apenas referência pontual | Manter em `sinteses/capturados/` com links cruzados |

---

## Integração com Claude

Após clipar, você pode abrir uma sessão e dizer:

> "Acabei de clipar o acórdão [NÚMERO]. Está em `sinteses/capturados/`. Integra na wiki."

Claude vai:
1. Ler o arquivo capturado
2. Identificar o tema jurídico
3. Atualizar a página de tema correspondente (ou criar uma nova)
4. Adicionar wikilinks cruzados
5. Registrar em `log.md`

---

## Sites úteis para captura

| Fonte | URL | O que capturar |
|:---|:---|:---|
| STJ — Jurisprudência | stj.jus.br/sites/portalp/Jurisprudencia | Ementas e acórdãos |
| STJ — Temas Repetitivos | stj.jus.br/repetitivos | Teses vinculantes |
| TJPE — Jurisprudência | tjpe.jus.br/jurisprudencia | Acórdãos do TJ local |
| Jusbrasil | jusbrasil.com.br | Busca agregada (verificar fonte original) |
| LexML | lexml.gov.br | Legislação + jurisprudência consolidada |

> ⚠️ **Regra:** Sempre verificar o acórdão na fonte oficial (STJ/TJPE) antes de citar. O Jusbrasil é útil para encontrar, mas a citação deve vir da fonte original.

---

## Manutenção da pasta `capturados/`

Mensalmente (ou quando acumular mais de 10 arquivos), revisar `sinteses/capturados/`:
- Arquivos com status `para-revisar` há mais de 30 dias → integrar ou descartar
- Arquivos já integrados → mover para `sinteses/arquivados/` ou deletar

O LINT do vault ([[CLAUDE.md#3-lint-verificação-de-saúde]]) também identifica arquivos capturados não integrados como potenciais orphan notes.
