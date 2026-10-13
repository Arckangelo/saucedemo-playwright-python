"""Fixtures compartilhadas por todos os testes.

Cypress x pytest — como pensar em fixtures:
- No Cypress, preparação fica em beforeEach() e o teste usa o que foi
  preparado "por fora" (cy.get, aliases, this.*).
- No pytest, cada teste DECLARA do que precisa nos parâmetros da função.
  `def test_x(inventory_page):` faz o pytest procurar uma fixture chamada
  inventory_page, executá-la e injetar o resultado. Nada roda se nenhum
  teste pedir.
- O código ANTES do `yield` é o setup (≈ beforeEach); o código DEPOIS é o
  teardown (≈ afterEach). Uma fixture que só usa `return` não tem teardown.
- `scope` controla quanto a fixture vive: "function" (padrão, uma vez por
  teste), "module", "session" (uma vez por execução — ≈ before()).

O pytest-playwright já fornece prontas as fixtures `playwright`, `browser`
(scope session), `context` e `page` (scope function: cada teste recebe um
contexto novo — cookies e localStorage zerados, como o testIsolation do
Cypress 12+).
"""

import base64
import re

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, expect
from pytest_html import extras

from data.constants import PASSWORD, Users
from pages import InventoryPage, LoginPage


@pytest.fixture(scope="session", autouse=True)
def configure_test_id_attribute(playwright):
    """Faz page.get_by_test_id("x") procurar [data-test="x"].

    O padrão do Playwright é o atributo data-testid, mas o saucedemo usa
    data-test. `autouse=True` aplica a fixture a todos os testes sem que
    eles precisem pedi-la.
    """
    playwright.selectors.set_test_id_attribute("data-test")


@pytest.fixture
def login_page(page: Page) -> LoginPage:
    """Página de login já aberta."""
    return LoginPage(page).open()


@pytest.fixture(scope="session")
def standard_user_cookies(browser: Browser, base_url: str) -> list:
    """Faz login pela interface UMA única vez por execução e guarda os cookies.

    É o equivalente ao cy.session() do Cypress. O saucedemo guarda a sessão
    só em um cookie (`session-username`), então basta reaproveitá-lo.
    Como a fixture tem scope="session", ela não pode usar a fixture `page`
    (que é por teste), por isso criamos um contexto próprio e o fechamos.
    """
    context = browser.new_context(base_url=base_url)
    page = context.new_page()
    login = LoginPage(page).open()
    login.login(Users.STANDARD, PASSWORD)
    expect(page).to_have_url(re.compile(r"/inventory\.html$"))
    cookies = context.cookies()
    context.close()
    return cookies


@pytest.fixture
def inventory_page(
    page: Page, context: BrowserContext, standard_user_cookies: list
) -> InventoryPage:
    """Inventário aberto com o standard_user já autenticado.

    Injetamos o cookie de sessão no contexto NOVO deste teste: o login fica
    reaproveitado, mas o carrinho (localStorage) começa vazio — cada teste
    continua independente dos outros.
    """
    context.add_cookies(standard_user_cookies)
    inventory = InventoryPage(page).open()
    expect(inventory.header.title).to_have_text("Products")
    return inventory


# --- Relatório ------------------------------------------------------------

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Anexa um screenshot ao relatório HTML quando um teste falha.

    Hooks são "ganchos" que o pytest chama em momentos do ciclo de vida.
    Este roda ao montar o resultado de cada fase; na fase "call" (o corpo
    do teste) a página ainda está aberta, então dá para fotografá-la.
    """
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" or not report.failed:
        return
    page = item.funcargs.get("page")
    if page is None or page.is_closed():
        return
    try:
        png = page.screenshot(full_page=True)
    except Exception as error:  # ex.: navegador travou junto com o teste
        # Um erro DENTRO do hook quebraria o relatório inteiro e esconderia a
        # falha original. O screenshot é um "extra": se não der, só avisamos.
        report.sections.append(("screenshot", f"Não foi possível capturar: {error}"))
        return
    screenshot = base64.b64encode(png).decode()
    report.extras = [*getattr(report, "extras", []), extras.png(screenshot, "Screenshot")]