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
from collections.abc import Callable
from dataclasses import dataclass, field

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, Response, expect
from pytest_html import extras

from data.constants import PASSWORD, SLOW_RENDER_TIMEOUT, Users
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
def user_cookies(browser: Browser, base_url: str) -> Callable[[str], list]:
    """Faz login pela interface UMA única vez por usuário e guarda os cookies.

    É o equivalente ao cy.session() do Cypress. O saucedemo guarda a sessão
    só em um cookie (`session-username`), então basta reaproveitá-lo.
    Como a fixture tem scope="session", ela não pode usar a fixture `page`
    (que é por teste), por isso criamos um contexto próprio e o fechamos.

    Devolve uma função (padrão "factory as fixture"): o teste pede os cookies
    do usuário de que precisa, e cada usuário loga no máximo uma vez.
    """
    cache: dict[str, list] = {}

    def get(username: str) -> list:
        if username not in cache:
            context = browser.new_context(base_url=base_url)
            page = context.new_page()
            LoginPage(page).open().login(username, PASSWORD)
            expect(page).to_have_url(re.compile(r"/inventory\.html$"), timeout=SLOW_RENDER_TIMEOUT)
            cache[username] = context.cookies()
            context.close()
        return cache[username]

    return get


@pytest.fixture(scope="session")
def standard_user_cookies(user_cookies) -> list:
    return user_cookies(Users.STANDARD)


def _open_inventory(page: Page, context: BrowserContext, cookies: list) -> InventoryPage:
    context.add_cookies(cookies)
    inventory = InventoryPage(page).open()
    expect(inventory.header.title).to_have_text("Products", timeout=SLOW_RENDER_TIMEOUT)
    return inventory


@pytest.fixture
def inventory_page(
    page: Page, context: BrowserContext, standard_user_cookies: list
) -> InventoryPage:
    """Inventário aberto com o standard_user já autenticado.

    Injetamos o cookie de sessão no contexto NOVO deste teste: o login fica
    reaproveitado, mas o carrinho (localStorage) começa vazio — cada teste
    continua independente dos outros.
    """
    return _open_inventory(page, context, standard_user_cookies)


@pytest.fixture
def login_as(page: Page, context: BrowserContext, user_cookies) -> Callable[[str], InventoryPage]:
    """Abre o inventário já autenticado com o usuário pedido: login_as(Users.PROBLEM)."""
    return lambda username: _open_inventory(page, context, user_cookies(username))


@pytest.fixture
def oracle_inventory(browser: Browser, base_url: str, standard_user_cookies: list):
    """Inventário do standard_user em um contexto SEPARADO, usado como oráculo.

    Testes de outros perfis comparam o que veem com o que o standard_user vê,
    em vez de fixar preços, imagens ou posições no código. O contexto é
    próprio para não misturar cookies com o usuário sob teste.
    """
    context = browser.new_context(base_url=base_url)
    inventory = _open_inventory(context.new_page(), context, standard_user_cookies)
    yield inventory
    context.close()


@dataclass
class BrowserErrors:
    """Erros observados na página durante o teste."""

    page_errors: list[str] = field(default_factory=list)
    console_errors: list[str] = field(default_factory=list)
    failed_responses: list[str] = field(default_factory=list)


@pytest.fixture
def browser_errors(page: Page) -> BrowserErrors:
    """Registra exceções JavaScript, erros de console e respostas HTTP 4xx/5xx.

    page.on() inscreve uma função que o Playwright chama a cada evento
    (≈ cy.on('uncaught:exception') e cy.intercept() juntos). Como a fixture
    usa a mesma `page` do teste, os eventos são capturados desde o início.
    """
    errors = BrowserErrors()

    def on_response(response: Response):
        if response.status >= 400:
            errors.failed_responses.append(f"{response.status} {response.url}")

    page.on("pageerror", lambda error: errors.page_errors.append(str(error)))
    page.on(
        "console",
        lambda message: message.type == "error" and errors.console_errors.append(message.text),
    )
    page.on("response", on_response)
    return errors


# --- Marcadores -------------------------------------------------------------

def pytest_collection_modifyitems(items):
    """Marca como `known_bug` todo xfail cujo motivo comece com "BUG-".

    Assim a convenção fica num lugar só: basta escrever o xfail com o ID do
    bug para o teste entrar em `pytest -m known_bug`.
    """
    for item in items:
        for mark in item.iter_markers("xfail"):
            if str(mark.kwargs.get("reason", "")).startswith("BUG-"):
                item.add_marker(pytest.mark.known_bug)
                break


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