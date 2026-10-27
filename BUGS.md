# Bugs encontrados: SauceDemo (Swag Labs)

Bugs identificados por engenharia reversa do site, cada um com issue, evidências e (exceto o
BUG-023, um bug de tempo) um teste automatizado `xfail(strict=True)`, que avisa quando o bug for
corrigido.

> Relatório completo, com passos, esperado e obtido, evidências e reprodutibilidade:
> **[docs/relatorio-de-bugs.md](docs/relatorio-de-bugs.md)** ([PDF](docs/relatorio-de-bugs.pdf))

**25 bugs:** 8 afetam todos os usuários, inclusive o `standard_user`; 17 são os defeitos de treino
que o SauceDemo injeta de propósito no `problem_user`, no `error_user` e no `visual_user`.
**Ambiente:** https://www.saucedemo.com (produção, Chromium).

| ID | Severidade | Usuário | Área | Resumo | Teste | Issue |
|----|-----------|---------|------|--------|-------|:-----:|
| [BUG-001](docs/relatorio-de-bugs.md#bug-001) | Média | todos | Checkout | Pedido é concluído com o carrinho vazio | `test_cart_checkout.py` | [#2](https://github.com/Arckangelo/saucedemo-playwright-python/issues/2) |
| [BUG-002](docs/relatorio-de-bugs.md#bug-002) | Média | todos | Checkout | Formulário aceita campos preenchidos só com espaços | `test_cart_checkout.py` | [#3](https://github.com/Arckangelo/saucedemo-playwright-python/issues/3) |
| [BUG-003](docs/relatorio-de-bugs.md#bug-003) | Baixa | todos | Carrinho | Reset App State deixa os botões em "Remove" | `test_inventory.py` | [#4](https://github.com/Arckangelo/saucedemo-playwright-python/issues/4) |
| [BUG-004](docs/relatorio-de-bugs.md#bug-004) | Média | todos | Carrinho | Produto inexistente entra no carrinho e é contado | `test_product_detail.py` | [#5](https://github.com/Arckangelo/saucedemo-playwright-python/issues/5) |
| [BUG-005](docs/relatorio-de-bugs.md#bug-005) | Baixa | todos | HTTP | Rotas internas respondem HTTP 404 | `test_console_e_rede.py` | [#6](https://github.com/Arckangelo/saucedemo-playwright-python/issues/6) |
| [BUG-006](docs/relatorio-de-bugs.md#bug-006) | Baixa | todos | Telemetria | Telemetria com credenciais de exemplo (`UNIVERSE`/`TOKEN`) | `test_console_e_rede.py` | [#7](https://github.com/Arckangelo/saucedemo-playwright-python/issues/7) |
| [BUG-007](docs/relatorio-de-bugs.md#bug-007) | Média | problem | Catálogo | Todos os produtos exibem a imagem de erro | `test_inventory.py` | [#8](https://github.com/Arckangelo/saucedemo-playwright-python/issues/8) |
| [BUG-008](docs/relatorio-de-bugs.md#bug-008) | Média | problem | Catálogo | Ordenação não muda a lista | `test_problem_user.py` | [#9](https://github.com/Arckangelo/saucedemo-playwright-python/issues/9) |
| [BUG-009](docs/relatorio-de-bugs.md#bug-009) | **Crítica** | problem | Checkout | Sobrenome digitado vai para o campo de nome | `test_problem_user.py` | [#10](https://github.com/Arckangelo/saucedemo-playwright-python/issues/10) |
| [BUG-010](docs/relatorio-de-bugs.md#bug-010) | Alta | problem | Carrinho | Adicionar falha em 3 produtos e remover falha nos outros 3 | `test_problem_user.py` | [#11](https://github.com/Arckangelo/saucedemo-playwright-python/issues/11) |
| [BUG-011](docs/relatorio-de-bugs.md#bug-011) | Média | problem | Detalhe | Detalhe abre o produto seguinte ao clicado | `test_problem_user.py` | [#12](https://github.com/Arckangelo/saucedemo-playwright-python/issues/12) |
| [BUG-012](docs/relatorio-de-bugs.md#bug-012) | Baixa | problem | Menu | Link About aponta para uma página 404 | `test_menu.py` | [#13](https://github.com/Arckangelo/saucedemo-playwright-python/issues/13) |
| [BUG-013](docs/relatorio-de-bugs.md#bug-013) | Média | problem | Pedido | Carrinho continua cheio depois do pedido | `test_problem_user.py` | [#14](https://github.com/Arckangelo/saucedemo-playwright-python/issues/14) |
| [BUG-014](docs/relatorio-de-bugs.md#bug-014) | Média | error | Catálogo | Ordenação exibe "Sorting is broken!" e não ordena | `test_error_user.py` | [#15](https://github.com/Arckangelo/saucedemo-playwright-python/issues/15) |
| [BUG-015](docs/relatorio-de-bugs.md#bug-015) | Alta | error | Carrinho | Adicionar falha em 3 produtos e remover nos outros 3, com erro JavaScript | `test_error_user.py` | [#16](https://github.com/Arckangelo/saucedemo-playwright-python/issues/16) |
| [BUG-016](docs/relatorio-de-bugs.md#bug-016) | Média | error | Checkout | Campo de sobrenome não aceita texto | `test_error_user.py` | [#17](https://github.com/Arckangelo/saucedemo-playwright-python/issues/17) |
| [BUG-017](docs/relatorio-de-bugs.md#bug-017) | Média | error | Checkout | Checkout avança sem sobrenome | `test_error_user.py` | [#18](https://github.com/Arckangelo/saucedemo-playwright-python/issues/18) |
| [BUG-018](docs/relatorio-de-bugs.md#bug-018) | **Crítica** | error | Pedido | Finish não conclui o pedido | `test_error_user.py` | [#19](https://github.com/Arckangelo/saucedemo-playwright-python/issues/19) |
| [BUG-019](docs/relatorio-de-bugs.md#bug-019) | Alta | visual | Catálogo | Preços do inventário aleatórios e diferentes do cobrado | `test_visual_user.py` | [#20](https://github.com/Arckangelo/saucedemo-playwright-python/issues/20) |
| [BUG-020](docs/relatorio-de-bugs.md#bug-020) | Baixa | visual | Catálogo | Backpack exibe a imagem de erro | `test_visual_user.py` | [#21](https://github.com/Arckangelo/saucedemo-playwright-python/issues/21) |
| [BUG-021](docs/relatorio-de-bugs.md#bug-021) | Média | visual | Layout | Ícone do carrinho deslocado sobre a ordenação | `test_visual_user.py` | [#22](https://github.com/Arckangelo/saucedemo-playwright-python/issues/22) |
| [BUG-022](docs/relatorio-de-bugs.md#bug-022) | Baixa | visual | Layout | Botão do último produto desalinhado | `test_visual_user.py` | [#23](https://github.com/Arckangelo/saucedemo-playwright-python/issues/23) |
| [BUG-023](docs/relatorio-de-bugs.md#bug-023) | Baixa | todos | Menu | Menu lateral abre invisível se clicado logo após a página carregar | sem teste, de propósito: [`scripts/reproduzir_bug_023.py`](scripts/reproduzir_bug_023.py) | [#25](https://github.com/Arckangelo/saucedemo-playwright-python/issues/25) |
| [BUG-024](docs/relatorio-de-bugs.md#bug-024) | Média | todos | Checkout | Resumo abre pela URL e conclui o pedido sem nome, sobrenome e CEP | `test_cart_checkout.py` | [#35](https://github.com/Arckangelo/saucedemo-playwright-python/issues/35) |
| [BUG-025](docs/relatorio-de-bugs.md#bug-025) | Alta | problem | Checkout | Resumo mostra o subtotal em dobro | `test_problem_user.py` | [#37](https://github.com/Arckangelo/saucedemo-playwright-python/issues/37) |

**Por severidade:** 2 críticos, 4 altos, 12 médios e 7 baixos.

## Como rodar os testes dos bugs

```bash
pytest -m known_bug          # só os testes que documentam bugs (aparecem como XFAIL)
pytest -m "not known_bug"    # só o que deve passar
```

Cada teste de bug descreve o comportamento **correto** e aceita apenas a falha específica daquele
bug (`xfail(strict=True, raises=...)`). Se o bug for corrigido, o teste passa a dar XPASS e a suíte
avisa que a marcação pode ser removida.
