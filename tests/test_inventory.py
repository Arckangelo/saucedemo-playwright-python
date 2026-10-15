"""Inventário: ordenação, integridade das imagens e manipulação do carrinho."""

import pytest
from playwright.sync_api import expect

from data.constants import BUG_CHECK_TIMEOUT, PASSWORD, TOTAL_PRODUCTS, Products, Users
from pages import InventoryPage, LoginPage
from pages.base_page import parse_money
from support.bug_checks import bug_check


@pytest.mark.parametrize(
    "option, sort_by, descending",
    [
        pytest.param("az", "name", False, id="nome-A-Z"),
        pytest.param("za", "name", True, id="nome-Z-A"),
        pytest.param("lohi", "price", False, id="preco-menor-para-maior"),
        pytest.param("hilo", "price", True, id="preco-maior-para-menor"),
    ],
)
def test_ordenacao_de_produtos(
    inventory_page: InventoryPage, option: str, sort_by: str, descending: bool
):
    # Garante que a lista já foi renderizada antes de lê-la (ver all_inner_texts).
    expect(inventory_page.items).to_have_count(TOTAL_PRODUCTS)

    # O resultado esperado é CALCULADO a partir do que está na tela, e não
    # escrito à mão: se o catálogo mudar, o teste continua válido.
    if sort_by == "name":
        locator = inventory_page.item_names
        expected = sorted(inventory_page.get_item_names(), reverse=descending)
    else:
        locator = inventory_page.item_prices
        expected = sorted(
            inventory_page.item_prices.all_inner_texts(),
            key=parse_money,
            reverse=descending,
        )

    # Pré-condição: a lista NÃO pode já estar na ordem esperada. A página abre
    # em A-Z, então sem isto o caso "az" passaria mesmo com a ordenação
    # quebrada (um falso positivo). Partimos de uma ordem diferente da alvo.
    inventory_page.sort_by("za" if option == "az" else "az")
    expect(locator).not_to_have_text(expected)

    inventory_page.sort_by(option)

    # Passar uma LISTA para to_have_text compara todos os elementos, na ordem,
    # com retry automático até a re-renderização terminar.
    expect(inventory_page.sort_select).to_have_value(option)
    expect(locator).to_have_text(expected)


class BrokenProductImagesError(AssertionError):
    """Falha específica do bug de imagens.

    Por que uma exceção própria? O xfail, por padrão, aceita QUALQUER falha
    como "esperada" — inclusive de pré-condições. Se o login ou o seletor das
    imagens quebrasse, o teste continuaria aparecendo como XFAIL sem verificar
    nada. Com `raises=BrokenProductImagesError`, só esta falha é tolerada;
    qualquer outra aparece como FAILED.
    """


@pytest.mark.parametrize(
    "username",
    [
        pytest.param(Users.STANDARD, id="standard_user"),
        pytest.param(
            Users.PROBLEM,
            id="problem_user",
            marks=pytest.mark.xfail(
                strict=True,
                raises=BrokenProductImagesError,
                reason="BUG-007: problem_user exibe a mesma imagem (sl-404) em todos os produtos",
            ),
        ),
    ],
)
def test_cada_produto_exibe_sua_propria_imagem(login_page: LoginPage, username: str):
    login_page.login(username, PASSWORD)
    inventory = InventoryPage(login_page.page)
    expect(inventory.item_images).to_have_count(TOTAL_PRODUCTS)

    sources = inventory.get_image_sources()

    duplicated = len(set(sources)) != len(sources)
    error_image = any("sl-404" in src for src in sources)
    if duplicated or error_image:
        raise BrokenProductImagesError(f"Imagens repetidas ou de erro (404): {sources}")


def test_adicionar_e_remover_produtos_atualiza_o_carrinho(inventory_page: InventoryPage):
    badge = inventory_page.header.cart_badge

    inventory_page.add_to_cart(Products.BACKPACK)
    expect(badge).to_have_text("1")
    expect(inventory_page.item_button(Products.BACKPACK)).to_have_text("Remove")

    inventory_page.add_to_cart(Products.BIKE_LIGHT)
    expect(badge).to_have_text("2")

    inventory_page.remove_from_cart(Products.BACKPACK)
    expect(badge).to_have_text("1")
    expect(inventory_page.item_button(Products.BACKPACK)).to_have_text("Add to cart")

    inventory_page.remove_from_cart(Products.BIKE_LIGHT)
    # Com o carrinho vazio, o contador some da tela.
    expect(badge).to_be_hidden()


class StaleCartButtonsError(AssertionError):
    """Depois do Reset App State, os botões continuam como se os itens estivessem no carrinho."""


@pytest.mark.regression
@pytest.mark.xfail(
    strict=True,
    raises=StaleCartButtonsError,
    reason="BUG-003: Reset App State esvazia o carrinho, mas os botões continuam em 'Remove'",
)
def test_reset_app_state_restaura_os_botoes(inventory_page: InventoryPage):
    products = [Products.BACKPACK, Products.BIKE_LIGHT]
    for product in products:
        inventory_page.add_to_cart(product)
    expect(inventory_page.header.cart_badge).to_have_text("2")

    inventory_page.header.reset_app_state()
    expect(inventory_page.header.cart_badge).to_be_hidden()  # pré-condição: o reset aconteceu

    for product in products:
        with bug_check(StaleCartButtonsError, f"Botão de '{product}' continua em 'Remove'"):
            expect(inventory_page.item_button(product)).to_have_text(
                "Add to cart", timeout=BUG_CHECK_TIMEOUT
            )