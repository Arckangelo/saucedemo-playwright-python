"""Inventário: ordenação, integridade das imagens e manipulação do carrinho."""

import pytest
from playwright.sync_api import Page, expect

from data.constants import PASSWORD, PRODUCT_IDS, PRODUCT_PRICES, TOTAL_PRODUCTS, Products, Users
from pages import InventoryPage, LoginPage
from support.bug_checks import bug_check, wait_for_render


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
    # Garante que a lista já foi renderizada: sem isso, a pré-condição abaixo
    # (not_to_have_text) passaria com a lista ainda vazia.
    expect(inventory_page.items).to_have_count(TOTAL_PRODUCTS)

    # O resultado esperado é CALCULADO a partir da tabela de referência, não da
    # tela: se o site exibisse um produto ou preço errado, ordenar o que está
    # na tela não perceberia. Se o catálogo mudar, a tabela é atualizada de
    # propósito, num lugar só.
    catalog = PRODUCT_PRICES.values()
    if sort_by == "name":
        locator = inventory_page.item_names
        expected = sorted((product["name"] for product in catalog), reverse=descending)
    else:
        locator = inventory_page.item_prices
        prices = sorted((product["price"] for product in catalog), reverse=descending)
        expected = [f"${price}" for price in prices]

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
                reason="BUG-007 (#8): problem_user exibe a mesma imagem (sl-404) em todos os produtos",
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


def test_adicionar_atualiza_contador_e_botao(inventory_page: InventoryPage):
    # Clica na tela de propósito: é este teste que garante o botão Add to cart.
    # Dois produtos, para o contador provar que conta (e não mostra sempre 1).
    products = [Products.BACKPACK, Products.BIKE_LIGHT]
    for product in products:
        inventory_page.add_to_cart(product)

    expect(inventory_page.header.cart_badge).to_have_text("2")
    for product in products:
        expect(inventory_page.item_button(product)).to_have_text("Remove")


def test_remover_o_ultimo_item_esconde_o_contador_e_volta_o_botao(
    page: Page, standard_session, cart_with
):
    # O carrinho é montado pelo localStorage (adicionar tem teste próprio), mas
    # a remoção é clicada na tela: é este teste que garante o botão Remove.
    cart_with(PRODUCT_IDS[Products.BACKPACK])
    inventory = InventoryPage(page).open()
    expect(inventory.header.cart_badge).to_have_text("1")  # pré-condição: o carrinho foi montado

    inventory.remove_from_cart(Products.BACKPACK)

    # Com o carrinho vazio, o contador some e o botão volta a oferecer a adição.
    # Não conferimos o localStorage: neste site o contador é calculado a partir
    # dele, então uma remoção não gravada já faz o contador continuar na tela.
    expect(inventory.header.cart_badge).to_be_hidden()
    expect(inventory.item_button(Products.BACKPACK)).to_have_text("Add to cart")


class StaleCartButtonsError(AssertionError):
    """Depois do Reset App State, os botões continuam como se os itens estivessem no carrinho."""


@pytest.mark.regression
@pytest.mark.xfail(
    strict=True,
    raises=StaleCartButtonsError,
    reason="BUG-003 (#4): Reset App State esvazia o carrinho, mas os botões continuam em 'Remove'",
)
def test_reset_app_state_restaura_os_botoes(page: Page, standard_session, cart_with):
    products = [Products.BACKPACK, Products.BIKE_LIGHT]
    cart_with(*(PRODUCT_IDS[product] for product in products))
    inventory = InventoryPage(page).open()
    expect(inventory.header.cart_badge).to_have_text("2")  # pré-condição: o carrinho foi montado

    inventory.header.reset_app_state()
    expect(inventory.header.cart_badge).to_be_hidden()  # pré-condição: o reset aconteceu

    # O contador sumiu (sinal acima): a tela já reagiu ao reset.
    wait_for_render(inventory.page)
    for product in products:
        button = inventory.item_button(product)
        with bug_check(StaleCartButtonsError, f"Botão de '{product}' continua em 'Remove'"):
            assert button.inner_text() == "Add to cart"