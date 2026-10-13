from decimal import Decimal

from playwright.sync_api import Locator, Page

from pages.base_page import BasePage, parse_money
from pages.cart_page import CartPage
from pages.header import Header


class InventoryPage(BasePage):
    PATH = "/inventory.html"

    def __init__(self, page: Page):
        super().__init__(page)
        self.header = Header(page)
        self.items = page.get_by_test_id("inventory-item")
        self.item_names = page.get_by_test_id("inventory-item-name")
        self.item_prices = page.get_by_test_id("inventory-item-price")
        self.item_images = page.locator("img.inventory_item_img")
        self.sort_select = page.get_by_test_id("product-sort-container")

    def item(self, product_name: str) -> Locator:
        """Card de UM produto, encontrado pelo nome exato.

        Locators podem ser encadeados e filtrados. Aqui: "o inventory-item que
        contém um inventory-item-name com este texto exato". No Cypress seria
        algo como cy.contains('[data-test=inventory-item]', nome).within(...).
        """
        return self.items.filter(
            has=self.page.get_by_test_id("inventory-item-name").get_by_text(
                product_name, exact=True
            )
        )

    def item_button(self, product_name: str) -> Locator:
        # Busca o botão DENTRO do card do produto (escopo encadeado).
        # Não usamos get_by_role("button") aqui porque os links da imagem e do
        # título também têm role="button" no saucedemo: o locator acharia 3
        # elementos e o Playwright falharia com "strict mode violation" — ele
        # se recusa a agir quando um locator é ambíguo. Por isso, a tag <button>.
        return self.item(product_name).locator("button")

    def add_to_cart(self, product_name: str):
        self.item(product_name).get_by_role("button", name="Add to cart").click()

    def remove_from_cart(self, product_name: str):
        self.item(product_name).get_by_role("button", name="Remove").click()

    def sort_by(self, option_value: str):
        # Valores do <select>: "az", "za", "lohi", "hilo" (≈ cy.select()).
        self.sort_select.select_option(option_value)

    # --- Leitura de dados ---------------------------------------------------
    # ATENÇÃO: all_inner_texts() NÃO tem auto-wait — ele lê o que estiver na
    # tela naquele instante (pode ser uma lista vazia). Por isso, nos testes,
    # sempre garantimos antes com um expect(...) que a lista já foi renderizada.

    def get_item_names(self) -> list[str]:
        return self.item_names.all_inner_texts()

    def get_item_prices(self) -> list[Decimal]:
        return [parse_money(text) for text in self.item_prices.all_inner_texts()]

    def get_image_sources(self) -> list[str]:
        return [img.get_attribute("src") for img in self.item_images.all()]

    # --- Navegação ----------------------------------------------------------
    # Métodos que levam a outra página devolvem o Page Object da próxima tela.
    # Assim o teste "lê" como o fluxo do usuário: inventory.go_to_cart().checkout()

    def go_to_cart(self) -> CartPage:
        self.header.cart_link.click()
        return CartPage(self.page)
