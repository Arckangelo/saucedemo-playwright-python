"""Validação de linhas do carrinho e do resumo contra a tabela de referência.

Equivalente ao validarItem() do Cypress: o esperado vem de PRODUCT_PRICES,
nunca da própria tela que está sendo testada.
"""

from data.constants import PRODUCT_PRICES
from pages.cart_rows import CartRow


def assert_item(row: CartRow, product_id: int, qty: int = 1):
    """Confere nome, preço e quantidade de uma linha."""
    expected = PRODUCT_PRICES[product_id]
    assert row.name == expected["name"], f"nome da linha do id {product_id}: {row}"
    assert row.price == expected["price"], f"preço de '{row.name}': {row.price}, esperado {expected['price']}"
    assert row.quantity == qty, f"quantidade de '{row.name}': {row.quantity}, esperada {qty}"
