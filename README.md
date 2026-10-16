# SauceDemo E2E — Python + Playwright

[![E2E Tests](https://github.com/Arckangelo/saucedemo-playwright-python/actions/workflows/e2e-tests.yml/badge.svg)](https://github.com/Arckangelo/saucedemo-playwright-python/actions/workflows/e2e-tests.yml)
[![Security](https://github.com/Arckangelo/saucedemo-playwright-python/actions/workflows/security.yml/badge.svg)](https://github.com/Arckangelo/saucedemo-playwright-python/actions/workflows/security.yml)
[![CodeQL](https://github.com/Arckangelo/saucedemo-playwright-python/actions/workflows/codeql.yml/badge.svg)](https://github.com/Arckangelo/saucedemo-playwright-python/actions/workflows/codeql.yml)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-1.63-2EAD33?logo=playwright&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-9.1-0A9EDC?logo=pytest&logoColor=white)

Suíte de testes automatizados **end-to-end** para o [SauceDemo (Swag Labs)](https://www.saucedemo.com), loja virtual de demonstração da Sauce Labs feita para praticar automação.

Além de cobrir login, catálogo, carrinho e checkout, o projeto fez engenharia reversa do site e documentou **23 defeitos**: **7 afetam todos os usuários**, inclusive o padrão (como um pedido de $0.00 concluído com o carrinho vazio), e **16 são os defeitos de treino** que o SauceDemo injeta de propósito nos perfis especiais. Cada um tem issue e evidências e, em 22 casos, um teste automatizado que avisa quando o bug for corrigido.

<p align="center"><img src="docs/img/resumo-projeto.png" width="420" alt="Resumo do projeto: 7 defeitos que afetam todos os usuários do SauceDemo, inclusive o padrão, mais 16 defeitos de treino que o site injeta de propósito nos perfis especiais (7 no problem_user, 5 no error_user e 4 no visual_user), também mapeados e testados; execuções de teste passaram de 24 para 78, cobrindo os 6 perfis de usuário; 23 issues no GitHub, cada uma com evidência; CI 6 vezes mais rápido a cada push, de 101 s para 17 s. Destaque do BUG-001: até o usuário padrão conclui um pedido com o carrinho vazio, com total de $0.00."></p>

> Este projeto complementa meu [projeto em Cypress/JavaScript](https://github.com/Arckangelo/automationexercise-cypress-tests).

---

## Sumário

- [Destaques](#destaques)
- [Tecnologias](#tecnologias)
- [Como executar](#como-executar)
- [O que é testado](#o-que-é-testado)
- [Engenharia reversa e bugs encontrados](#engenharia-reversa-e-bugs-encontrados)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Relatórios e depuração](#relatórios-e-depuração)
- [Integração contínua](#integração-contínua)
- [Segurança do pipeline](#segurança-do-pipeline)
- [Decisões técnicas](#decisões-técnicas)
- [Autor](#autor)

---

## Destaques

- **78 execuções de teste** a partir de 36 cenários, usando parametrização, cobrindo os **6 perfis de usuário** do site.
- **Engenharia reversa documentada**: [requisitos inferidos](docs/requisitos-inferidos.md) do comportamento observado, com mapa de fluxos e matriz usuário × funcionalidade.
- **23 defeitos documentados** (7 que afetam todos os usuários e 16 de treino dos perfis especiais), 22 deles cobertos por testes em vez de ignorados, com [relatório completo e evidências](docs/relatorio-de-bugs.md) e [uma issue por bug](https://github.com/Arckangelo/saucedemo-playwright-python/issues?q=label%3Abug). O 23º, um bug de tempo, tem um script de reprodução controlada.
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
| `pytest tests/test_login.py` | Roda um único arquivo |
| `pytest -k ordenacao` | Roda os testes cujo nome contém o termo |
| `pytest --browser firefox` | Roda no Firefox (requer `playwright install firefox`) |

---

## O que é testado

| Área | Cenário | Execuções |
|---|---|:---:|
| **Login** | Usuários válidos acessam a loja (`standard`, `problem`, `performance_glitch`, `error`, `visual`) | 5 |
| | Login inválido mostra a mensagem certa (bloqueado, senha errada, usuário inexistente, campos vazios) | 5 |
| | Páginas internas exigem login (`/inventory`, `/cart`, `/checkout`) | 3 |
| | Cookie de sessão adulterado não dá acesso (usuário inexistente, bloqueado, maiúsculas) | 3 |
| | Logout encerra a sessão de verdade | 1 |
| **Catálogo** | Ordenação por nome (A–Z, Z–A) e por preço (menor e maior) | 4 |
| | Cada produto exibe a própria imagem | 2 |
| | Adicionar e remover produtos atualiza o contador do carrinho | 1 |
| | Reset App State volta os botões para "Add to cart" | 1 |
| **Detalhe do produto** | Clicar no produto abre o detalhe dele | 1 |
| | A URL `?id=N` abre o produto certo | 6 |
| | Produto inexistente não entra no carrinho (pela URL e pelo `localStorage`) | 3 |
| **Menu** | All Items volta ao inventário; About aponta para a Sauce Labs | 3 |
| **Carrinho e checkout** | Compra completa, conferindo subtotal, imposto de 8% e total | 1 |
| | Formulário exige nome, sobrenome e CEP | 3 |
| | Formulário rejeita campos só com espaços | 3 |
| | Não conclui pedido com o carrinho vazio | 1 |
| | Carrinho continua salvo após recarregar a página | 1 |
| **Saúde técnica** | Compra sem erros JavaScript; rotas respondem HTTP 200; telemetria sem erros | 3 |
| **problem_user** | Ordenação, adicionar e remover cada produto, detalhe, sobrenome e carrinho após o pedido | 10 |
| **error_user** | Ordenação, adicionar e remover cada produto, sobrenome e botão Finish | 10 |
| **visual_user** | Preços, imagens e layout comparados com o `standard_user` | 8 |
| | **Total** | **78** |

Das 78 execuções, 42 passam e 36 documentam bugs conhecidos como falha esperada (`xfail`).

### Perfis de usuário

O SauceDemo oferece usuários com comportamentos diferentes. Os defeitos do `problem_user`, do `error_user` e do `visual_user` são injetados de propósito pelo site, para treino; a suíte mapeia e automatiza cada um:

| Usuário | Comportamento | Como é testado |
|---|---|---|
| `standard_user` | Funciona normalmente, mas compartilha os 7 bugs que afetam todos os usuários (ex.: pedido concluído com o carrinho vazio) | Base de todos os fluxos e **oráculo** dos outros perfis; 7 bugs registrados (6 como falhas conhecidas e 1 com script de reprodução) |
| `locked_out_user` | Bloqueado no login | Verifica a mensagem de bloqueio, inclusive com cookie forjado |
| `problem_user` | Defeitos de interface: imagens, ordenação, botões, detalhe errado e formulário | 7 bugs registrados como falhas conhecidas |
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
| [Relatório de bugs](docs/relatorio-de-bugs.md) ([PDF](docs/relatorio-de-bugs.pdf)) | 23 bugs confirmados (7 que afetam todos os usuários e 16 de treino dos perfis especiais; 2 críticos, 3 altos, 11 médios, 7 baixos), 4 suspeitas e comportamentos intencionais, com passos, evidências e o teste (ou o script de reprodução) de cada um |
| [Issues dos bugs](https://github.com/Arckangelo/saucedemo-playwright-python/issues?q=label%3Abug) | Uma issue por bug confirmado, com severidade, passos para reproduzir, evidências e o teste que a cobre |
| [Sugestões de melhoria](docs/sugestoes-de-melhoria.md) | Melhorias para a aplicação e para este projeto, com esforço e impacto |

Destaques entre os defeitos que afetam todos os usuários: o `standard_user` consegue concluir um
pedido de $0.00 com o carrinho vazio, e o paralelismo da própria suíte revelou uma condição de
corrida no menu do site ([BUG-023](docs/relatorio-de-bugs.md#bug-023)): investigada a partir do
trace do Playwright e reproduzida com a CPU 30x mais lenta, ela deixa o menu aberto porém
invisível. Entre os defeitos de treino, o `visual_user` vê um preço no catálogo e paga outro, e o
`error_user` não consegue finalizar a compra.

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
│   ├── requisitos-inferidos.md   # Engenharia reversa: fluxos, regras e matriz de usuários
│   ├── relatorio-de-bugs.md      # Bugs confirmados, suspeitas e evidências
│   ├── relatorio-de-bugs.pdf     # O mesmo relatório em PDF (A4), gerado pelo script abaixo
│   ├── sugestoes-de-melhoria.md  # Melhorias para a aplicação e para o projeto
│   ├── evidencias/               # Screenshots e logs citados no relatório
│   └── img/                      # Imagem-resumo exibida no topo deste README
├── pages/                 # Page Objects (uma classe por tela)
│   ├── base_page.py
│   ├── header.py          # Cabeçalho comum (carrinho e menu lateral)
│   ├── login_page.py
│   ├── inventory_page.py
│   ├── product_detail_page.py
│   ├── cart_page.py
│   └── checkout_page.py
├── scripts/
│   ├── gerar_relatorio_pdf.py  # Gera docs/relatorio-de-bugs.pdf a partir do Markdown
│   └── reproduzir_bug_023.py   # Reproduz a condição de corrida do menu (BUG-023) com a CPU mais lenta
├── support/
│   └── bug_checks.py      # Verificações compartilhadas pelo problem_user e pelo error_user
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

O workflow [`e2e-tests.yml`](.github/workflows/e2e-tests.yml) prepara o Python 3.13, instala as dependências num `venv`, instala o Chromium, executa os testes em paralelo (`pytest -n auto`) e publica o relatório e os traces como artefato (`relatorio-e2e`), inclusive quando algum teste falha.

O que roda depende do gatilho:

| Gatilho | O que executa | Para quê |
|---|---|---|
| Push em qualquer branch | `pytest -n auto -m "not known_bug"`: só os testes que devem passar | Feedback rápido a cada mudança |
| Pull request | `pytest -n auto`: suíte completa, com os testes de bugs conhecidos | Garantir, antes do merge, que os bugs documentados continuam se comportando como registrado |
| Agendamento diário (09:00 UTC, 06:00 em Brasília) | Suíte completa | Detectar mudanças no site, que é de terceiros: um bug corrigido aparece como XPASS e um comportamento novo aparece como falha |
| Manual (aba **Actions**) | Suíte completa | Rodar sob demanda |

Os testes de bugs conhecidos ficam fora do push porque não mudam com o código deste repositório: eles acompanham o site, e isso é papel do PR e da execução diária.

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
  (`security-events: write` no CodeQL e no gitleaks).
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

- **Seletores estáveis:** os elementos são localizados principalmente pelo atributo `data-test` do site, que não muda quando o layout muda. Os botões Open Menu, Close Menu, Add to cart e Remove são encontrados pelo papel acessível e pelo nome (como um leitor de tela os enxerga). Seletores CSS ficam restritos às imagens dos produtos, à tag `<button>` dentro do card do produto (usada para ler o botão sem saber se ele diz Add to cart ou Remove; os links do card também têm papel de botão, o que tornaria a busca por papel ambígua) e ao sinal de que o menu fechado já foi escondido (`.bm-menu-wrap[hidden]`, ver [BUG-023](docs/relatorio-de-bugs.md#bug-023)).
- **Login reaproveitado:** o login é feito uma única vez por usuário e o cookie de sessão é reutilizado (fixture `login_as`). Cada teste ainda recebe um navegador limpo, então o carrinho sempre começa vazio e os testes não dependem uns dos outros.
- **`standard_user` como oráculo:** os testes do `visual_user` leem preços, imagens e posições do `standard_user` em outro contexto do navegador, durante o próprio teste, em vez de fixar valores no código. Posições usam tolerância de 5 px e só são medidas depois que as fontes web carregam, o que eliminou um falso positivo de largura de texto.
- **Resultados calculados, não decorados:** a ordenação é comparada com a lista ordenada a partir da própria tela, e no checkout subtotal, imposto e total são recalculados a partir dos preços exibidos.
- **Dinheiro com `Decimal`:** `float` não representa centavos com exatidão (`0.1 + 0.2 = 0.30000000000000004`). A taxa de 8% foi confirmada no [código-fonte oficial do site](https://github.com/saucelabs/sample-app-web).
- **Bugs conhecidos com `xfail(strict=True)`:** cada bug fica marcado como falha esperada, com o ID do relatório e o número da issue no motivo (`reason="BUG-010 (#11): ..."`). A marcação aceita apenas a exceção específica daquele bug (`raises=...`): se outra coisa quebrar (login, seletor), o teste falha normalmente em vez de se esconder. E se o bug for corrigido, o teste avisa que a marcação pode ser removida. O `conftest.py` aplica o marker `known_bug` a todo xfail com "BUG-", então basta seguir a convenção.
- **Sem `sleep`:** o Playwright espera automaticamente os elementos ficarem prontos. Para o usuário lento, apenas o tempo limite daquela verificação foi aumentado.
- **Confirmar que algo NÃO aconteceu, sem esperar um tempo fixo:** para provar um bug (o contador não mudou, o pedido não foi concluído), não adianta esperar o efeito, porque ele nunca vem. Em vez de aguardar um tempo fixo, o teste executa a ação, espera o navegador desenhar dois quadros (`wait_for_render`, com `requestAnimationFrame`) e lê o estado sem esperar mais. O navegador só desenha um quadro depois de processar o evento e a atualização de tela que ele dispara, então esse é o sinal concreto de que a ação já teve efeito, se fosse ter. A técnica foi validada no `standard_user`: em 175 repetições de 7 ações diferentes, o efeito sempre já estava na tela depois dos dois quadros. Onde há um sinal ainda mais direto (a página de pedido concluído apareceu, o contador sumiu), ele é usado.
- **Exceções documentadas (esperas por sinal, não por tempo):**
  - **Menu lateral ([BUG-023](docs/relatorio-de-bugs.md#bug-023)):** o componente do menu (`react-burger-menu`) agenda um timer de 500 ms, ao carregar a página e ao fechar o menu, que esconde o menu fechado. Um clique antes desse timer, em máquina lenta, deixa o menu "aberto" mas invisível. A condição de corrida apareceu nas execuções em paralelo e foi reproduzida com a CPU 30x mais lenta. Antes de abrir o menu, o `Header` espera o atributo `hidden` aparecer no menu fechado, o sinal de que o timer já rodou (no máximo 500 ms depois da carga).
  - **Telemetria (BUG-006):** o teste espera até 10 s pela requisição ao Backtrace. A espera termina assim que ela sai; só chega ao limite se a telemetria tiver sido removida, e nesse caso o teste passa e o xfail avisa.
- **Site indisponível não vira falha de teste:** uma checagem única no início da sessão (`pytest_sessionstart`) interrompe a execução se o site não responder. Não há retry: re-executar testes que falharam esconde instabilidade em vez de mostrá-la.

</details>

### Próximos passos

Os próximos passos, detalhados nas [sugestões de melhoria](docs/sugestoes-de-melhoria.md#parte-b-melhorias-para-este-projeto):

- rodar a suíte em Chromium, Firefox e WebKit no CI (matriz de navegadores);
- levar a checagem de acessibilidade com axe-core para o CI, falhando só em violações sérias e críticas;
- adicionar ruff ao CI e ao `pre-commit`;
- avaliar as 4 [suspeitas](docs/relatorio-de-bugs.md#suspeitas) do relatório, como o pedido que pode ser finalizado de novo pelo botão Voltar.

---

## Autor

**Angelo Roque**, QA com foco em automação de testes.

[LinkedIn](https://www.linkedin.com/in/angelo-roque-223b6b259/) · [GitHub](https://github.com/Arckangelo)