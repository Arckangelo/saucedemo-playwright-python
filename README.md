# SauceDemo E2E — Python + Playwright

[![E2E Tests](https://github.com/Arckangelo/saucedemo-playwright-python/actions/workflows/e2e-tests.yml/badge.svg)](https://github.com/Arckangelo/saucedemo-playwright-python/actions/workflows/e2e-tests.yml)
[![Security](https://github.com/Arckangelo/saucedemo-playwright-python/actions/workflows/security.yml/badge.svg)](https://github.com/Arckangelo/saucedemo-playwright-python/actions/workflows/security.yml)
[![CodeQL](https://github.com/Arckangelo/saucedemo-playwright-python/actions/workflows/codeql.yml/badge.svg)](https://github.com/Arckangelo/saucedemo-playwright-python/actions/workflows/codeql.yml)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-1.64-2EAD33?logo=playwright&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-9.1-0A9EDC?logo=pytest&logoColor=white)

📊 [Relatório HTML da última execução na `main`](https://arckangelo.github.io/saucedemo-playwright-python/) (publicado pelo CI) · 🐞 [Bugs encontrados](BUGS.md) · [Relatório de bugs (PDF)](docs/relatorio-de-bugs.pdf)

Suíte de testes automatizados **end-to-end** para o [SauceDemo (Swag Labs)](https://www.saucedemo.com), loja virtual de demonstração da Sauce Labs feita para praticar automação.

### Em resumo

- **O que testa:** login, catálogo, detalhe do produto, carrinho, checkout e menu, com os **6 perfis de usuário** do site.
- **Tamanho:** **87 execuções** de teste: 49 verificam o que deve funcionar e 38 documentam bugs conhecidos.
- **O que encontrou:** **25 bugs**. 8 afetam todos os usuários, inclusive o padrão (por exemplo, um pedido de $0.00 concluído com o carrinho vazio); os outros 17 são os defeitos que o site injeta de propósito nos perfis de treino. Cada bug tem issue, evidência e teste ([lista](BUGS.md)).
- **Como os bugs ficam na suíte:** cada bug é um teste que descreve o comportamento **correto** e aparece como falha esperada (XFAIL). Se o site corrigir o bug, o teste avisa.
- **Por que dá para confiar nos testes:** preços e totais conferidos contra uma tabela de referência (não contra a própria tela), estado conferido no `localStorage` e no cookie, qualquer erro JavaScript reprova o teste, seletores por `data-test` e uma [análise de mutação](#análise-de-mutação) que não encontra mais testes fracos.
- **CI:** GitHub Actions a cada push e pull request, execução diária e [relatório publicado](https://arckangelo.github.io/saucedemo-playwright-python/).
- **Para rodar:** `pip install -r requirements.txt && playwright install chromium && pytest` (detalhes em [Como executar](#como-executar)).

<p align="center"><img src="docs/img/resumo-projeto.png" width="420" alt="Resumo do projeto: 8 defeitos que afetam todos os usuários do SauceDemo, inclusive o padrão, mais 17 defeitos de treino que o site injeta de propósito nos perfis especiais (8 no problem_user, 5 no error_user e 4 no visual_user), também mapeados e testados; execuções de teste passaram de 24 para 87, cobrindo os 6 perfis de usuário; 25 issues no GitHub, cada uma com evidência; CI 6 vezes mais rápido a cada push, de 101 s para 17 s. Destaque do BUG-001: até o usuário padrão conclui um pedido com o carrinho vazio, com total de $0.00."></p>

> Este projeto complementa meu [projeto em Cypress/JavaScript](https://github.com/Arckangelo/automationexercise-cypress-tests).

---

## Sumário

- [Destaques](#destaques)
- [Tecnologias](#tecnologias)
- [Como executar](#como-executar)
- [O que é testado](#o-que-é-testado)
- [Engenharia reversa e bugs encontrados](#engenharia-reversa-e-bugs-encontrados)
- [Análise de mutação](#análise-de-mutação)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Relatórios e depuração](#relatórios-e-depuração)
- [Integração contínua](#integração-contínua)
- [Segurança do pipeline](#segurança-do-pipeline)
- [Decisões técnicas](#decisões-técnicas)
- [Autor](#autor)

---

## Destaques

- **87 execuções de teste** a partir de 42 cenários, usando parametrização, cobrindo os **6 perfis de usuário** do site.
- **Engenharia reversa documentada**: [requisitos inferidos](docs/requisitos-inferidos.md) do comportamento observado, com mapa de fluxos e matriz usuário × funcionalidade.
- **25 defeitos documentados** (8 que afetam todos os usuários e 17 de treino dos perfis especiais), 24 deles cobertos por testes em vez de ignorados, com [relatório completo e evidências](docs/relatorio-de-bugs.md) e [uma issue por bug](https://github.com/Arckangelo/saucedemo-playwright-python/issues?q=label%3Abug). O BUG-023, um bug de tempo, tem um script de reprodução controlada. Resumo rápido em [BUGS.md](BUGS.md).
- **Análise de mutação com os próprios perfis do site:** os testes do `standard_user` rodam com o `problem_user` e o `error_user` (`--base-user`). Nenhum teste sobrevive numa funcionalidade que o perfil quebra (na versão anterior, 2 sobreviviam), e a análise revelou o [BUG-025](docs/relatorio-de-bugs.md#bug-025). Ver [Análise de mutação](#análise-de-mutação).
- **Page Object Model**: cada tela do site é uma classe, então os testes ficam curtos e legíveis.
- **Suíte rápida:** login feito uma única vez por usuário e execução em paralelo com pytest-xdist; no CI, cerca de 17 s a cada push e 33 s na suíte completa.
- **Relatório HTML** com screenshot automático de cada falha.
- **CI no GitHub Actions** a cada push e pull request.
- **Pipeline com DevSecOps**: detecção de segredos, auditoria de dependências e análise estática a cada mudança.

---

## Tecnologias

| Ferramenta | Para que serve |
|---|---|
| [Python 3.13](https://www.python.org/) | Linguagem |
| [Playwright](https://playwright.dev/python/) | Controla o navegador |
| [pytest](https://docs.pytest.org/) | Executa os testes, com fixtures e parametrização |
| [pytest-playwright](https://github.com/microsoft/playwright-pytest) | Integra o Playwright ao pytest |
| [pytest-html](https://pytest-html.readthedocs.io/) | Gera o relatório HTML |
| [pytest-xdist](https://pytest-xdist.readthedocs.io/) | Distribui os testes entre os núcleos da máquina (execução paralela) |
| [GitHub Actions](https://docs.github.com/actions) | Roda a suíte automaticamente na nuvem |
| gitleaks, pip-audit, Dependabot e CodeQL | Segurança do pipeline (ver [seção própria](#segurança-do-pipeline)) |

---

## Como executar

**Pré-requisitos:** Python 3.10 ou superior e Git.

### 1. Instalação (apenas na primeira vez)

```bash
# Baixar o projeto
git clone https://github.com/Arckangelo/saucedemo-playwright-python.git
cd saucedemo-playwright-python

# Criar e ativar um ambiente virtual
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# Instalar as dependências e o navegador
pip install -r requirements.txt
playwright install chromium
```

### 2. Rodar os testes

```bash
pytest
```

Ao final, abra `reports/report.html` no navegador para ver o resultado.

### Comandos úteis

| Comando | O que faz |
|---|---|
| `pytest` | Roda todos os testes, um por vez, sem abrir o navegador |
| `pytest -n auto` | Roda em paralelo, um processo por núcleo (o mesmo que o CI usa) |
| `pytest -n auto -m "not known_bug"` | Execução rápida do push: só o que deve passar, em paralelo |
| `pytest --headed --slowmo 500` | Mostra o navegador e desacelera cada ação, útil para acompanhar |
| `pytest -m smoke` | Roda só os fluxos críticos |
| `pytest -m known_bug` | Roda só os testes que documentam bugs conhecidos |
| `pytest -m regression` | Roda a regressão por perfil de usuário e os cenários de borda |
| `pytest -m "not known_bug" --base-user problem_user` | Análise de mutação: roda os testes do `standard_user` com um perfil defeituoso |
| `pytest tests/test_login.py` | Roda um único arquivo |
| `pytest -k ordenacao` | Roda os testes cujo nome contém o termo |
| `pytest --browser firefox` | Roda no Firefox (requer `playwright install firefox`) |

---

## O que é testado

| Área | Cenário | Execuções |
|---|---|:---:|
| **Login** | Usuários válidos acessam a loja (`standard`, `problem`, `performance_glitch`, `error`, `visual`) | 5 |
| | Login inválido mostra a mensagem certa (bloqueado, senha errada, usuário inexistente, campos vazios) | 5 |
| | Páginas internas exigem login (inventário, detalhe, carrinho e as três telas do checkout) | 6 |
| | Cookie de sessão adulterado não dá acesso (usuário inexistente, bloqueado, maiúsculas) | 3 |
| | Logout encerra a sessão de verdade | 1 |
| **Catálogo** | Ordenação por nome (A–Z, Z–A) e por preço (menor e maior) | 4 |
| | Cada produto exibe a própria imagem | 2 |
| | Adicionar atualiza o contador e o botão | 1 |
| | Remover o último item esconde o contador e volta o botão | 1 |
| | Reset App State volta os botões para "Add to cart" | 1 |
| **Detalhe do produto** | Clicar no produto abre o detalhe dele | 1 |
| | A URL `?id=N` abre o produto certo | 6 |
| | Produto inexistente não entra no carrinho (pela URL e pelo `localStorage`) | 3 |
| **Menu** | All Items volta ao inventário; About aponta para a Sauce Labs | 3 |
| **Carrinho e checkout** | Compra completa pela tela, do inventário ao pedido concluído, conferindo cada item | 1 |
| | Resumo calcula subtotal, imposto de 8% e total com a tabela de preços | 1 |
| | Concluir o pedido esvazia o carrinho no `localStorage` | 1 |
| | Formulário exige nome, sobrenome e CEP | 3 |
| | Formulário rejeita campos só com espaços | 3 |
| | Não conclui pedido com o carrinho vazio | 1 |
| | Resumo do checkout exige o passo 1 (nome, sobrenome e CEP) | 1 |
| | Carrinho continua salvo após recarregar a página, com os ids certos no `localStorage` | 1 |
| | Carrinho mostra nome, preço e quantidade 1 de cada produto | 1 |
| | Remover do carrinho mantém os demais itens após recarregar | 1 |
| **Saúde técnica** | Rotas respondem HTTP 200; telemetria sem erros (erros JavaScript são conferidos em todos os testes) | 2 |
| **problem_user** | Ordenação, adicionar e remover cada produto, detalhe, sobrenome, subtotal do resumo e carrinho após o pedido | 11 |
| **error_user** | Ordenação, adicionar e remover cada produto, sobrenome e botão Finish | 10 |
| **visual_user** | Preços, imagens e layout comparados com o `standard_user` | 8 |
| | **Total** | **87** |

Das 87 execuções, 49 passam e 38 documentam bugs conhecidos como falha esperada (`xfail`).

### Perfis de usuário

O SauceDemo oferece usuários com comportamentos diferentes. Os defeitos do `problem_user`, do `error_user` e do `visual_user` são injetados de propósito pelo site, para treino; a suíte mapeia e automatiza cada um:

| Usuário | Comportamento | Como é testado |
|---|---|---|
| `standard_user` | Funciona normalmente, mas compartilha os 8 bugs que afetam todos os usuários (ex.: pedido concluído com o carrinho vazio) | Base de todos os fluxos e **oráculo** dos outros perfis; 8 bugs registrados (7 como falhas conhecidas e 1 com script de reprodução) |
| `locked_out_user` | Bloqueado no login | Verifica a mensagem de bloqueio, inclusive com cookie forjado |
| `problem_user` | Defeitos de interface: imagens, ordenação, botões, detalhe errado, formulário e subtotal em dobro | 8 bugs registrados como falhas conhecidas |
| `performance_glitch_user` | ~5 s de atraso sempre que o inventário é renderizado | Usa um tempo de espera maior, sem pausas fixas; tempos medidos nos [requisitos](docs/requisitos-inferidos.md#tempos-do-performance_glitch_user) |
| `error_user` | Falhas funcionais com erros JavaScript: ordenação, botões, sobrenome e Finish | 5 bugs registrados como falhas conhecidas |
| `visual_user` | Diferenças visuais: preços aleatórios, imagem trocada e elementos fora do lugar | Comparado com o `standard_user` em tempo de execução; 4 bugs registrados |

---

## Engenharia reversa e bugs encontrados

Sem acesso a especificação, os requisitos do site foram deduzidos do comportamento observado, e
cada perfil foi comparado com o `standard_user`.

| Documento | Conteúdo |
|---|---|
| [Requisitos inferidos](docs/requisitos-inferidos.md) | Mapa de telas (Mermaid), 20 regras de negócio, como funcionam cookie, `localStorage` e URL, matriz usuário × funcionalidade e tempos do `performance_glitch_user` |
| [Relatório de bugs](docs/relatorio-de-bugs.md) ([PDF](docs/relatorio-de-bugs.pdf)) | 25 bugs confirmados (8 que afetam todos os usuários e 17 de treino dos perfis especiais; 2 críticos, 4 altos, 12 médios, 7 baixos), 4 suspeitas e comportamentos intencionais, com passos, evidências e o teste (ou o script de reprodução) de cada um |
| [Issues dos bugs](https://github.com/Arckangelo/saucedemo-playwright-python/issues?q=label%3Abug) | Uma issue por bug confirmado, com severidade, passos para reproduzir, evidências e o teste que a cobre |
| [Sugestões de melhoria](docs/sugestoes-de-melhoria.md) | Melhorias para a aplicação e para este projeto, com esforço e impacto |

Destaques entre os defeitos que afetam todos os usuários: o `standard_user` consegue concluir um
pedido de $0.00 com o carrinho vazio ou, digitando a URL do resumo, sem nome nem endereço de entrega
([BUG-024](docs/relatorio-de-bugs.md#bug-024)); e o paralelismo da própria suíte revelou uma condição de
corrida no menu do site ([BUG-023](docs/relatorio-de-bugs.md#bug-023)): investigada a partir do
trace do Playwright e reproduzida com a CPU 30x mais lenta, ela deixa o menu aberto porém
invisível. Entre os defeitos de treino, o `visual_user` vê um preço no catálogo e paga outro, e o
`error_user` não consegue finalizar a compra.

---

## Análise de mutação

O `problem_user`, o `error_user` e o `visual_user` são o mesmo site com defeitos injetados: são
"mutantes" prontos. Rodar os testes do `standard_user` com eles mostra quais asserções são fracas:
um teste que continua passando numa funcionalidade que o perfil quebra não a protege.

```bash
pytest -m "not known_bug" --base-user problem_user
```

| | Antes da revisão da suíte | Agora |
|---|:-:|:-:|
| Testes que usam o usuário base | 20 | 24 |
| Pegos com `problem_user` | 11 (55%) | 14 (58%) |
| Pegos com `error_user` | 9 (45%) | 13 (54%) |
| **Sobreviventes numa funcionalidade quebrada** | **2** | **0** |

A análise reforçou um teste que só adicionava os produtos que esses perfis conseguem adicionar e
revelou o [BUG-025](docs/relatorio-de-bugs.md#bug-025) (subtotal em dobro no `problem_user`). Os
sobreviventes restantes estão em funcionalidades que o perfil não quebra, cada um justificado na
[tabela completa](docs/analise-de-mutacao.md).

---

## Estrutura do projeto

```
saucedemo-playwright-python/
├── .github/
│   ├── dependabot.yml     # Atualizações semanais de dependências pip e das actions
│   ├── scripts/
│   │   └── pip_audit_severidade.py  # Faz o pip-audit falhar só em severidade alta/crítica
│   └── workflows/
│       ├── e2e-tests.yml  # Suíte de testes
│       ├── security.yml   # Segredos (gitleaks) e dependências vulneráveis (pip-audit)
│       └── codeql.yml     # Análise estática do Python e dos workflows
├── data/
│   └── constants.py       # Usuários, produtos, ids e mensagens esperadas
├── docs/
│   ├── analise-de-mutacao.md     # Testes do standard_user rodados com os perfis defeituosos
│   ├── requisitos-inferidos.md   # Engenharia reversa: fluxos, regras e matriz de usuários
│   ├── relatorio-de-bugs.md      # Bugs confirmados, suspeitas e evidências
│   ├── relatorio-de-bugs.pdf     # O mesmo relatório em PDF (A4), gerado pelo script abaixo
│   ├── sugestoes-de-melhoria.md  # Melhorias para a aplicação e para o projeto
│   ├── evidencias/               # Screenshots e logs citados no relatório
│   └── img/                      # Imagem-resumo do topo deste README e o HTML que a gera
├── pages/                 # Page Objects (uma classe por tela)
│   ├── base_page.py
│   ├── header.py          # Cabeçalho comum (carrinho e menu lateral)
│   ├── login_page.py
│   ├── inventory_page.py
│   ├── product_detail_page.py
│   ├── cart_page.py
│   ├── cart_rows.py       # Leitura das linhas (nome, preço, quantidade) do carrinho e do resumo
│   └── checkout_page.py
├── scripts/
│   ├── gerar_relatorio_pdf.py  # Gera docs/relatorio-de-bugs.pdf a partir do Markdown
│   └── reproduzir_bug_023.py   # Reproduz a condição de corrida do menu (BUG-023) com a CPU mais lenta
├── support/
│   ├── bug_checks.py      # Verificações compartilhadas pelo problem_user e pelo error_user
│   ├── item_checks.py     # assert_item: confere uma linha com a tabela de preços
│   └── state.py           # cart_ids e session_cookie: leem o estado por baixo da tela
├── tests/                 # Os testes, separados por área e por perfil
│   ├── test_login.py
│   ├── test_inventory.py
│   ├── test_product_detail.py
│   ├── test_menu.py
│   ├── test_cart_checkout.py
│   ├── test_console_e_rede.py
│   ├── test_problem_user.py
│   ├── test_error_user.py
│   └── test_visual_user.py
├── BUGS.md                # Resumo dos bugs: ID, severidade, área, teste e issue
├── conftest.py            # Preparação compartilhada (login por usuário, oráculo, erros, relatório)
├── pytest.ini             # Configuração do pytest
├── requirements.txt       # Dependências com versões fixas
├── .gitleaks.toml         # Regras do gitleaks (exceções devem ser específicas e comentadas)
├── .pre-commit-config.yaml # Hook local opcional que bloqueia segredos antes do commit
└── SECURITY.md            # Política de reporte de vulnerabilidades
```

---

## Relatórios e depuração

- **Relatório HTML:** cada execução gera `reports/report.html`, um arquivo único que abre em qualquer navegador. Testes com falha trazem um screenshot da tela no momento do erro.
- **Trace do Playwright:** para cada falha, uma gravação completa (telas, cliques, rede e console) é salva em `test-results/`. Para abrir:

  ```bash
  playwright show-trace test-results/<pasta-do-teste>/trace.zip
  ```

- **Relatório de bugs em PDF:** [`docs/relatorio-de-bugs.pdf`](docs/relatorio-de-bugs.pdf) é gerado a partir do Markdown: começa com uma página de resumo executivo (totais por usuário e severidade, os 3 bugs mais relevantes e links para as issues), seguida do relatório completo com as screenshots das evidências incorporadas e links clicáveis. Depois de editar o relatório, regenere com:

  ```bash
  python scripts/gerar_relatorio_pdf.py
  ```

  O script usa o Chromium do Playwright e o GitHub CLI (`gh`, autenticado) para converter o Markdown, sem dependências extras no `requirements.txt`.

---

## Integração contínua

O workflow [`e2e-tests.yml`](.github/workflows/e2e-tests.yml) prepara o Python 3.13, instala as dependências num `venv`, instala o Chromium, executa os testes em paralelo (`pytest -n auto`) e publica o relatório e os traces como artefato (`relatorio-e2e`), inclusive quando algum teste falha. Na `main`, o job **Publicar relatório no GitHub Pages** coloca o relatório HTML no ar em [https://arckangelo.github.io/saucedemo-playwright-python/](https://arckangelo.github.io/saucedemo-playwright-python/) (só o relatório; os traces ficam no artefato).

O que roda depende do gatilho:

| Gatilho | O que executa | Para quê |
|---|---|---|
| Push fora da `main` | `pytest -n auto -m "not known_bug"`: só os testes que devem passar | Feedback rápido a cada mudança |
| Push na `main` (merge) | Suíte completa e publicação no GitHub Pages | Manter no ar o relatório do que está na `main`, com os bugs conhecidos |
| Pull request | `pytest -n auto`: suíte completa, com os testes de bugs conhecidos | Garantir, antes do merge, que os bugs documentados continuam se comportando como registrado |
| Agendamento diário (09:00 UTC, 06:00 em Brasília) | Suíte completa e publicação no GitHub Pages | Detectar mudanças no site, que é de terceiros: um bug corrigido aparece como XPASS e um comportamento novo aparece como falha |
| Manual (aba **Actions**) | Suíte completa (e publicação, se rodado na `main`) | Rodar sob demanda |

Ao final de cada execução, a página do workflow mostra um **resumo** com a contagem de testes que passaram, de **XFAIL** (bug conhecido que continua reproduzindo) e de **XPASS** (bug conhecido que deixou de reproduzir), além de falhas, erros e pulados. Um XPASS aparece com o teste e o bug: é o sinal para confirmar a correção no site e tirar o `xfail` do teste. O resumo é escrito pelo `conftest.py` (hook `pytest_terminal_summary`) no `$GITHUB_STEP_SUMMARY`; fora do CI, nada é escrito.

Os testes de bugs conhecidos ficam fora do push nas outras branches porque não mudam com o código deste repositório: eles acompanham o site, e isso é papel do PR e da execução diária.

> **Atenção ao agendamento:** o GitHub só agenda workflows a partir da branch padrão (`main`) e, em repositórios públicos como este, **desativa automaticamente os workflows agendados após 60 dias sem atividade** no repositório (sem commits, por exemplo). Para voltar a ter a execução diária, basta reativar o workflow na aba **Actions**.

Antes de qualquer teste, o `conftest.py` confere se o saucedemo.com responde com a página do Swag Labs. Se não responder, a execução é interrompida com a mensagem `SITE INDISPONÍVEL`, em vez de gerar dezenas de falhas que pareceriam bugs.

---

## Segurança do pipeline

Além dos testes, o CI aplica práticas de DevSecOps para proteger o próprio repositório:

| Ferramenta | O que detecta | Quando roda |
|---|---|---|
| [gitleaks](https://github.com/gitleaks/gitleaks) ([`security.yml`](.github/workflows/security.yml)) | Segredos (tokens, chaves, senhas) em **todo o histórico** do git; resultados também na aba *Security* | Push e PR na `main`, semanalmente e no hook local opcional |
| [pip-audit](https://github.com/pypa/pip-audit) ([`security.yml`](.github/workflows/security.yml)) | Dependências (inclusive transitivas) com vulnerabilidade conhecida; falha só em severidade **alta ou crítica** | Push e PR na `main` e semanalmente |
| [Dependabot](.github/dependabot.yml) | Versões desatualizadas ou vulneráveis dos pacotes pip e das GitHub Actions; abre PRs agrupando atualizações menores | Semanalmente |
| [CodeQL](https://codeql.github.com/) ([`codeql.yml`](.github/workflows/codeql.yml)) | Falhas de segurança no Python e nos próprios workflows (ex.: injeção de expressões, permissões excessivas) | Push e PR na `main` e semanalmente |

**Endurecimento dos workflows**

- `permissions: contents: read` no topo de cada workflow; permissões extras só no job que precisa
  (`security-events: write` no CodeQL e no gitleaks; `pages` e `id-token` no deploy do GitHub Pages).
- Todas as actions fixadas pelo **SHA completo do commit**, com a versão em comentário. Uma tag
  pode ser movida para código malicioso; um SHA não. O Dependabot mantém esses SHAs atualizados.
- O gitleaks roda pelo binário oficial com versão e checksum SHA-256 fixos.
- O pip-audit não tem filtro de severidade, então o script [`pip_audit_severidade.py`](.github/scripts/pip_audit_severidade.py)
  consulta cada achado na base pública [OSV](https://osv.dev) e só falha em severidade alta, crítica
  ou desconhecida (na dúvida, falha). As moderadas e baixas aparecem no log como aviso.

**Hook local (opcional)**

Para barrar um segredo antes mesmo do commit:

```bash
pip install pre-commit
pre-commit install            # instala o hook neste clone
pre-commit run --all-files    # (opcional) varre o repositório inteiro uma vez
```

Para reportar uma vulnerabilidade, veja [SECURITY.md](SECURITY.md).

---

## Decisões técnicas

<details>
<summary><b>Clique para ver os detalhes</b></summary>

- **Seletores estáveis:** todos os elementos são localizados pelo atributo `data-test` do site (`get_by_test_id`), que não muda quando o layout ou o texto mudam. Os botões do card usam o prefixo do `data-test` (`add-to-cart-…` vira `remove-…` depois do clique), sem depender do texto exibido. Só duas exceções, justificadas no código: os botões de abrir e fechar o menu são localizados pelo **ID** (`#react-burger-menu-btn`), porque o `data-test="open-menu"` está na imagem do ícone, que fica por baixo do botão e não recebe o clique; e o sinal de que o menu fechado já foi escondido ([BUG-023](docs/relatorio-de-bugs.md#bug-023)) é "o elemento `[hidden]` que contém o link All Items", ancorado num `data-test`, porque o contêiner não tem `data-test` nem ID. Nenhum seletor depende de classe CSS ou de tag.
- **Login reaproveitado:** o login é feito uma única vez por usuário e o cookie de sessão é reutilizado (fixtures `login_as` e `session_as`). Cada teste ainda recebe um navegador limpo, então o carrinho sempre começa vazio e os testes não dependem uns dos outros.
- **Carrinho montado sem passar pela tela:** o SauceDemo não tem API, e o carrinho mora no `localStorage` como lista de ids. A fixture `cart_with(4, 5)` grava essa lista antes de a página carregar, uma única vez por aba (para um item removido não "voltar" no reload), e só aceita ids do catálogo, sem repetição. Só os testes do botão "Add to cart" e a jornada completa clicam na tela; os demais (checkout, Reset App State, `problem_user` e `error_user`) abrem a tela direto pela URL e não falham por causa do botão de adicionar (BUG-010 e BUG-015).
- **`standard_user` como oráculo:** os testes do `visual_user` leem preços, imagens e posições do `standard_user` em outro contexto do navegador, durante o próprio teste, em vez de fixar valores no código. Posições usam tolerância de 5 px e só são medidas depois que as fontes web carregam, o que eliminou um falso positivo de largura de texto.
- **Tabela de preços como fonte de verdade:** `PRODUCT_PRICES` (em `data/constants.py`) guarda id, nome e preço dos 6 produtos, conferidos uma única vez no site. Ordenação, linhas do carrinho e do resumo, subtotal, imposto e total são calculados a partir dela, nunca a partir da própria tela: um preço errado exibido e cobrado de forma coerente passaria despercebido se o teste somasse o que a tela mostra.
- **Dinheiro com `Decimal`:** `float` não representa centavos com exatidão (`0.1 + 0.2 = 0.30000000000000004`). A taxa de 8% foi confirmada no [código-fonte oficial do site](https://github.com/saucelabs/sample-app-web).
- **Bugs conhecidos com `xfail(strict=True)`:** cada bug fica marcado como falha esperada, com o ID do relatório e o número da issue no motivo (`reason="BUG-010 (#11): ..."`). A marcação aceita apenas a exceção específica daquele bug (`raises=...`): se outra coisa quebrar (login, seletor), o teste falha normalmente em vez de se esconder. E se o bug for corrigido, o teste avisa que a marcação pode ser removida. O `conftest.py` aplica o marker `known_bug` a todo xfail com "BUG-", então basta seguir a convenção.
- **Erro JavaScript falha qualquer teste:** a fixture `browser_errors` (autouse) falha o teste no teardown se a página lançar uma exceção não tratada, como o Cypress faz por padrão. Só os testes com o marker `allow_js_errors` toleram exceções, e cada uso cita o bug que as gera (hoje, BUG-015, BUG-016 e BUG-018, todos do `error_user`).
- **Estado conferido por baixo da tela onde a tela não basta:** `cart_ids` lê o carrinho no `localStorage` e `session_cookie` lê o cookie de sessão. São usados onde a tela não prova o efeito: os ids gravados ao adicionar, o carrinho esvaziado depois do pedido e o cookie apagado no logout. Onde a tela já é calculada a partir desse estado (o contador do carrinho), conferir os dois seria redundante.
- **Sem `sleep`:** o Playwright espera automaticamente os elementos ficarem prontos. Para o usuário lento, apenas o tempo limite daquela verificação foi aumentado.
- **Confirmar que algo NÃO aconteceu, sem esperar um tempo fixo:** para provar um bug (o contador não mudou, o pedido não foi concluído), não adianta esperar o efeito, porque ele nunca vem. Em vez de aguardar um tempo fixo, o teste executa a ação, espera o navegador desenhar dois quadros (`wait_for_render`, com `requestAnimationFrame`) e lê o estado sem esperar mais. O navegador só desenha um quadro depois de processar o evento e a atualização de tela que ele dispara, então esse é o sinal concreto de que a ação já teve efeito, se fosse ter. A técnica foi validada no `standard_user`: em 175 repetições de 7 ações diferentes, o efeito sempre já estava na tela depois dos dois quadros. Onde há um sinal ainda mais direto (a página de pedido concluído apareceu, o contador sumiu), ele é usado.
- **Exceções documentadas (esperas por sinal, não por tempo):**
  - **Menu lateral ([BUG-023](docs/relatorio-de-bugs.md#bug-023)):** o componente do menu (`react-burger-menu`) agenda um timer de 500 ms, ao carregar a página e ao fechar o menu, que esconde o menu fechado. Um clique antes desse timer, em máquina lenta, deixa o menu "aberto" mas invisível. A condição de corrida apareceu nas execuções em paralelo e foi reproduzida com a CPU 30x mais lenta. Antes de abrir o menu, o `Header` espera o atributo `hidden` aparecer no menu fechado, o sinal de que o timer já rodou (no máximo 500 ms depois da carga).
  - **Telemetria (BUG-006):** o teste espera até 10 s pela requisição ao Backtrace. A espera termina assim que ela sai; só chega ao limite se a telemetria tiver sido removida, e nesse caso o teste passa e o xfail avisa. Se a requisição sai mas não recebe resposta (desde 27/10/2026 o Backtrace demora mais que os 15 s em que o próprio site aborta a chamada), o resultado é inconclusivo e o teste é pulado (skip), em vez de um falso "corrigido".
- **Site indisponível não vira falha de teste:** uma checagem única no início da sessão (`pytest_sessionstart`) interrompe a execução se o site não responder. Não há retry: re-executar testes que falharam esconde instabilidade em vez de mostrá-la.

</details>

### Próximos passos

Os próximos passos, detalhados nas [sugestões de melhoria](docs/sugestoes-de-melhoria.md#parte-b-melhorias-para-este-projeto):

- rodar a suíte em Chromium, Firefox e WebKit no CI (matriz de navegadores);
- levar a checagem de acessibilidade com axe-core para o CI, falhando só em violações sérias e críticas;
- adicionar ruff ao CI e ao `pre-commit`;
- avaliar as 4 [suspeitas](docs/relatorio-de-bugs.md#suspeitas) do relatório, como o pedido que pode ser finalizado de novo pelo botão Voltar.
- testar o recibo em PDF do botão **Generate PDF order** (itens, total e dados de entrega), funcionalidade nova do site que ainda não tem teste;
- fechar as lacunas de cobertura das [regras de negócio](docs/requisitos-inferidos.md#regras-de-negócio): a ordem de validação do login e do checkout (RN-02 e RN-15), a validade de 10 minutos da sessão (RN-05), o inventário abrir em A–Z (RN-07), o clique na imagem do produto (RN-09) e o comportamento do resumo ao recarregar e ao voltar ao passo 1 (RN-20).

---

## Autor

**Angelo Roque**, QA com foco em automação de testes.

[LinkedIn](https://www.linkedin.com/in/angelo-roque-223b6b259/) · [GitHub](https://github.com/Arckangelo)