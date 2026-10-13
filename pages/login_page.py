from playwright.sync_api import Page

from pages.base_page import BasePage


class LoginPage(BasePage):
    PATH = "/"

    def __init__(self, page: Page):
        super().__init__(page)
        # Criar um locator NÃO busca nada na tela ainda. Ele é uma "receita"
        # de como encontrar o elemento; a busca acontece (e é refeita) só
        # quando uma ação ou asserção é executada. Por isso dá para declarar
        # todos os locators no __init__, antes de a página sequer carregar.
        self.username_input = page.get_by_test_id("username")
        self.password_input = page.get_by_test_id("password")
        self.login_button = page.get_by_test_id("login-button")
        self.error_message = page.get_by_test_id("error")

    def login(self, username: str, password: str):
        # fill() limpa o campo e digita o valor de uma vez (≈ cy.clear().type()).
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.login_button.click()
