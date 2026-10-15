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
import time
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


# O cookie de sessão do saucedemo expira 10 minutos após o login. Renovamos com
# folga para um teste não receber um cookie que vence no meio da execução.
COOKIE_REFRESH_MARGIN_S = 120


def _expiring_soon(cookies: list) -> bool:
    deadline = time.time() + COOKIE_REFRESH_MARGIN_S
    # expires = -1 significa cookie de sessão do navegador (sem data de validade).
    return any(0 < cookie.get("expires", -1) < deadline for cookie in cookies)


@pytest.fixture(scope="session")
def user_cookies(browser: Browser, browser_context_args: dict) -> Callable[[str], list]:
    """Faz login pela interface e guarda os cookies, reaproveitando-os por usuário.

    É o equivalente ao cy.session() do Cypress. O saucedemo guarda a sessão
    só em um cookie (`session-username`), então basta reaproveitá-lo.
    Como a fixture tem scope="session", ela não pode usar a fixture `page`
    (que é por teste), por isso criamos um contexto próprio e o fechamos.
    `browser_context_args` são as mesmas opções (base_url, --device) que o
    pytest-playwright usa no contexto de cada teste.

    Devolve uma função (padrão "factory as fixture"): o teste pede os cookies
    do usuário de que precisa. Cada usuário loga uma vez, e de novo só quando
    o cookie está para expirar.
    """
    cache: dict[str, list] = {}

    def get(username: str) -> list:
        if username not in cache or _expiring_soon(cache[username]):
            context = browser.new_context(**browser_context_args)
            try:
                page = context.new_page()
                LoginPage(page).open().login(username, PASSWORD)
                expect(page).to_have_url(re.compile(r"/inventory\.html$"), timeout=SLOW_RENDER_TIMEOUT)
                cache[username] = context.cookies()
            finally:
                context.close()
        return cache[username]

    return get


@pytest.fixture
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
def oracle_inventory(browser: Browser, browser_context_args: dict, standard_user_cookies: list):
    """Inventário do standard_user em um contexto SEPARADO, usado como oráculo.

    Testes de outros perfis comparam o que veem com o que o standard_user vê,
    em vez de fixar preços, imagens ou posições no código. O contexto é
    próprio para não misturar cookies com o usuário sob teste, mas usa as
    mesmas opções (viewport, --device) do contexto do teste, senão o layout
    dos dois não seria comparável.
    """
    context = browser.new_context(**browser_context_args)
    try:
        yield _open_inventory(context.new_page(), context, standard_user_cookies)
    finally:
        context.close()


@dataclass
class BrowserErrors:
    """Erros observados na página durante o teste."""

    page_errors: list[str] = field(default_factory=list)
    console_errors: list[str] = field(default_factory=list)
    failed_responses: list[str] = field(default_factory=list)


@pytest.fixture(autouse=True)
def browser_errors(page: Page) -> BrowserErrors:
    """Registra exceções JavaScript, erros de console e respostas HTTP 4xx/5xx.

    page.on() inscreve uma função que o Playwright chama a cada evento
    (≈ cy.on('uncaught:exception') e cy.intercept() juntos). Com autouse, os
    ouvintes são registrados antes de qualquer fixture que navegue, então
    nada da primeira carga da página se perde, seja qual for a ordem dos
    parâmetros do teste. Basta pedir `browser_errors` para ler os erros.
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