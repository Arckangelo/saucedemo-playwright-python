# Plano de testes — saucedemo-playwright-python

| | |
|---|---|
| **Versão** | 1.0 · 17/11/2026 |
| **Responsável** | Angelo Roque |
| **Sistema sob teste** | [SauceDemo (Swag Labs)](https://www.saucedemo.com), em produção |
| **Documentos relacionados** | [Casos de teste](casos-de-teste.md) · [Requisitos inferidos](requisitos-inferidos.md) · [Insumos do ambiente](insumos-do-ambiente.md) · [Relatório de bugs](relatorio-de-bugs.md) · [BUGS.md](../BUGS.md) · [Análise de mutação](analise-de-mutacao.md) · [README](../README.md) |

O plano descreve o que a suíte testa, como, onde, quando e com que critério uma execução é aceita. O
detalhe de cada teste (passos, dados e resultado esperado) fica nos [casos de teste](casos-de-teste.md),
com o mesmo ID `CT-…` do comentário no código.

## 1. Objetivo

- Verificar os fluxos de uma loja virtual (login, catálogo, detalhe do produto, carrinho, checkout e
  menu) com os 6 perfis de usuário do site.
- Manter cada bug encontrado como um teste que descreve o comportamento correto e aparece como falha
  esperada (`xfail(strict=True)`), avisando quando o bug for corrigido.
- Medir se os testes pegam defeitos de verdade, usando os perfis defeituosos do próprio site como
  mutantes (análise de mutação).

## 2. Sistema sob teste

- **Site:** loja de demonstração da Sauce Labs, feita para praticar automação. É de terceiros e só tem
  front-end ([código-fonte oficial](https://github.com/saucelabs/sample-app-web)): login, carrinho e
  pedido acontecem no navegador.
- **Sem API nem banco:** o valor esperado vem do catálogo lido do JavaScript do site na hora, do
  código-fonte oficial e do `standard_user` como oráculo; o efeito das ações é conferido no
  `localStorage` e no cookie (seção 4.2).
- **Sem especificação:** os critérios de aceite são as regras RN-01 a RN-20, inferidas por engenharia
  reversa em [requisitos-inferidos.md](requisitos-inferidos.md).
- **Perfis de usuário:** `standard_user` (base e oráculo), `locked_out_user` (bloqueado),
  `problem_user`, `error_user` e `visual_user` (defeitos injetados de propósito pelo site) e
  `performance_glitch_user` (atraso de ~5 s no inventário).
- **Ambiente:** produção pública e compartilhada. Nada é gravado no servidor (seção 9).

## 3. Escopo

### 3.1 Dentro do escopo

| Área | Funcionalidades | Arquivo | Casos | Execuções | Bugs conhecidos |
|---|---|---|:-:|:-:|:-:|
| Autenticação | Login dos perfis válidos, mensagens de erro, páginas que exigem login, cookie adulterado, logout | `test_login.py` | 5 | 20 | 0 |
| Catálogo | Ordenação, imagens, adicionar e remover, Reset App State | `test_inventory.py` | 5 | 9 | 2 |
| Detalhe do produto | Clique abre o produto certo, URL `?id=N`, produto inexistente | `test_product_detail.py` | 4 | 10 | 3 |
| Menu | All Items e About | `test_menu.py` | 2 | 3 | 1 |
| Carrinho e checkout | Compra completa, subtotal, imposto e total, campos obrigatórios, carrinho persistido | `test_cart_checkout.py` | 10 | 14 | 5 |
| Saúde técnica | Status HTTP das rotas e telemetria | `test_console_e_rede.py` | 2 | 2 | 2 |
| Guarda de preços | Catálogo do site igual à tabela conferida | `test_catalogo.py` | 1 | 1 | 0 |
| `problem_user` | Ordenação, botões, detalhe, sobrenome, subtotal, carrinho após o pedido | `test_problem_user.py` | 6 | 11 | 11 |
| `error_user` | Ordenação, botões, sobrenome, Finish | `test_error_user.py` | 5 | 10 | 10 |
| `visual_user` | Preços, imagens e layout | `test_visual_user.py` | 3 | 8 | 4 |
| **Testes do site** | | **10 arquivos** | **43** | **88** | **38** |

Das 88 execuções, 50 devem passar e 38 documentam bugs conhecidos como falha esperada.

Além delas, **96 testes conferem a própria suíte**, sem acessar o site:

| Arquivo | Testes | O que prova |
|---|:-:|---|
| `test_protecao_site.py` | 19 | A proteção contra queda do site funciona (queda simulada) |
| `test_regra_dos_bugs.py` | 16 | Um xfail fora da regra dos bugs conhecidos vira erro |
| `test_resumo_dos_bugs.py` | 4 | O resumo dos bugs no CI mostra cada resultado possível |
| `test_leitura_do_catalogo.py` | 28 | A leitura do catálogo de preços e a marca SUSPEITO do teste de guarda |
| `test_convencoes.py` | 29 | As convenções do código (assert sem mensagem, espera fixa, `page.goto` direto, teste pulado, depurador, senha e tabela de preços fora do lugar) |

### 3.2 Fora do escopo

| Item | Motivo |
|---|---|
| Desempenho e carga | Site público de terceiros: carga seria abuso do serviço |
| Firefox e WebKit no CI | Hoje só Chromium; a matriz de navegadores está nos próximos passos do README |
| Acessibilidade | Próximo passo: axe-core no CI, falhando só em violações sérias e críticas |
| Recibo em PDF (**Generate PDF order**) | Funcionalidade nova do site, ainda sem teste |
| BUG-023 (menu que abre invisível) | Condição de corrida dependente de tempo: reproduzida em `scripts/reproduzir_bug_023.py`, sem teste de propósito |
| Lacunas de regras de negócio | Ordem de validação do login e do checkout (RN-02, RN-15), validade de 10 minutos da sessão (RN-05), inventário abrindo em A–Z (RN-07), clique na imagem (RN-09), resumo ao recarregar e ao voltar (RN-20) |
| 4 suspeitas do relatório de bugs | Ainda em avaliação (ex.: pedido finalizado de novo pelo botão Voltar) |

## 4. Estratégia

### 4.1 Níveis e tipos de teste

| Tipo | O que cobre | Onde |
|---|---|---|
| Funcional E2E | Fluxos completos na tela, com o efeito conferido no estado do navegador | `tests/test_*.py` do site |
| Regressão por perfil | Cada defeito dos perfis de treino mapeado e testado contra o `standard_user` | `test_problem_user.py`, `test_error_user.py`, `test_visual_user.py` |
| Bugs conhecidos | Comportamento correto esperado; XFAIL enquanto o bug existir, XPASS reprova e avisa | Marker `known_bug`, aplicado sozinho |
| Fumaça (`smoke`) | 6 execuções dos fluxos críticos: login dos perfis válidos e compra completa | `pytest -m smoke` |
| Regressão (`regression`) | 43 execuções por perfil e de bordas | `pytest -m regression` |
| Segurança de sessão | Páginas internas sem login e cookie forjado | `test_login.py` |
| Saúde técnica | Status HTTP e telemetria; erro JavaScript reprova qualquer teste | `test_console_e_rede.py` e fixture `browser_errors` |
| Teste de guarda | Catálogo do site comparado com `PRODUCT_PRICES` (conferida em 27/10/2026) | `test_catalogo.py` |
| Análise de mutação | Testes do `standard_user` rodados com `problem_user`, `error_user` e `visual_user` | `--base-user`, ver [análise de mutação](analise-de-mutacao.md) |
| Testes da suíte | Proteções, regras e convenções da própria suíte | Os 5 arquivos da seção 3.1 |
| Segurança do pipeline | Segredos (gitleaks), dependências vulneráveis (pip-audit), análise estática (CodeQL) | Workflows de segurança |

### 4.2 Técnicas de projeto

- **Oráculo independente:**
  - nome e preço esperados vêm do catálogo lido do JavaScript do site na hora (`catalog_prices`),
    nunca da tela testada;
  - a regra do imposto de 8% (RN-17) fica no teste (`TAX_RATE`);
  - dinheiro sempre em `Decimal`.
- **`standard_user` como oráculo:** imagens e posições do `visual_user` são comparadas com as do
  `standard_user`, lidas em outro contexto durante o teste.
- **Efeito no estado:** onde a tela não prova o efeito, o teste lê o `localStorage` (`cart_ids`) e o
  cookie (`session_cookie`): ids gravados ao adicionar, carrinho vazio depois do pedido, cookie apagado
  no logout.
- **Partição e valor-limite:** ids de produto válidos e inexistentes (`6`, `-1`, `999`), campos vazios e
  só com espaços, cookie com usuário inexistente, bloqueado ou em maiúsculas.
- **Parametrização:** 43 cenários viram 88 execuções (cada perfil, produto, ordenação ou campo).

### 4.3 Princípios de escrita

- Nunca `sleep` nem `wait_for_timeout`. Para provar que algo não aconteceu, `wait_for_render` (dois
  quadros); depois de troca de tela, `on_page` e `reached`.
- Toda asserção negativa vem depois de um controle positivo de que a página certa já foi desenhada.
- Seletores por `data-test`; as duas exceções têm comentário no código.
- Toda `assert` tem mensagem; nenhum dado solto no teste (tudo em `data/constants.py`).
- Login feito uma vez por usuário e reaproveitado; carrinho montado com `cart_with(...)`; a tela só para
  o que está sendo testado.
- Testes independentes, num contexto novo do navegador, prontos para rodar em paralelo.
- Nenhum teste é repetido quando falha: repetir esconde instabilidade.

## 5. Priorização

A prioridade de cada caso segue o risco: dinheiro (checkout e preços) e acesso primeiro.

| Área | Alta | Média | Baixa | Total |
|---|:-:|:-:|:-:|:-:|
| Autenticação | 4 | 1 | 0 | 5 |
| Catálogo | 1 | 3 | 1 | 5 |
| Detalhe do produto | 0 | 4 | 0 | 4 |
| Menu | 0 | 0 | 2 | 2 |
| Carrinho e checkout | 6 | 4 | 0 | 10 |
| Saúde técnica | 0 | 0 | 2 | 2 |
| Guarda de preços | 0 | 1 | 0 | 1 |
| `problem_user` | 3 | 3 | 0 | 6 |
| `error_user` | 2 | 3 | 0 | 5 |
| `visual_user` | 1 | 1 | 1 | 3 |
| **Total** | **17** | **20** | **6** | **43** |

Os 25 bugs se dividem em 2 críticos, 4 altos, 12 médios e 7 baixos. 8 afetam todos os usuários e 17
são de treino (8 no `problem_user`, 5 no `error_user` e 4 no `visual_user`). Detalhes em
[BUGS.md](../BUGS.md).

## 6. Critérios

### 6.1 Entrada

- Python 3.13 no CI (3.10 ou superior localmente), dependências do `requirements.txt` com versões
  exatas e o Chromium do Playwright instalados.
- Site respondendo: a checagem do início da sessão confere se o saucedemo.com mostra a página do Swag
  Labs. Se não mostrar, nenhum teste roda (6.3).

### 6.2 Saída (execução aceita)

| Execução | Critério |
|---|---|
| Testes do site | As 50 execuções que devem passar passam |
| Bugs conhecidos | As 38 dão XFAIL com a exceção própria do bug ("reproduz"). Um XPASS reprova a execução e indica um bug possivelmente corrigido: confirmar no site e tirar o `xfail` |
| Regra dos bugs | Nenhum xfail fora da regra (sem `strict=True`, sem `raises=` específico, ou com ID e issue que não batem com o BUGS.md): violação termina como ERRO |
| Testes da suíte | Os 96 passam, inclusive as convenções do código |
| Site | Nenhum resultado "SITE INDISPONÍVEL"; se houver, a execução termina com código 2 e não é aceita |
| Mutação | Nenhum teste do `standard_user` sobrevive numa funcionalidade que o perfil quebra (hoje: 0) |
| Segurança | gitleaks sem segredo, pip-audit sem severidade alta ou crítica e CodeQL sem alerta |

### 6.3 Suspensão e retomada

- **Suspensão:** o site não responde, responde 429, 502–504 ou 520–524, ou mostra uma página sem o
  título "Swag Labs". O carregamento é tentado até 3 vezes (`safe_goto`); se o site não voltar, o teste
  termina como "SITE INDISPONÍVEL", nem aprovado nem bug.
- **Falha com o site fora do ar:** quando um teste falha ou dá XFAIL, o site é conferido de novo; fora
  do ar, o resultado também vira "SITE INDISPONÍVEL".
- **Disjuntor:** depois de 2 quedas, os testes seguintes nem começam.
- **Retomada:** quando o site volta a responder, a execução é refeita.

## 7. Ambiente e ferramentas

| Item | Valor |
|---|---|
| Linguagem e framework | Python 3.13, Playwright 1.64, pytest 9.2, pytest-playwright |
| Paralelismo | pytest-xdist (`-n auto`) |
| Navegador | Chromium (padrão do `pytest.ini`); Firefox e WebKit só sob demanda |
| Padrão de projeto | Page Object Model (`pages/`) |
| Marcadores | `smoke`, `regression`, `known_bug` (automático) e `allow_js_errors`, com `--strict-markers` |
| Depuração | Trace do Playwright para cada falha (`test-results/`) |
| Relatórios | pytest-html (`reports/report.html`, com screenshot de cada falha) |
| CI | GitHub Actions (`ubuntu-latest`), relatório publicado no GitHub Pages |

## 8. Cronograma de execução

| Gatilho | O que roda |
|---|---|
| Push fora da `main` | Só o que deve passar (`pytest -n auto -m "not known_bug"`), ~17 s |
| Pull request | Suíte completa, com os bugs conhecidos (`pytest -n auto`), ~33 s; gitleaks, pip-audit e CodeQL |
| Push na `main` (merge) | Suíte completa e publicação do relatório no GitHub Pages; gitleaks, pip-audit e CodeQL |
| Diário, 09:00 UTC (06:00 em Brasília) | Suíte completa e publicação no GitHub Pages |
| Semanal | gitleaks e pip-audit (segunda, 05:00 UTC), CodeQL (domingo, 04:00 UTC), Dependabot |
| Manual | Qualquer workflow, pela aba Actions |
| Ao alterar um teste do usuário base | Análise de mutação local (`pytest -m "not known_bug" --base-user problem_user`, e `error_user`) |
| Local | Só o arquivo afetado durante o trabalho; suíte completa (`pytest -n auto`) antes do commit |

O GitHub desativa o agendamento após 60 dias sem atividade no repositório; nesse caso, o workflow é
reativado na aba Actions.

## 9. Dados de teste

- **Usuários:** os 6 perfis fixos do site, com a senha pública `secret_sauce`, em `data/constants.py`.
  Não dá para criar nem apagar contas.
- **Massa:** produtos, ids, mensagens esperadas e dados do checkout (`CHECKOUT_INFO`) em
  `data/constants.py`; preços lidos do catálogo do site na hora.
- **Isolamento:** cada teste recebe um contexto novo do navegador, com cookies e `localStorage`
  vazios; o carrinho sempre começa vazio.
- **Limpeza:** automática. O contexto é fechado no fim do teste, e com ele tudo o que o teste gravou.
- **Efeito fora do navegador:** nenhum. O pedido não é gravado em servidor; a única chamada externa é
  a telemetria que o próprio site envia (BUG-006).

## 10. Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Site instável ou fora do ar | Checagem no início, `safe_goto` com novas tentativas só do carregamento, disjuntor e resultado "SITE INDISPONÍVEL" com código de saída 2 |
| Mudança de preço derrubar os testes | Preço esperado lido do catálogo do site na hora; só o teste de guarda compara com a tabela e diz o que mudou e quanto, marcando como SUSPEITO uma variação acima de 50% |
| Preço errado no próprio catálogo, aceito pelos outros testes | Teste de guarda; a falha pede confirmação com quem define os preços antes de atualizar a tabela |
| Formato do JavaScript do site mudar | Sem plano B silencioso: os testes falham com "não foi possível ler o catálogo" |
| Teste que passa sem pegar defeito | Análise de mutação com os perfis defeituosos do site |
| Outra falha escondida num xfail | `raises=` específico em todo bug conhecido, conferido por `support/known_bugs.py` |
| Asserção negativa passar com a página ainda carregando | Controle positivo antes, `wait_for_render`, `on_page` e `reached`; validado com a CPU 30x mais lenta |
| Condição de corrida do menu (BUG-023) | O `Header` espera o sinal de que o menu fechado foi escondido antes de abri-lo |
| Telemetria sem resposta (BUG-006) | Resultado inconclusivo (skip), nunca um falso "corrigido" |
| Instabilidade escondida por repetição | Nenhum teste é repetido; atalhos proibidos barrados por `test_convencoes.py` |
| Marcador digitado errado | `--strict-markers`: vira erro de coleta |
| Agendamento desativado por inatividade | Aviso no README e no workflow; reativação manual |

## 11. Gestão de defeitos

1. **Investigação:** um comportamento diferente do esperado é investigado; a asserção nunca é afrouxada
   para o teste passar.
2. **Registro:** um defeito confirmado ganha:
   - um ID `BUG-NNN` e uma severidade (crítica, alta, média ou baixa);
   - uma linha no [BUGS.md](../BUGS.md), com as contagens atualizadas;
   - uma seção no [relatório de bugs](relatorio-de-bugs.md) (passos, esperado, obtido, evidência e
     teste), com o PDF gerado de novo por `scripts/gerar_relatorio_pdf.py`;
   - evidência em `docs/evidencias/`;
   - um teste com `xfail(strict=True)`, `raises=` específico e `reason="BUG-NNN (#issue): ..."`;
   - uma issue no GitHub com a label `bug`;
   - as contagens do README e da imagem-resumo atualizadas.
3. **Acompanhamento:** o PR e a execução diária rodam os bugs conhecidos. O resumo do CI mostra, teste a
   teste, se cada bug reproduz, foi corrigido (XPASS), falhou por outro motivo, ficou inconclusivo ou
   não foi avaliado por site indisponível.

## 12. Rastreabilidade

| Elemento | Liga com |
|---|---|
| `# CT-<ARQUIVO>-NN` acima de cada teste | O caso de mesmo ID em [casos-de-teste.md](casos-de-teste.md) |
| `reason="BUG-NNN (#issue): ..."` no xfail | A linha do [BUGS.md](../BUGS.md), a seção do relatório e a issue |
| `RN-NN` citado no teste | A regra em [requisitos-inferidos.md](requisitos-inferidos.md) |
| Teste do usuário base | A linha dele na tabela da [análise de mutação](analise-de-mutacao.md) |

## 13. Entregáveis

| Entregável | Onde |
|---|---|
| Relatório HTML da última execução na `main` | [GitHub Pages](https://angelo-roque-barbosa.github.io/saucedemo-playwright-python/) |
| Relatório HTML e traces de cada execução | Artefato `relatorio-e2e` do CI |
| Resumo da execução e bugs conhecidos teste a teste | Página de cada execução no GitHub Actions |
| Casos de teste | [docs/casos-de-teste.md](casos-de-teste.md) |
| Requisitos inferidos | [docs/requisitos-inferidos.md](requisitos-inferidos.md) |
| Bugs | [BUGS.md](../BUGS.md), [relatório](relatorio-de-bugs.md) ([PDF](relatorio-de-bugs.pdf)) e evidências em `docs/evidencias/` |
| Análise de mutação | [docs/analise-de-mutacao.md](analise-de-mutacao.md) |
| Plano de testes | Este documento |

## 14. Responsabilidades

| Papel | Responsável |
|---|---|
| Definir o que testar, as regras do projeto e aprovar cada mudança | Angelo Roque |
| Propor e escrever código, testes e documentação; investigar o site; rodar os testes | Claude Code (assistente de IA), sob revisão |
| Manter as dependências e as actions atualizadas | Dependabot, com PRs revisados |
