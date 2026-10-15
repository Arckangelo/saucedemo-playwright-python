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
        self.close_menu_button = page.get_by_role("button", name="Close Menu")
        self.all_items_link = page.get_by_test_id("inventory-sidebar-link")
        self.about_link = page.get_by_test_id("about-sidebar-link")
        self.logout_link = page.get_by_test_id("logout-sidebar-link")
        self.reset_app_state_link = page.get_by_test_id("reset-sidebar-link")
        # O menu fechado e "assentado" recebe o atributo hidden.
        self._settled_closed_menu = page.locator(".bm-menu-wrap[hidden]")

    def open_menu(self):
        # O componente do menu (react-burger-menu) agenda um timer de 500 ms, ao
        # carregar a página e ao fechar o menu, que esconde o menu se ele estiver
        # fechado. Um clique antes desse timer, numa máquina lenta, deixa o menu
        # "aberto" mas invisível (condição de corrida do site, reproduzida com a
        # CPU 30x mais lenta). Esperar o atributo hidden aparecer é o sinal
        # concreto de que o timer já rodou e o clique é seguro.
        self._settled_closed_menu.wait_for(state="attached")
        self.menu_button.click()

    def _click_menu_item(self, link):
        self.open_menu()
        # O menu abre com animação. Não precisamos de sleep: antes de clicar,
        # o Playwright espera o elemento estar visível, estável (sem animar),
        # habilitado e recebendo eventos — as "actionability checks".
        link.click()

    def logout(self):
        self._click_menu_item(self.logout_link)

    def go_to_all_items(self):
        self._click_menu_item(self.all_items_link)

    def reset_app_state(self):
        """Esvazia o carrinho pelo menu e fecha o menu, como um usuário faria."""
        self._click_menu_item(self.reset_app_state_link)
        self.close_menu_button.click()

    def get_about_url(self) -> str:
        # Só lemos o destino do link: seguir para o site da Sauce Labs testaria
        # um sistema de terceiros, fora do escopo desta suíte.
        self.open_menu()
        return self.about_link.get_attribute("href") or ""
