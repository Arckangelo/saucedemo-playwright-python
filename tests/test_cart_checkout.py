"""Carrinho e checkout: persistência, validação de formulário e compra completa."""

import json
import re
from decimal import ROUND_HALF_UP, Decimal

import pytest
from playwright.sync_api import expect

from data.constants import BUG_CHECK_TIMEOUT, TAX_RATE, Messages, Products
from pages import CartPage, CheckoutInformationPage, InventoryPage
from support.bug_checks import bug_check


class EmptyCartOrderError(AssertionError):
    """Um pedido sem nenhum item foi concluído."""


class BlankFieldAcceptedError(AssertionError):
    """Um campo preenchido só com espaços foi aceito como válido."""


@pytest.fixture
def checkout_information_page(inventory_page: InventoryPage) -> CheckoutInformationPage:
    """Fixture local (vale só para este arquivo): leva o teste até o passo 1 do checkout.

    Note que ela depende de outra fixture (inventory_page, do conftest).
    O pytest resolve a cadeia sozinho: cookies -> inventário -> carrinho -> checkout.
    """
    inventory_page.add_to_cart(Products.BACKPACK)
    return inventory_page.go_to_cart().checkout()


@pytest.mark.smoke
def test_compra_completa_com_validacao_dos_valores(inventory_page: InventoryPage):
    products = [Products.BACKPACK, Products.BOLT_TSHIRT, Products.ONESIE]
    for product in products:
        inventory_page.add_to_cart(product)

    cart = inventory_page.go_to_cart()
    expect(cart.item_names).to_have_text(products)

    information = cart.checkout()
    information.fill_information("Ana", "Souza", "72980-000")
    overview = information.continue_to_overview()
    expect(overview.item_names).to_have_text(products)

    # Validação dos cálculos: em vez de comparar com valores fixos, recalculamos
    # a partir dos preços exibidos e conferimos a matemática do site.
    subtotal = overview.get_subtotal()
    tax = overview.get_tax()
    total = overview.get_total()
    expected_tax = (subtotal * Decimal(TAX_RATE)).quantize(Decimal("0.01"), ROUND_HALF_UP)

    assert subtotal == sum(overview.get_item_prices())
    assert tax == expected_tax
    assert total == subtotal + tax

    complete = overview.finish()
    expect(complete.complete_header).to_have_text(Messages.ORDER_COMPLETE)
    expect(complete.header.cart_badge).to_be_hidden()


@pytest.mark.parametrize(
    "first_name, last_name, postal_code, expected_error",
    [
        pytest.param("", "Souza", "72980-000", Messages.FIRST_NAME_REQUIRED, id="sem-nome"),
        pytest.param("Ana", "", "72980-000", Messages.LAST_NAME_REQUIRED, id="sem-sobrenome"),
        pytest.param("Ana", "Souza", "", Messages.POSTAL_CODE_REQUIRED, id="sem-cep"),
    ],
)
def test_checkout_exige_campos_obrigatorios(
    checkout_information_page: CheckoutInformationPage,
    first_name: str,
    last_name: str,
    postal_code: str,
    expected_error: str,
):
    checkout = checkout_information_page
    checkout.fill_information(first_name, last_name, postal_code)
    checkout.continue_button.click()

    expect(checkout.error_message).to_have_text(expected_error)
    # Continua no passo 1: o formulário inválido não pode avançar.
    expect(checkout.page).to_have_url(re.compile(re.escape(checkout.PATH) + "$"))


@pytest.mark.regression
@pytest.mark.parametrize(
    "first_name, last_name, postal_code, blank_field",
    [
        pytest.param("   ", "Souza", "72980-000", "nome", id="nome-so-espacos"),
        pytest.param("Ana", "   ", "72980-000", "sobrenome", id="sobrenome-so-espacos"),
        pytest.param("Ana", "Souza", "   ", "CEP", id="cep-so-espacos"),
    ],
)
@pytest.mark.xfail(
    strict=True,
    raises=BlankFieldAcceptedError,
    reason="BUG-002: o checkout aceita campos preenchidos só com espaços",
)
def test_checkout_rejeita_campos_so_com_espacos(
    checkout_information_page: CheckoutInformationPage,
    first_name: str,
    last_name: str,
    postal_code: str,
    blank_field: str,
):
    checkout = checkout_information_page
    checkout.fill_information(first_name, last_name, postal_code)
    checkout.continue_button.click()

    with bug_check(
        BlankFieldAcceptedError,
        lambda: f"Campo {blank_field} só com espaços foi aceito; página atual: {checkout.page.url}",
    ):
        expect(checkout.error_message).to_be_visible(timeout=BUG_CHECK_TIMEOUT)


def _blocked(locator) -> bool:
    """True se o elemento não aparecer a tempo: a etapa foi bloqueada."""
    try:
        expect(locator).to_be_visible(timeout=BUG_CHECK_TIMEOUT)
    except AssertionError:
        return True
    return False


@pytest.mark.regression
@pytest.mark.xfail(
    strict=True,
    raises=EmptyCartOrderError,
    reason="BUG-001: é possível concluir um pedido com o carrinho vazio",
)
def test_nao_conclui_pedido_com_carrinho_vazio(inventory_page: InventoryPage):
    cart = inventory_page.go_to_cart()
    expect(cart.items).to_have_count(0)  # pré-condição: carrinho vazio

    # A correção pode bloquear o pedido em qualquer etapa (botão Checkout
    # escondido ou desabilitado, formulário que não avança, Finish que não
    # conclui). Cada bloqueio conta como comportamento correto: o teste passa,
    # e o xfail(strict=True) avisa que o bug foi corrigido.
    if _blocked(cart.checkout_button) or not cart.checkout_button.is_enabled():
        return
    information = cart.checkout()
    information.fill_information("Ana", "Souza", "72980-000")
    overview = information.continue_to_overview()
    if _blocked(overview.finish_button):
        return
    complete = overview.finish()
    if _blocked(complete.complete_header):
        return
    raise EmptyCartOrderError(f"Pedido vazio concluído: {complete.complete_header.inner_text()}")


def test_carrinho_persiste_apos_recarregar_a_pagina(inventory_page: InventoryPage):
    inventory_page.add_to_cart(Products.BACKPACK)
    inventory_page.add_to_cart(Products.FLEECE_JACKET)

    inventory_page.page.reload()
    expect(inventory_page.header.cart_badge).to_have_text("2")

    # O saucedemo guarda o carrinho no localStorage. page.evaluate() roda
    # JavaScript dentro do navegador e devolve o resultado para o Python
    # (parecido com cy.window().then(win => win.localStorage...)).
    stored = inventory_page.page.evaluate("() => localStorage.getItem('cart-contents')")
    assert len(json.loads(stored)) == 2

    cart: CartPage = inventory_page.go_to_cart()
    expect(cart.item_names).to_have_text([Products.BACKPACK, Products.FLEECE_JACKET])
