import re
from decimal import Decimal

from playwright.sync_api import Page


# data-test dos botões de carrinho: "add-to-cart-<produto>" vira "remove-<produto>"
# depois do clique. Os prefixos localizam o botão sem depender do texto exibido.
ADD_TO_CART_BUTTON = re.compile(r"^add-to-cart-")
REMOVE_BUTTON = re.compile(r"^remove-")
CART_BUTTON = re.compile(r"^(add-to-cart|remove)-")


def parse_money(text: str) -> Decimal:
    """Extrai o valor monetário de um texto: 'Item total: $39.98' -> Decimal('39.98').

    Usamos Decimal (e não float) porque float não representa centavos com
    exatidão: em Python, 0.1 + 0.2 == 0.30000000000000004.
    """
    match = re.search(r"\$(\d+(?:\.\d+)?)", text)
    if not match:
        raise ValueError(f"Nenhum valor em dólar encontrado em: {text!r}")
    return Decimal(match.group(1))


class BasePage:
    """Classe base de todas as páginas.

    Guarda a instância de `Page` do Playwright e sabe abrir a própria URL.
    `PATH` é relativo: o domínio vem do `base_url` configurado no pytest.ini,
    igual ao `baseUrl` do cypress.config.js.
    """

    PATH = "/"

    def __init__(self, page: Page):
        self.page = page

    def open(self):
        self.page.goto(self.PATH)
        return self
