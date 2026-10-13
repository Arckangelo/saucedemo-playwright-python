"""Massa de dados dos testes.

Centralizar usuários, produtos e mensagens aqui evita "strings mágicas"
espalhadas pelos testes: se o site mudar um texto, ajustamos em um lugar só.
(No Cypress, o equivalente seria um arquivo em cypress/fixtures/*.json.)
"""

PASSWORD = "secret_sauce"


class Users:
    STANDARD = "standard_user"
    LOCKED_OUT = "locked_out_user"
    PROBLEM = "problem_user"
    PERFORMANCE_GLITCH = "performance_glitch_user"


class Products:
    BACKPACK = "Sauce Labs Backpack"
    BIKE_LIGHT = "Sauce Labs Bike Light"
    BOLT_TSHIRT = "Sauce Labs Bolt T-Shirt"
    FLEECE_JACKET = "Sauce Labs Fleece Jacket"
    ONESIE = "Sauce Labs Onesie"


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


# Regra de negócio do site: imposto de 8% sobre o subtotal
# (confirmada no código-fonte oficial: saucelabs/sample-app-web, utils/orderCalculations.js).
TAX_RATE = "0.08"
