from playwright.sync_api import Page

from pages.base_page import BasePage
from pages.checkout_page import CheckoutInformationPage
from pages.header import Header


class CartPage(BasePage):
    PATH = "/cart.html"

    def __init__(self, page: Page):
        super().__init__(page)
        self.header = Header(page)
        self.items = page.get_by_test_id("inventory-item")
        self.item_names = page.get_by_test_id("inventory-item-name")
        self.item_prices = page.get_by_test_id("inventory-item-price")
        self.checkout_button = page.get_by_test_id("checkout")
        self.continue_shopping_button = page.get_by_test_id("continue-shopping")

    def checkout(self) -> CheckoutInformationPage:
        self.checkout_button.click()
        return CheckoutInformationPage(self.page)
