import re
from decimal import Decimal

from playwright.sync_api import Locator, Page

from pages.base_page import ADD_TO_CART_BUTTON, CART_BUTTON, REMOVE_BUTTON, BasePage, parse_money
from pages.cart_page import CartPage
from pages.header import Header
from pages.product_detail_page import ProductDetailPage


class InventoryPage(BasePage):
    PATH = "/inventory.html"

    def __init__(self, page: Page):
        super().__init__(page)
        self.header = Header(page)
        self.items = page.get_by_test_id("inventory-item")
        self.item_names = page.get_by_test_id("inventory-item-name")
        self.item_prices = page.get_by_test_id("inventory-item-price")
        self.item_images = page.get_by_test_id(re.compile(r"^inventory-item-.+-img$"))
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
        # O botão do card, esteja ele em "Add to cart" ou em "Remove": o
        # data-test muda de add-to-cart-<produto> para remove-<produto>, então
        # o prefixo localiza os dois estados sem depender do texto exibido.
        return self.item(product_name).get_by_test_id(CART_BUTTON)

    def add_to_cart(self, product_name: str):
        self.item(product_name).get_by_test_id(ADD_TO_CART_BUTTON).click()

    def remove_from_cart(self, product_name: str):
        self.item(product_name).get_by_test_id(REMOVE_BUTTON).click()

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
        # get_attribute devolve None se o atributo não existir; "or ''" evita
        # um TypeError mais adiante e mantém o retorno sempre como list[str].
        return [img.get_attribute("src") or "" for img in self.item_images.all()]

    # Indexar pelo nome deixa a comparação independente da ordem na tela.
    def get_prices_by_name(self) -> dict[str, Decimal]:
        return dict(zip(self.get_item_names(), self.get_item_prices()))

    def get_images_by_name(self) -> dict[str, str]:
        return dict(zip(self.get_item_names(), self.get_image_sources()))

    # --- Navegação ----------------------------------------------------------
    # Métodos que levam a outra página devolvem o Page Object da próxima tela.
    # Assim o teste "lê" como o fluxo do usuário: inventory.go_to_cart().checkout()

    def go_to_cart(self) -> CartPage:
        self.header.cart_link.click()
        return CartPage(self.page)

    def open_product(self, product_name: str) -> ProductDetailPage:
        self.item(product_name).get_by_test_id("inventory-item-name").click()
        return ProductDetailPage(self.page)