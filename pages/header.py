from playwright.sync_api import Page


class Header:
    """Componente de cabeçalho, presente em todas as páginas logadas.

    Em vez de repetir os seletores do carrinho/menu em cada Page Object,
    as páginas *contêm* um Header (composição). É o padrão "Page Component".
    """

    def __init__(self, page: Page):
        self.page = page
        self.title = page.get_by_test_id("title")
        self.cart_link = page.get_by_test_id("shopping-cart-link")
        self.cart_badge = page.get_by_test_id("shopping-cart-badge")
        # Seletor por papel acessível + nome: é como um usuário (ou leitor de tela)
        # enxerga o botão. Equivale ao cy.findByRole da Testing Library.
        self.menu_button = page.get_by_role("button", name="Open Menu")
        self.logout_link = page.get_by_test_id("logout-sidebar-link")

    def logout(self):
        self.menu_button.click()
        # O menu abre com animação. Não precisamos de sleep: antes de clicar,
        # o Playwright espera o elemento estar visível, estável (sem animar),
        # habilitado e recebendo eventos — as "actionability checks".
        self.logout_link.click()
