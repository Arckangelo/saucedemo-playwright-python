# Insumos do ambiente

As cinco informações que uma suíte E2E precisa ter antes do primeiro teste, respondidas para o
SauceDemo. Sem elas, a suíte pode passar sem testar nada, acusar um bug que não existe ou sujar o
ambiente. Este documento resume e aponta para onde cada assunto está detalhado. Ele deve ser
atualizado quando algum desses pontos mudar.

| # | Insumo | Resposta curta |
|:-:|---|---|
| 1 | [Ambiente e permissão](#1-ambiente-e-permissão) | Produção pública de terceiros, compartilhada; nada é criado no servidor |
| 2 | [Fonte de verdade](#2-fonte-de-verdade) | Sem API nem banco: catálogo lido do JavaScript do site na hora, código-fonte oficial, `standard_user` como oráculo e o estado gravado no navegador |
| 3 | [Usuários e dados](#3-usuários-e-dados) | 6 usuários fixos do site; os dados de cada teste vivem num contexto novo do navegador e somem com ele |
| 4 | [Critérios de aceite e bordas](#4-critérios-de-aceite-e-bordas) | Regras RN-01 a RN-20 inferidas por engenharia reversa; o efeito é conferido no `localStorage` e no cookie |
| 5 | [Instabilidades](#5-instabilidades) | Checagem no início e em toda página aberta; queda vira "SITE INDISPONÍVEL"; a página real tem o título "Swag Labs" |

---

## 1. Ambiente e permissão

- **URL:** https://www.saucedemo.com (`base_url` no `pytest.ini`; pode ser trocada com
  `pytest --base-url`).
- **Tipo:** produção. É um site público de demonstração da Sauce Labs, feito para praticar
  automação. Não existe ambiente de homologação.
- **Compartilhado:** sim, com qualquer pessoa na internet. Não temos controle sobre o site, as
  versões nem as quedas.
- **O que pode ser criado e apagado:** nada no servidor. O site só tem front-end
  ([código-fonte oficial](https://github.com/saucelabs/sample-app-web)): login, carrinho e pedido
  acontecem no navegador. Os testes gravam apenas no próprio navegador (cookie e `localStorage`).
- **Cuidados por ser um site de terceiros:** sem teste de carga. A execução em paralelo
  (`pytest -n auto`) usa só os núcleos da máquina, e cada processo faz um login por usuário, que é
  reaproveitado pelos testes.

## 2. Fonte de verdade

O site não tem API nem banco acessível. Por isso, os valores esperados vêm destas fontes, nunca da
tela que está sendo testada:

| Fonte | O que confere | Onde |
|---|---|---|
| Catálogo do site, lido na hora | nome e preço dos 6 produtos, tirados do JavaScript da aplicação (o mesmo de onde a tela os tira); ordenação, linhas, subtotal, imposto e total são calculados a partir dele | fixture `catalog_prices`, `support/catalog.py` |
| Código-fonte oficial do site | regras que a tela não explica, como o imposto de 8% (RN-17) | [sample-app-web](https://github.com/saucelabs/sample-app-web) |
| `standard_user` como oráculo | o que os outros perfis deveriam ver (imagens, posições), lido em outro contexto durante o teste | fixture `oracle_inventory` no `conftest.py` |
| Estado gravado no navegador | o efeito da ação, onde a tela não prova nada: ids do carrinho e cookie de sessão | `support/state.py` (`cart_ids`, `session_cookie`) |

Do JavaScript só saem nomes e preços: a regra do imposto continua no teste (`TAX_RATE`). Se o formato
do arquivo mudar e o catálogo não puder ser lido com segurança, os testes falham com "não foi possível
ler o catálogo", sem plano B silencioso.

**Limite:** um preço errado no próprio catálogo (cobrado errado de forma coerente em todas as telas)
não é percebido pelos testes que leem o catálogo. Só o teste de guarda (`tests/test_catalogo.py`), que
compara o catálogo com a tabela `PRODUCT_PRICES` conferida em 27/10/2026, avisa que um preço mudou,
com a variação em porcentagem e a marca SUSPEITO acima de 50% (ex.: "29.99 → 2.99 (-90%, SUSPEITO)").
Nesse caso é preciso confirmar com quem define os preços: a tabela só é atualizada se a mudança for
intencional; se foi engano, é bug do site. Afrouxar a
asserção nunca é a saída (regra 3 do `CLAUDE.md`).

## 3. Usuários e dados

- **Usuários:** os 6 perfis fixos do site (`standard_user`, `locked_out_user`, `problem_user`,
  `performance_glitch_user`, `error_user` e `visual_user`), todos com a senha pública
  `secret_sauce`. Ficam em `data/constants.py`. Não dá para criar nem apagar contas, e ninguém
  consegue alterá-las: o site aceita só esses nomes.
- **Dados de cada teste:** cada teste recebe um contexto novo do navegador, com cookies e
  `localStorage` vazios. O login é reaproveitado por usuário (o cookie é copiado para o contexto
  novo) e o carrinho é montado com `cart_with(...)` nesse mesmo contexto. Nenhum teste depende de
  dado deixado por outro.
- **Limpeza:** automática. O contexto é fechado no fim de cada teste, e com ele tudo o que o teste
  gravou.
- **O que não pode ser limpo:** nada fica no SauceDemo; o pedido não é gravado em servidor
  (o Finish só esvazia o carrinho no `localStorage`, RN-19). O único efeito fora do navegador é a
  telemetria que o próprio site envia ao Backtrace na primeira carga de cada sessão (BUG-006), que
  não depende dos testes.

## 4. Critérios de aceite e bordas

Não existe especificação oficial. Os critérios foram inferidos do comportamento observado e estão em
[requisitos-inferidos.md](requisitos-inferidos.md):

- **regras de negócio** RN-01 a RN-20 (autenticação, catálogo, carrinho e checkout);
- **mapa de telas** com os `data-test` de cada uma;
- **como o estado funciona** (cookie, `localStorage`, URL) e o que acontece quando é manipulado;
- **matriz usuário × funcionalidade**, que diz o que é bug e o que é comportamento intencional de
  cada perfil.

**Como o efeito é conferido:** como não há servidor, "efeito no servidor" vira "efeito no estado".
Os testes leem o `localStorage` e o cookie (ids gravados ao adicionar, carrinho vazio depois do
pedido, cookie apagado no logout), em vez de confiar só na mensagem de sucesso.

**Bordas já cobertas:** campos só com espaços (BUG-002), carrinho vazio no checkout (BUG-001), ids
inexistentes na URL e no carrinho (RN-10, BUG-004), cookie manipulado (RN-06), resumo aberto pela URL
sem o passo 1 (BUG-024). As regras ainda sem teste estão nos
[próximos passos do README](../README.md#próximos-passos).

## 5. Instabilidades

| Instabilidade | Como reconhecer | Como a suíte trata |
|---|---|---|
| Site fora do ar antes de começar | sem resposta em 15 s, ou HTTP de erro na página inicial | a checagem do `pytest_sessionstart` interrompe a execução com "SITE INDISPONÍVEL"; nenhum teste roda |
| Site cai no meio da execução | ao abrir uma página: HTTP 429, 502–504 ou 520–524, sem resposta, ou página sem o título "Swag Labs" | `safe_goto` tenta o carregamento até 3 vezes; se o site não voltar, o teste termina como "SITE INDISPONÍVEL"; depois de 2 quedas, o disjuntor impede os testes seguintes; a execução termina com código 2 |
| Site cai no meio de um teste, depois de um clique ou reload | o teste falha (ou dá XFAIL) e, logo depois, o site não passa na checagem | o resultado vira "SITE INDISPONÍVEL", com a falha original no motivo; com o site no ar, a falha continua falha |
| Página de erro ou de desafio que responde 200 (ex.: Cloudflare) | a página não tem o título `<title>Swag Labs</title>` | as mesmas checagens: o título é o marcador da página real |
| Telemetria do Backtrace sem resposta (desde 27/10/2026) | a requisição sai, mas não volta antes do limite de 15 s do próprio site | o teste do BUG-006 é pulado (skip, inconclusivo), nunca vira "corrigido" |
| Menu lateral clicado cedo demais em máquina lenta (BUG-023) | menu "aberto", mas invisível | o `Header` espera o sinal de que o menu fechado foi escondido antes de abri-lo |
| Atraso de ~5 s do `performance_glitch_user` | comportamento intencional do perfil | tempo limite maior (`SLOW_RENDER_TIMEOUT`) só onde o inventário é renderizado |

**Não é instabilidade:** as rotas internas respondem **HTTP 404** mesmo funcionando, porque o site é
uma aplicação de página única (BUG-005). Um 404 numa rota interna não indica site fora do ar.

**Limite conhecido:** a checagem depois de uma falha é feita logo depois dela. Se o site cair e voltar
no meio de um teste, antes da checagem, a falha aparece como falha comum. O trace do Playwright mostra
as respostas da rede de cada falha (`test-results/`), o que permite reconhecer esse caso.

**Sem repetição de teste:** a suíte não repete teste que falhou (regra 5 do `CLAUDE.md`), porque
repetir esconde instabilidade em vez de mostrá-la.
