# Arquitetura do Second Brain STJ: Base de Conhecimento Jurisprudencial

A implementação de um "Second Brain" para a jurisprudência do Superior Tribunal de Justiça (STJ), inspirada na abordagem de Andrej Karpathy, transforma um repositório estático de metadados em uma base de conhecimento viva, interconectada e otimizada para interação com Modelos de Linguagem de Grande Escala (LLMs) como o Claude. Esta arquitetura visa resolver o problema clássico de recuperação de informações jurídicas, substituindo a busca tradicional por uma síntese contínua e cumulativa.

## Visão Geral do Sistema

O sistema é composto por três camadas fundamentais que separam os dados originais da síntese gerada pela inteligência artificial. Esta separação garante a integridade das fontes primárias enquanto permite que a base de conhecimento evolua organicamente.

A primeira camada consiste nas **Fontes Brutas (Raw Sources)**. No contexto do STJ, esta camada é representada pelos arquivos JSON já existentes na pasta `STJ JURIS/ARQUIVOS STJ`, organizados por turmas e seções. Estes arquivos contêm os metadados originais dos julgamentos, incluindo ementas, relatores, datas e classes processuais. Esta camada é estritamente imutável; o LLM apenas lê estas informações, garantindo que a fonte da verdade permaneça inalterada e auditável [1].

A segunda camada é a **Wiki Jurisprudencial**, o coração do Second Brain. Trata-se de um diretório estruturado de arquivos Markdown (`.md`) que o LLM gera e mantém de forma autônoma. Em vez de simplesmente recuperar ementas a cada consulta, o Claude compila resumos temáticos, cria páginas para teses jurídicas recorrentes, mapeia a evolução do entendimento de relatores específicos e estabelece conexões entre julgados similares. O usuário interage com esta camada através de uma interface como o Obsidian, consumindo o conhecimento já sintetizado e interligado [1].

A terceira camada é o **Esquema (Schema)**, materializado em um arquivo de configuração (como `CLAUDE.md`). Este documento atua como o "cérebro do cérebro", instruindo o Claude sobre como a wiki deve ser estruturada, quais convenções de nomenclatura adotar para processos e temas, e quais fluxos de trabalho seguir durante a ingestão de novos acórdãos ou na resposta a consultas complexas [1].

## Estrutura de Diretórios Proposta

Para acomodar esta arquitetura, propõe-se a seguinte organização de diretórios dentro do ambiente do usuário:

| Diretório/Arquivo | Descrição e Propósito |
| :--- | :--- |
| `raw/` | Repositório imutável contendo os JSONs originais do STJ, organizados por órgão julgador. |
| `wiki/` | O Second Brain propriamente dito, contendo todos os arquivos Markdown gerados pelo Claude. |
| `wiki/temas/` | Sínteses de teses jurídicas, organizadas por ramos do direito (ex: Responsabilidade Civil, Direito de Família). |
| `wiki/relatores/` | Perfis analíticos da jurisprudência de cada Ministro, destacando posicionamentos consolidados. |
| `wiki/orgaos/` | Análises de tendências e divergências entre as diferentes Turmas e Seções do STJ. |
| `wiki/index.md` | Catálogo central mantido pelo LLM, listando todas as páginas da wiki com breves resumos e metadados. |
| `wiki/log.md` | Registro cronológico (append-only) de todas as operações de ingestão, consultas e manutenções realizadas. |
| `CLAUDE.md` | O arquivo de esquema com as instruções de sistema para o comportamento do agente LLM. |

## Fluxos de Operação (Workflows)

A manutenção e expansão do Second Brain ocorrem através de três operações principais, executadas pelo Claude sob a supervisão do usuário.

### 1. Ingestão Contínua (Ingest)

A ingestão é o processo de incorporar novos julgamentos à base de conhecimento. Quando o script `coletor_stj.py` baixa novos dados do STJ, o Claude é acionado para processá-los. O modelo lê os novos acórdãos, identifica os temas centrais e atualiza as páginas correspondentes na wiki. Se um novo julgado consolida uma tese inédita, uma nova página temática é criada. Se altera um entendimento anterior, a página existente é revisada com a devida anotação temporal. Todo este processo é registrado no arquivo `log.md`, garantindo rastreabilidade [1].

### 2. Consulta Cumulativa (Query)

Diferente de sistemas RAG (Retrieval-Augmented Generation) tradicionais que recomeçam do zero a cada pergunta, as consultas neste Second Brain são cumulativas. Quando o usuário questiona o Claude sobre a evolução da jurisprudência em contratos de plano de saúde, o modelo consulta o `index.md`, acessa as páginas temáticas relevantes e sintetiza uma resposta. O diferencial crucial é que análises profundas, tabelas comparativas ou novas conexões descobertas durante a resposta são **arquivadas de volta na wiki** como novas páginas. Assim, cada exploração enriquece permanentemente a base de conhecimento [1].

### 3. Manutenção e Higienização (Lint)

Para evitar a degradação da base de conhecimento, o Claude executa rotinas periódicas de verificação (linting). O modelo varre a wiki em busca de contradições entre páginas temáticas, identifica entendimentos que foram superados por julgamentos recentes (overruling), localiza páginas órfãs sem links de entrada e sugere a criação de novos verbetes para conceitos jurídicos frequentemente mencionados, mas ainda não aprofundados. Esta manutenção proativa garante a integridade e a confiabilidade da pesquisa jurisprudencial [1].

## Integração Tecnológica

A implementação técnica desta arquitetura aproveita as ferramentas já presentes no ambiente do usuário. O script `coletor_stj.py` continuará responsável pela extração dos dados brutos via API do DataJud e portal CKAN do STJ. O banco de dados PostgreSQL (definido em `stj_schema.sql`) pode atuar como um índice auxiliar para buscas textuais rápidas, complementando a navegação semântica da wiki.

Para a interface de usuário, recomenda-se fortemente o uso do **Obsidian**. Como um editor Markdown local, ele permite a visualização imediata da wiki gerada pelo Claude. Funcionalidades nativas do Obsidian, como o *Graph View*, oferecem uma representação visual poderosa das conexões entre diferentes teses e relatores, revelando a topologia da jurisprudência do STJ de uma forma impossível em sistemas de busca tradicionais [1].

## Referências

[1] Karpathy, A. (2026). *LLM Wiki*. GitHub Gist. https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
