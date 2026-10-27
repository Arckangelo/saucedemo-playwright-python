"""Massa de dados dos testes.

Centralizar usuários, produtos e mensagens aqui evita "strings mágicas"
espalhadas pelos testes: se o site mudar um texto, ajustamos em um lugar só.
(No Cypress, o equivalente seria um arquivo em cypress/fixtures/*.json.)
"""

from decimal import Decimal

PASSWORD = "secret_sauce"

# Quantidade de produtos do catálogo (evita o "número mágico" 6 espalhado nos testes).
TOTAL_PRODUCTS = 6

# O performance_glitch_user atrasa ~5 s toda renderização do inventário.
SLOW_RENDER_TIMEOUT = 15_000


class Users:
    STANDARD = "standard_user"
    LOCKED_OUT = "locked_out_user"
    PROBLEM = "problem_user"
    PERFORMANCE_GLITCH = "performance_glitch_user"
    ERROR = "error_user"
    VISUAL = "visual_user"


class Products:
    BACKPACK = "Sauce Labs Backpack"
    BIKE_LIGHT = "Sauce Labs Bike Light"
    BOLT_TSHIRT = "Sauce Labs Bolt T-Shirt"
    FLEECE_JACKET = "Sauce Labs Fleece Jacket"
    ONESIE = "Sauce Labs Onesie"
    RED_TSHIRT = "Test.allTheThings() T-Shirt (Red)"

    ALL = [BACKPACK, BIKE_LIGHT, BOLT_TSHIRT, FLEECE_JACKET, ONESIE, RED_TSHIRT]


# Tabela de referência do catálogo: id -> nome e preço. É a fonte de verdade
# dos testes, independente do que a tela mostrar (no Cypress, os preços vinham
# da API). Valores conferidos uma única vez no site, como standard_user, em
# 27/10/2026. Não gere esta tabela a partir da tela: o teste passaria a
# comparar a tela com ela mesma. Preço em Decimal, como no resto da suíte.
PRODUCT_PRICES = {
    0: {"name": Products.BIKE_LIGHT, "price": Decimal("9.99")},
    1: {"name": Products.BOLT_TSHIRT, "price": Decimal("15.99")},
    2: {"name": Products.ONESIE, "price": Decimal("7.99")},
    3: {"name": Products.RED_TSHIRT, "price": Decimal("15.99")},
    4: {"name": Products.BACKPACK, "price": Decimal("29.99")},
    5: {"name": Products.FLEECE_JACKET, "price": Decimal("49.99")},
}

# Id de cada produto na URL do detalhe (/inventory-item.html?id=N) e no
# localStorage do carrinho. Ids fora desta lista não existem no catálogo.
# Derivado da tabela acima, para a relação id <-> nome existir num lugar só.
PRODUCT_IDS = {product["name"]: product_id for product_id, product in PRODUCT_PRICES.items()}

ABOUT_URL = "https://saucelabs.com/"

# Dados válidos do passo 1 do checkout. As chaves são os parâmetros de
# fill_information(), então dá para usar fill_information(**CHECKOUT_INFO).
# (No Cypress, o equivalente seria o cypress/fixtures/apiData.json.)
CHECKOUT_INFO = {
    "first_name": "Ana",
    "last_name": "Souza",
    "postal_code": "72980-000",
}


class Messages:
    # Login
    LOCKED_OUT = "Epic sadface: Sorry, this user has been locked out."
    INVALID_CREDENTIALS = (
        "Epic sadface: Username and password do not match any user in this service"
    )
    USERNAME_REQUIRED = "Epic sadface: Username is required"
    PASSWORD_REQUIRED = "Epic sadface: Password is required"

    @staticmethod
    def not_logged_in(path: str) -> str:
        return f"Epic sadface: You can only access '{path}' when you are logged in."

    # Checkout
    FIRST_NAME_REQUIRED = "Error: First Name is required"
    LAST_NAME_REQUIRED = "Error: Last Name is required"
    POSTAL_CODE_REQUIRED = "Error: Postal Code is required"
    ORDER_COMPLETE = "Thank you for your order!"

    # Produto inexistente
    ITEM_NOT_FOUND = "ITEM NOT FOUND"


# Regra de negócio do site: imposto de 8% sobre o subtotal
# (confirmada no código-fonte oficial: saucelabs/sample-app-web, utils/orderCalculations.js).
TAX_RATE = "0.08"
