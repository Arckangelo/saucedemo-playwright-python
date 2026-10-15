from playwright.sync_api import Page

from pages.base_page import BasePage
from pages.header import Header


class ProductDetailPage(BasePage):
    """Detalhe de um produto: /inventory-item.html?id=N."""

    PATH = "/inventory-item.html"

    def __init__(self, page: Page):
        super().__init__(page)
        self.header = Header(page)
        # Na tela de detalhe existe um único inventory-item, então os mesmos
        # data-test do inventário identificam o produto exibido.
        self.name = page.get_by_test_id("inventory-item-name")
        self.add_to_cart_button = page.get_by_test_id("add-to-cart")
        self.back_button = page.get_by_test_id("back-to-products")

    def open_product(self, product_id: int | str) -> "ProductDetailPage":
        self.page.goto(f"{self.PATH}?id={product_id}")
        return self

    def get_product_id(self) -> str:
        return self.page.url.split("id=")[-1]
