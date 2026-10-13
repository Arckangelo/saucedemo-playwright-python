"""Carrinho e checkout: persistência, validação de formulário e compra completa."""

import json
import re
from decimal import ROUND_HALF_UP, Decimal

import pytest
from playwright.sync_api import expect

from data.constants import TAX_RATE, Messages, Products
from pages import CartPage, CheckoutInformationPage, InventoryPage


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
    page = checkout_information_page
    page.fill_information(first_name, last_name, postal_code)
    page.continue_button.click()

    expect(page.error_message).to_have_text(expected_error)
    expect(page.page).to_have_url(re.compile(re.escape(CheckoutInformationPage.PATH) + "$"))


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
