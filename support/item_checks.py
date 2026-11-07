"""Validação de linhas do carrinho e do resumo contra o catálogo do site.

Equivalente ao validarItem() do Cypress: o esperado vem do catálogo lido na
hora (fixture catalog_prices), nunca da própria tela que está sendo testada.
"""

from pages.cart_rows import CartRow
from support.catalog import Catalog


def assert_item(row: CartRow, catalog: Catalog, product_id: int, qty: int = 1):
    """Confere nome, preço e quantidade de uma linha contra o catálogo."""
    expected = catalog[product_id]
    assert row.name == expected["name"], f"nome da linha do id {product_id}: {row}"
    assert row.price == expected["price"], f"preço de '{row.name}': {row.price}, esperado {expected['price']}"
    assert row.quantity == qty, f"quantidade de '{row.name}': {row.quantity}, esperada {qty}"
