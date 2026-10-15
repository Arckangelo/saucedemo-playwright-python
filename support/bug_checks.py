"""Verificações compartilhadas por mais de um perfil de usuário.

Cada verificação levanta uma exceção PRÓPRIA quando encontra o defeito. É ela
que o `xfail(raises=...)` aceita: qualquer outra falha (login, seletor, página
que não carregou) continua aparecendo como FAILED, em vez de se esconder
atrás do xfail. É o mesmo padrão do BrokenProductImagesError.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager

import pytest
from playwright.sync_api import Page, expect

from data.constants import Products
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


_TWO_FRAMES = "() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(() => r(true))))"


def wait_for_render(page: Page):
    """Espera o navegador desenhar dois quadros depois da última ação.

    É o sinal concreto de que a ação foi processada: o navegador só desenha um
    quadro depois de executar o evento (clique, troca de opção) e a
    atualização de tela que ele dispara. Depois disso, ler o estado SEM
    esperar responde "o efeito aconteceu?" em milissegundos, em vez de
    aguardar um tempo fixo por algo que não vai acontecer.
    """
    page.evaluate(_TWO_FRAMES)


@contextmanager
def bug_check(error: type[AssertionError], message: str | Callable[[], str]) -> Iterator[None]:
    """Transforma a falha de uma verificação na exceção específica do bug.

    Uso:
        button.click()
        wait_for_render(page)
        with bug_check(AddToCartFailedError, "não entrou no carrinho"):
            assert badge.all_inner_texts() == ["1"]

    A falha original fica encadeada (`from cause`), então o relatório mostra
    também o que foi lido. `message` pode ser uma função, para ler o estado da
    página só quando a verificação falha.
    """
    try:
        yield
    except AssertionError as cause:
        raise error(message() if callable(message) else message) from cause


def check_add_and_remove(inventory: InventoryPage, product: str):
    """Adiciona e remove um produto, conferindo o contador e o texto do botão."""
    button = inventory.item_button(product)
    badge = inventory.header.cart_badge
    expect(button).to_have_text("Add to cart")  # pré-condição: carrinho vazio

    # all_inner_texts() e inner_text() de um elemento que existe não esperam:
    # leem o estado já renderizado.
    button.click()
    wait_for_render(inventory.page)
    with bug_check(AddToCartFailedError, f"'{product}' não entrou no carrinho"):
        assert badge.all_inner_texts() == ["1"], f"contador: {badge.all_inner_texts()}"
        assert button.inner_text() == "Remove", f"botão: {button.inner_text()}"

    button.click()
    wait_for_render(inventory.page)
    with bug_check(RemoveFromCartFailedError, f"'{product}' não saiu do carrinho"):
        assert badge.all_inner_texts() == [], f"contador: {badge.all_inner_texts()}"
        assert button.inner_text() == "Add to cart", f"botão: {button.inner_text()}"


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
