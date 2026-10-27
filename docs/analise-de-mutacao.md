# Análise de mutação com os perfis defeituosos

O SauceDemo já traz "mutantes" prontos: o `problem_user`, o `error_user` e o `visual_user` são o
mesmo site com defeitos injetados de propósito. Rodar os testes do `standard_user` com um desses
perfis mostra quais asserções são fracas: **um teste que continua passando numa funcionalidade que o
perfil quebra não protege essa funcionalidade.**

## Como rodar

```bash
pytest -m "not known_bug" --base-user problem_user
pytest -m "not known_bug" --base-user error_user
pytest -m "not known_bug" --base-user visual_user
```

`--base-user` troca o usuário das fixtures `inventory_page` e `standard_session` (os testes do
`standard_user`). Os testes que já escolhem o perfil (login parametrizado, `test_problem_user.py`
etc.) e o oráculo do `visual_user` não mudam. Com `-m "not known_bug"`, entram só os testes que
devem passar.

## Resultado (27/10/2026)

24 testes usam o usuário base. "**pego**" = o teste falhou com o perfil defeituoso (o mutante foi
detectado); "passa" = o teste sobreviveu.

| Arquivo | Teste | problem_user | error_user | visual_user |
|---|---|:-:|:-:|:-:|
| `test_cart_checkout.py` | `test_carrinho_mostra_cada_produto_com_nome_preco_e_quantidade_1` | **pego** | **pego** | passa |
| `test_cart_checkout.py` | `test_carrinho_persiste_apos_recarregar_a_pagina` | **pego** | **pego** | passa |
| `test_cart_checkout.py` | `test_checkout_exige_campos_obrigatorios [sem-cep]` | **pego** | **pego** (erro JS) | passa |
| `test_cart_checkout.py` | `test_checkout_exige_campos_obrigatorios [sem-nome]` | **pego** | **pego** (erro JS) | passa |
| `test_cart_checkout.py` | `test_checkout_exige_campos_obrigatorios [sem-sobrenome]` | passa | **pego** | passa |
| `test_cart_checkout.py` | `test_compra_completa_do_inventario_ao_pedido_concluido` | **pego** | **pego** | passa |
| `test_cart_checkout.py` | `test_concluir_o_pedido_esvazia_o_carrinho` | **pego** | **pego** | passa |
| `test_cart_checkout.py` | `test_remover_do_carrinho_mantem_os_demais_apos_recarregar` | passa | passa | passa |
| `test_cart_checkout.py` | `test_resumo_calcula_subtotal_imposto_e_total` | **pego** | passa | passa |
| `test_inventory.py` | `test_adicionar_atualiza_contador_e_botao` | **pego** | **pego** | passa |
| `test_inventory.py` | `test_ordenacao_de_produtos [nome-A-Z]` | **pego** | **pego** | passa |
| `test_inventory.py` | `test_ordenacao_de_produtos [nome-Z-A]` | **pego** | **pego** | passa |
| `test_inventory.py` | `test_ordenacao_de_produtos [preco-maior-para-menor]` | **pego** | **pego** | **pego** |
| `test_inventory.py` | `test_ordenacao_de_produtos [preco-menor-para-maior]` | **pego** | **pego** | **pego** |
| `test_inventory.py` | `test_remover_o_ultimo_item_esconde_o_contador_e_volta_o_botao` | **pego** | **pego** | passa |
| `test_login.py` | `test_logout_encerra_a_sessao` | passa | passa | passa |
| `test_menu.py` | `test_all_items_volta_para_o_inventario` | passa | passa | passa |
| `test_product_detail.py` | `test_detalhe_mostra_o_produto_clicado` | **pego** | passa | passa |
| `test_product_detail.py` | `test_url_do_detalhe_abre_o_produto_pelo_id [Sauce Labs Backpack]` | passa | passa | passa |
| `test_product_detail.py` | `test_url_do_detalhe_abre_o_produto_pelo_id [Sauce Labs Bike Light]` | passa | passa | passa |
| `test_product_detail.py` | `test_url_do_detalhe_abre_o_produto_pelo_id [Sauce Labs Bolt T-Shirt]` | passa | passa | passa |
| `test_product_detail.py` | `test_url_do_detalhe_abre_o_produto_pelo_id [Sauce Labs Fleece Jacket]` | passa | passa | passa |
| `test_product_detail.py` | `test_url_do_detalhe_abre_o_produto_pelo_id [Sauce Labs Onesie]` | passa | passa | passa |
| `test_product_detail.py` | `test_url_do_detalhe_abre_o_produto_pelo_id [Test.allTheThings() T-Shirt (Red)]` | passa | passa | passa |

