from playwright.sync_api import Page

from pages.base_page import BasePage
from pages.cart_rows import CartRow, read_rows
from pages.checkout_page import CheckoutInformationPage
from pages.header import Header


class CartPage(BasePage):
    PATH = "/cart.html"

    def __init__(self, page: Page):
        super().__init__(page)
        self.header = Header(page)
        self.items = page.get_by_test_id("inventory-item")
        self.item_names = page.get_by_test_id("inventory-item-name")
        self.checkout_button = page.get_by_test_id("checkout")
        self.continue_shopping_button = page.get_by_test_id("continue-shopping")

    def get_rows(self) -> list[CartRow]:
        return read_rows(self.items)

    def remove(self, product_name: str):
        item = self.items.filter(
            has=self.page.get_by_test_id("inventory-item-name").get_by_text(product_name, exact=True)
        )
        item.get_by_role("button", name="Remove").click()

    def checkout(self) -> CheckoutInformationPage:
        self.checkout_button.click()
        return CheckoutInformationPage(self.page)
