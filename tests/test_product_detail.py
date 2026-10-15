"""Detalhe do produto (/inventory-item.html?id=N) e validação do carrinho."""

import pytest
from playwright.sync_api import expect

from data.constants import PRODUCT_IDS, TOTAL_PRODUCTS, Messages, Products
from pages import InventoryPage, ProductDetailPage
from support.bug_checks import bug_check, find_wrong_product_details, wait_for_render


class PhantomCartItemError(AssertionError):
    """O contador do carrinho conta um produto que não existe no catálogo."""


def test_detalhe_mostra_o_produto_clicado(inventory_page: InventoryPage):
    assert find_wrong_product_details(inventory_page, Products.ALL) == []


@pytest.mark.parametrize(
    "product, product_id", [pytest.param(name, pid, id=name) for name, pid in PRODUCT_IDS.items()]
)
def test_url_do_detalhe_abre_o_produto_pelo_id(inventory_page: InventoryPage, product: str, product_id: int):
    detail = ProductDetailPage(inventory_page.page).open_by_id(product_id)
    expect(detail.name).to_have_text(product)


@pytest.mark.regression
@pytest.mark.parametrize("invalid_id", ["6", "-1"])
@pytest.mark.xfail(
    strict=True,
    raises=PhantomCartItemError,
    reason="BUG-004 (#5): produto inexistente pode ser adicionado e conta no carrinho",
)
def test_produto_inexistente_nao_entra_no_carrinho(inventory_page: InventoryPage, invalid_id: str):
    detail = ProductDetailPage(inventory_page.page).open_by_id(invalid_id)
    expect(detail.name).to_have_text(Messages.ITEM_NOT_FOUND)  # pré-condição

    if detail.add_to_cart_button.is_visible():
        detail.add_to_cart_button.click()
    wait_for_render(detail.page)
    badge = detail.header.cart_badge
    with bug_check(PhantomCartItemError, lambda: f"Contador mostra {badge.all_inner_texts()} para o id {invalid_id}"):
        assert badge.all_inner_texts() == []


@pytest.mark.regression
@pytest.mark.xfail(
    strict=True,
    raises=PhantomCartItemError,
    reason="BUG-004 (#5): o carrinho conta ids inexistentes vindos do localStorage",
)
def test_carrinho_ignora_ids_inexistentes_no_localstorage(inventory_page: InventoryPage):
    page = inventory_page.page
    page.evaluate("() => localStorage.setItem('cart-contents', '[999]')")
    page.reload()
    expect(inventory_page.items).to_have_count(TOTAL_PRODUCTS)

    # A lista e o cabeçalho são desenhados juntos; os 6 itens na tela são o sinal
    # de que o contador também já foi calculado a partir do localStorage.
    wait_for_render(page)
    badge = inventory_page.header.cart_badge
    with bug_check(PhantomCartItemError, lambda: f"Contador mostra {badge.all_inner_texts()} com o carrinho vazio"):
        assert badge.all_inner_texts() == []
