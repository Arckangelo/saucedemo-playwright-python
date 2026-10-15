"""Massa de dados dos testes.

Centralizar usuários, produtos e mensagens aqui evita "strings mágicas"
espalhadas pelos testes: se o site mudar um texto, ajustamos em um lugar só.
(No Cypress, o equivalente seria um arquivo em cypress/fixtures/*.json.)
"""

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


# Id de cada produto na URL do detalhe (/inventory-item.html?id=N) e no
# localStorage do carrinho. Ids fora desta lista não existem no catálogo.
PRODUCT_IDS = {
    Products.BIKE_LIGHT: 0,
    Products.BOLT_TSHIRT: 1,
    Products.ONESIE: 2,
    Products.RED_TSHIRT: 3,
    Products.BACKPACK: 4,
    Products.FLEECE_JACKET: 5,
}

ABOUT_URL = "https://saucelabs.com/"


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
