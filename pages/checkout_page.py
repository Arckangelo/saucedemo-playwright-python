"""O checkout do saucedemo tem 3 telas, então são 3 Page Objects.

Ficam no mesmo módulo porque formam um único fluxo, mas cada tela continua
com a sua própria classe, seus seletores e seus métodos.
"""

from decimal import Decimal

from playwright.sync_api import Page

from pages.base_page import BasePage, parse_money
from pages.header import Header


class CheckoutInformationPage(BasePage):
    """Passo 1: dados do comprador."""

    PATH = "/checkout-step-one.html"

    def __init__(self, page: Page):
        super().__init__(page)
        self.header = Header(page)
        self.first_name_input = page.get_by_test_id("firstName")
        self.last_name_input = page.get_by_test_id("lastName")
        self.postal_code_input = page.get_by_test_id("postalCode")
        self.continue_button = page.get_by_test_id("continue")
        self.error_message = page.get_by_test_id("error")

    def fill_information(self, first_name: str, last_name: str, postal_code: str):
        self.first_name_input.fill(first_name)
        self.last_name_input.fill(last_name)
        self.postal_code_input.fill(postal_code)

    def continue_to_overview(self) -> "CheckoutOverviewPage":
        self.continue_button.click()
        return CheckoutOverviewPage(self.page)


class CheckoutOverviewPage(BasePage):
    """Passo 2: resumo do pedido com subtotal, imposto e total."""

    PATH = "/checkout-step-two.html"

    def __init__(self, page: Page):
        super().__init__(page)
        self.header = Header(page)
        self.item_names = page.get_by_test_id("inventory-item-name")
        self.item_prices = page.get_by_test_id("inventory-item-price")
        self.subtotal_label = page.get_by_test_id("subtotal-label")
        self.tax_label = page.get_by_test_id("tax-label")
        self.total_label = page.get_by_test_id("total-label")
        self.finish_button = page.get_by_test_id("finish")

    def get_item_prices(self) -> list[Decimal]:
        return [parse_money(text) for text in self.item_prices.all_inner_texts()]

    def get_subtotal(self) -> Decimal:
        # inner_text() tem auto-wait: espera o elemento existir antes de ler.
        return parse_money(self.subtotal_label.inner_text())

    def get_tax(self) -> Decimal:
        return parse_money(self.tax_label.inner_text())

    def get_total(self) -> Decimal:
        return parse_money(self.total_label.inner_text())

    def finish(self) -> "CheckoutCompletePage":
        self.finish_button.click()
        return CheckoutCompletePage(self.page)


class CheckoutCompletePage(BasePage):
    """Passo 3: confirmação do pedido."""

    PATH = "/checkout-complete.html"

    def __init__(self, page: Page):
        super().__init__(page)
        self.header = Header(page)
        self.complete_header = page.get_by_test_id("complete-header")
        self.back_home_button = page.get_by_test_id("back-to-products")
