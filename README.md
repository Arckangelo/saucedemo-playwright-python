# SauceDemo E2E — Python + Playwright

[![E2E Tests](https://github.com/Arckangelo/saucedemo-playwright-python/actions/workflows/e2e-tests.yml/badge.svg)](https://github.com/Arckangelo/saucedemo-playwright-python/actions/workflows/e2e-tests.yml)
[![Security](https://github.com/Arckangelo/saucedemo-playwright-python/actions/workflows/security.yml/badge.svg)](https://github.com/Arckangelo/saucedemo-playwright-python/actions/workflows/security.yml)
[![CodeQL](https://github.com/Arckangelo/saucedemo-playwright-python/actions/workflows/codeql.yml/badge.svg)](https://github.com/Arckangelo/saucedemo-playwright-python/actions/workflows/codeql.yml)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-1.63-2EAD33?logo=playwright&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-9.1-0A9EDC?logo=pytest&logoColor=white)

Suíte de testes automatizados **end-to-end** para o [SauceDemo (Swag Labs)](https://www.saucedemo.com), loja virtual de demonstração da Sauce Labs feita para praticar automação.

Os testes simulam um usuário real no navegador: fazem login, navegam pelo catálogo, montam o carrinho e finalizam a compra, conferindo se cada etapa se comporta como esperado.

> Este projeto complementa meu [projeto em Cypress/JavaScript](https://github.com/Arckangelo/automationexercise-cypress-tests).

---

## Sumário

- [Destaques](#destaques)
- [Tecnologias](#tecnologias)
- [Como executar](#como-executar)
- [O que é testado](#o-que-é-testado)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Relatórios e depuração](#relatórios-e-depuração)
- [Integração contínua](#integração-contínua)
- [Segurança do pipeline](#segurança-do-pipeline)
- [Decisões técnicas](#decisões-técnicas)
- [Autor](#autor)

---

## Destaques

- **24 execuções de teste** a partir de 10 cenários, usando parametrização.
- **Page Object Model**: cada tela do site é uma classe, então os testes ficam curtos e legíveis.
- **Login feito uma única vez** por execução e reaproveitado, o que deixa a suíte rápida (menos de 1 minuto).
- **Bugs conhecidos documentados como testes**, em vez de ignorados.
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
| `pytest` | Roda todos os testes, sem abrir o navegador |
| `pytest --headed --slowmo 500` | Mostra o navegador e desacelera cada ação, útil para acompanhar |
| `pytest -m smoke` | Roda só os fluxos críticos |
| `pytest tests/test_login.py` | Roda um único arquivo |
| `pytest -k ordenacao` | Roda os testes cujo nome contém o termo |
| `pytest --browser firefox` | Roda no Firefox (requer `playwright install firefox`) |

---

## O que é testado

| Área | Cenário | Execuções |
|---|---|:---:|
| **Login** | Usuários válidos acessam a loja (`standard`, `problem`, `performance_glitch`) | 3 |
| | Login inválido mostra a mensagem certa (bloqueado, senha errada, usuário inexistente, campos vazios) | 5 |
| | Páginas internas exigem login (`/inventory`, `/cart`, `/checkout`) | 3 |
| | Logout encerra a sessão de verdade | 1 |
| **Catálogo** | Ordenação por nome (A–Z, Z–A) e por preço (menor e maior) | 4 |
| | Cada produto exibe a própria imagem | 2 |
| | Adicionar e remover produtos atualiza o contador do carrinho | 1 |
| **Carrinho e checkout** | Compra completa, conferindo subtotal, imposto de 8% e total | 1 |
| | Formulário exige nome, sobrenome e CEP | 3 |
| | Carrinho continua salvo após recarregar a página | 1 |
| | **Total** | **24** |

### Perfis de usuário

O SauceDemo oferece usuários com comportamentos diferentes, e a suíte explora cada um:

| Usuário | Comportamento | Como é testado |
|---|---|---|
| `standard_user` | Funciona normalmente | Base de todos os fluxos de compra |
| `locked_out_user` | Bloqueado no login | Verifica a mensagem de bloqueio |
| `problem_user` | Tem defeitos de interface | Consegue logar, e o bug das imagens fica registrado como falha conhecida |
| `performance_glitch_user` | Carrega devagar (~5 s) | Usa um tempo de espera maior, sem pausas fixas |

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
│   └── constants.py       # Usuários, produtos e mensagens esperadas
├── pages/                 # Page Objects (uma classe por tela)
│   ├── base_page.py
│   ├── header.py          # Cabeçalho comum (carrinho e menu)
│   ├── login_page.py
│   ├── inventory_page.py
│   ├── cart_page.py
│   └── checkout_page.py
├── tests/                 # Os testes, separados por área
│   ├── test_login.py
│   ├── test_inventory.py
│   └── test_cart_checkout.py
├── conftest.py            # Preparação compartilhada (login, relatório)
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

---

## Integração contínua

O workflow [`e2e-tests.yml`](.github/workflows/e2e-tests.yml) roda a cada push, pull request ou manualmente pela aba **Actions**. Ele:

1. Prepara o Python 3.13;
2. Cria um ambiente virtual (`venv`) e instala as dependências com `pip`;
3. Instala o Chromium;
4. Executa a suíte;
5. Publica o relatório e os traces como artefato (`relatorio-e2e`), inclusive quando algum teste falha.

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

- **Seletores estáveis:** os elementos são localizados principalmente pelo atributo `data-test` do site, que não muda quando o layout muda. As exceções são o botão do menu, encontrado pelo papel acessível (como um leitor de tela o enxerga), e as imagens dos produtos, encontradas pela classe CSS.
- **Login reaproveitado:** o login é feito uma única vez e o cookie de sessão é reutilizado. Cada teste ainda recebe um navegador limpo, então o carrinho sempre começa vazio e os testes não dependem uns dos outros.
- **Resultados calculados, não decorados:** a ordenação é comparada com a lista ordenada a partir da própria tela, e no checkout subtotal, imposto e total são recalculados a partir dos preços exibidos.
- **Dinheiro com `Decimal`:** `float` não representa centavos com exatidão (`0.1 + 0.2 = 0.30000000000000004`). A taxa de 8% foi confirmada no [código-fonte oficial do site](https://github.com/saucelabs/sample-app-web).
- **Bugs conhecidos com `xfail(strict=True)`:** o bug de imagens do `problem_user` fica marcado como falha esperada. A marcação aceita apenas a falha específica desse bug: se outra coisa quebrar (login, seletor), o teste falha normalmente em vez de se esconder. E se o bug for corrigido, o teste avisa que a marcação pode ser removida.
- **Sem `sleep`:** o Playwright espera automaticamente os elementos ficarem prontos. Para o usuário lento, apenas o tempo limite daquela verificação foi aumentado.

</details>

### Próximos passos

Bugs já observados no `problem_user` que podem virar novos testes:

- a ordenação de produtos não funciona;
- no checkout, o texto digitado no campo de sobrenome vai para o campo de nome, e o sobrenome fica vazio, o que impede a compra.

---

## Autor

**Angelo Roque**, QA com foco em automação de testes.

[LinkedIn](https://www.linkedin.com/in/angelo-roque-223b6b259/) · [GitHub](https://github.com/Arckangelo)