"""Leitura das linhas de itens, comum ao carrinho e ao resumo do checkout.

As duas telas usam a mesma marcação em cada linha (inventory-item com nome,
preço e item-quantity), então a leitura fica num lugar só.
"""

from dataclasses import dataclass
from decimal import Decimal

from playwright.sync_api import Locator

from pages.base_page import parse_money


@dataclass(frozen=True)
class CartRow:
    name: str
    price: Decimal
    quantity: int


def read_rows(items: Locator) -> list[CartRow]:
    """Lê cada linha por completo, na ordem da tela.

    Não espera: lê o que já está renderizado. Antes de chamar, sincronize com
    expect(items).to_have_count(n).
    """
    return [
        CartRow(
            name=item.get_by_test_id("inventory-item-name").inner_text(),
            price=parse_money(item.get_by_test_id("inventory-item-price").inner_text()),
            quantity=int(item.get_by_test_id("item-quantity").inner_text()),
        )
        for item in items.all()
    ]