### Sobreviventes: todos justificados

Nenhum teste sobrevive numa funcionalidade que o perfil quebra (ver a
[matriz usuário × funcionalidade](requisitos-inferidos.md#matriz-usuário--funcionalidade)):

| Teste | Por que sobreviver é correto |
|---|---|
| `test_url_do_detalhe_abre_o_produto_pelo_id` (6) | Pela URL, o detalhe abre certo em todos os perfis; o BUG-011 do `problem_user` está no clique, coberto por `test_detalhe_mostra_o_produto_clicado`. |
| `test_logout_encerra_a_sessao` e `test_all_items_volta_para_o_inventario` | Logout e All Items funcionam em todos os perfis. |
| `test_remover_do_carrinho_mantem_os_demais_apos_recarregar` | A remoção pela página do carrinho funciona; os BUG-010 e BUG-015 estão nos botões do inventário, cobertos por `test_remover_o_ultimo_item_esconde_o_contador_e_volta_o_botao`. |
| `test_checkout_exige_campos_obrigatorios [sem-sobrenome]` com `problem_user` | Com o sobrenome vazio não há nada digitado no campo, então o BUG-009 (texto que vai para o nome) não se manifesta, e a validação funciona. |
| `test_resumo_calcula_subtotal_imposto_e_total` e `test_detalhe_mostra_o_produto_clicado` com `error_user` | O `error_user` não tem defeito nos cálculos nem no detalhe. |
| Os 22 que passam com `visual_user` | Os defeitos do `visual_user` são visuais (imagens e posições) e de preço no inventário; o preço é pego pela ordenação por preço, e o resto pelos testes dedicados em `test_visual_user.py`, que comparam com o `standard_user`. |

### O que a análise encontrou

1. **Uma asserção fraca, reforçada.** `test_adicionar_atualiza_contador_e_botao` só adicionava
   Backpack e Bike Light, os dois produtos que o `problem_user` e o `error_user` conseguem adicionar,
   e passava com eles. A fraqueza nasceu quando o teste de adicionar e remover foi dividido em dois.
   Agora o teste adiciona os 6 produtos e pega os dois perfis.
2. **Um bug novo, o [BUG-025](relatorio-de-bugs.md#bug-025).** O teste de cálculos do resumo falhou
   com o `problem_user`, numa funcionalidade que a matriz não registrava como quebrada: o subtotal é
   o dobro da soma dos itens.

## Comparação com a linha de base

A mesma análise na versão anterior à revisão da suíte (commit `d1bed47`):

| | Linha de base | Agora |
|---|:-:|:-:|
| Testes que usam o usuário base | 20 | 24 |
| Pegos com `problem_user` | 11 (55%) | 14 (58%) |
| Pegos com `error_user` | 9 (45%) | 13 (54%) |
| Pegos com `visual_user` | 2 (10%) | 2 (8%) |
| **Sobreviventes numa funcionalidade quebrada** | **2** | **0** |

Os 2 sobreviventes da linha de base eram `test_checkout_exige_campos_obrigatorios [sem-nome]` e
`[sem-cep]` com o `error_user`: o campo de sobrenome lançava erro JavaScript (BUG-016) e os testes
passavam assim mesmo. Hoje, qualquer exceção JavaScript não tratada falha o teste.

A porcentagem de "pegos" não chega a 100% de propósito: ela inclui testes de funcionalidades que o
perfil **não** quebra, que devem continuar passando. A medida que importa é a última linha.
