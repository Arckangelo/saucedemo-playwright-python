"""problem_user: defeitos de interface confirmados por engenharia reversa.

Cada teste descreve o comportamento CORRETO (o do standard_user). Enquanto o
bug existir, o teste falha com a exceção específica do defeito e aparece como
XFAIL; se o bug for corrigido, o xfail(strict=True) avisa (XPASS vira falha).
Detalhes de cada bug em docs/relatorio-de-bugs.md.
"""

import pytest
from playwright.sync_api import Page, expect

from data.constants import BUG_CHECK_TIMEOUT, TOTAL_PRODUCTS, Messages, Products, Users
from pages import CheckoutOverviewPage
from support.bug_checks import (
    WrongProductDetailError,
    add_remove_params,
    check_add_and_remove,
    find_wrong_product_details,
)

pytestmark = pytest.mark.regression


class SortNotAppliedError(AssertionError):
    """A lista não mudou de ordem depois de escolher outra ordenação."""


class LastNameFieldError(AssertionError):
    """O texto digitado no sobrenome não ficou no campo de sobrenome."""


class CartNotClearedError(AssertionError):
    """O carrinho continuou com itens depois de o pedido ser concluído."""


@pytest.mark.xfail(
    strict=True,
    raises=SortNotAppliedError,
    reason="BUG-008: a ordenação do problem_user não muda a lista e volta para A-Z",
)
def test_ordenacao_por_nome_z_a(login_as):
    inventory = login_as(Users.PROBLEM)
    expect(inventory.items).to_have_count(TOTAL_PRODUCTS)
    expected = sorted(inventory.get_item_names(), reverse=True)

    inventory.sort_by("za")
    try:
        expect(inventory.sort_select).to_have_value("za", timeout=BUG_CHECK_TIMEOUT)
        expect(inventory.item_names).to_have_text(expected, timeout=BUG_CHECK_TIMEOUT)
    except AssertionError:
        raise SortNotAppliedError(f"Ordem exibida: {inventory.get_item_names()}") from None


@pytest.mark.parametrize("product", add_remove_params("BUG-010", Users.PROBLEM))
def test_adicionar_e_remover_cada_produto(login_as, product: str):
    check_add_and_remove(login_as(Users.PROBLEM), product)


@pytest.mark.xfail(
    strict=True,
    raises=WrongProductDetailError,
    reason="BUG-011: o problem_user abre o detalhe do produto seguinte (id + 1)",
)
def test_detalhe_mostra_o_produto_clicado(login_as):
    inventory = login_as(Users.PROBLEM)
    wrong = find_wrong_product_details(inventory, Products.ALL)
    if wrong:
        raise WrongProductDetailError("; ".join(wrong))


@pytest.mark.xfail(
    strict=True,
    raises=LastNameFieldError,
    reason="BUG-009: no problem_user o sobrenome digitado vai para o campo de nome",
)
def test_sobrenome_fica_no_campo_de_sobrenome(login_as):
    inventory = login_as(Users.PROBLEM)
    inventory.add_to_cart(Products.BACKPACK)
    information = inventory.go_to_cart().checkout()

    information.last_name_input.fill("Souza")

    values = information.get_values()
    if values != {"first_name": "", "last_name": "Souza", "postal_code": ""}:
        raise LastNameFieldError(f"Campos após digitar só o sobrenome: {values}")


@pytest.mark.xfail(
    strict=True,
    raises=CartNotClearedError,
    reason="BUG-013: no problem_user o carrinho continua cheio depois de concluir o pedido",
)
def test_carrinho_esvazia_apos_concluir_o_pedido(login_as, page: Page):
    inventory = login_as(Users.PROBLEM)
    inventory.add_to_cart(Products.BACKPACK)  # este produto o problem_user consegue adicionar
    expect(inventory.header.cart_badge).to_have_text("1")

    # O formulário do passo 1 está quebrado para este perfil (BUG-009), então
    # vamos direto ao resumo para isolar o comportamento do Finish.
    complete = CheckoutOverviewPage(page).open().finish()
    expect(complete.complete_header).to_have_text(Messages.ORDER_COMPLETE)

    try:
        expect(complete.header.cart_badge).to_be_hidden(timeout=BUG_CHECK_TIMEOUT)
    except AssertionError:
        badge = complete.header.cart_badge.inner_text()
        raise CartNotClearedError(f"Contador após o pedido: {badge}") from None
