"""Verificações compartilhadas por mais de um perfil de usuário.

Cada verificação levanta uma exceção PRÓPRIA quando encontra o defeito. É ela
que o `xfail(raises=...)` aceita: qualquer outra falha (login, seletor, página
que não carregou) continua aparecendo como FAILED, em vez de se esconder
atrás do xfail. É o mesmo padrão do BrokenProductImagesError.
"""

import pytest
from playwright.sync_api import expect

from data.constants import BUG_CHECK_TIMEOUT, Products
from pages import InventoryPage

# problem_user e error_user falham nos MESMOS produtos: não conseguem adicionar
# estes três, e os outros três eles adicionam mas não conseguem remover.
PRODUCTS_THAT_FAIL_TO_ADD = {Products.BOLT_TSHIRT, Products.FLEECE_JACKET, Products.RED_TSHIRT}


class AddToCartFailedError(AssertionError):
    """O clique em "Add to cart" não colocou o produto no carrinho."""


class RemoveFromCartFailedError(AssertionError):
    """O clique em "Remove" não tirou o produto do carrinho."""


class WrongProductDetailError(AssertionError):
    """O detalhe aberto não é o do produto clicado."""


def check_add_and_remove(inventory: InventoryPage, product: str):
    """Adiciona e remove um produto, conferindo o contador e o texto do botão."""
    button = inventory.item_button(product)
    badge = inventory.header.cart_badge
    expect(button).to_have_text("Add to cart")  # pré-condição: carrinho vazio

    button.click()
    try:
        expect(badge).to_have_text("1", timeout=BUG_CHECK_TIMEOUT)
        expect(button).to_have_text("Remove", timeout=BUG_CHECK_TIMEOUT)
    except AssertionError:
        raise AddToCartFailedError(f"'{product}' não entrou no carrinho") from None

    button.click()
    try:
        expect(badge).to_be_hidden(timeout=BUG_CHECK_TIMEOUT)
        expect(button).to_have_text("Add to cart", timeout=BUG_CHECK_TIMEOUT)
    except AssertionError:
        raise RemoveFromCartFailedError(f"'{product}' não saiu do carrinho") from None


def add_remove_params(bug_id: str, username: str) -> list:
    """Um pytest.param por produto, com o xfail da falha que cada um apresenta."""
    params = []
    for product in Products.ALL:
        if product in PRODUCTS_THAT_FAIL_TO_ADD:
            raises, action = AddToCartFailedError, "não adiciona"
        else:
            raises, action = RemoveFromCartFailedError, "adiciona mas não remove"
        params.append(
            pytest.param(
                product,
                id=product,
                marks=pytest.mark.xfail(
                    strict=True, raises=raises, reason=f"{bug_id}: {username} {action} '{product}'"
                ),
            )
        )
    return params


def find_wrong_product_details(inventory: InventoryPage, products: list[str]) -> list[str]:
    """Abre o detalhe de cada produto pelo nome e devolve os que abriram outro item."""
    wrong = []
    for product in products:
        detail = inventory.open_product(product)
        expect(detail.back_button).to_be_visible()  # pré-condição: está no detalhe
        shown = detail.name.inner_text()
        if shown != product:
            wrong.append(f"'{product}' abriu '{shown}' (id={detail.get_product_id()})")
        detail.back_button.click()
        expect(inventory.items.first).to_be_visible()
    return wrong
