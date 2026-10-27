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
import json
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from urllib.parse import urlparse

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, Response, expect
from pytest_html import extras

from data.constants import PASSWORD, PRODUCT_PRICES, SLOW_RENDER_TIMEOUT, Users
from pages import InventoryPage, LoginPage


SITE_CHECK_TIMEOUT_S = 15


def _site_unavailable_reason(base_url: str) -> str | None:
    """Motivo pelo qual o site não está utilizável, ou None se estiver."""
    request = urllib.request.Request(base_url, headers={"User-Agent": "saucedemo-e2e-healthcheck"})
    try:
        with urllib.request.urlopen(request, timeout=SITE_CHECK_TIMEOUT_S) as response:
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        return f"respondeu HTTP {error.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return f"não respondeu ({getattr(error, 'reason', error)})"
    # Uma página de erro ou de desafio (ex.: Cloudflare) também responde 200.
    if "Swag Labs" not in body:
        return "respondeu, mas não com a página do Swag Labs"
    return None


def pytest_addoption(parser):
    parser.addoption(
        "--base-user",
        default=Users.STANDARD,
        choices=[Users.STANDARD, Users.PROBLEM, Users.ERROR, Users.VISUAL, Users.PERFORMANCE_GLITCH],
        help=(
            "Usuário dos testes do standard_user (fixtures inventory_page e standard_session). "
            "Trocar por um perfil com defeitos é uma análise de mutação: um teste que continua "
            "passando numa funcionalidade que o perfil quebra tem asserção fraca."
        ),
    )


def pytest_report_header(config):
    if config.getoption("base_user") != Users.STANDARD:
        return f"ANÁLISE DE MUTAÇÃO: testes do standard_user rodando como {config.getoption('base_user')}"


def pytest_sessionstart(session):
    """Encerra a execução logo no início se o saucedemo.com estiver fora do ar.

    Sem isso, uma queda do site vira dezenas de falhas de teste que parecem
    bugs. Não é um retry: a checagem roda uma vez e, se falhar, a execução para
    com uma mensagem clara. Com pytest-xdist, roda só no processo principal.
    """
    config = session.config
    if hasattr(config, "workerinput") or config.option.collectonly:
        return
    base_url = config.getoption("base_url") or config.getini("base_url")
    reason = _site_unavailable_reason(base_url)
    if reason:
        pytest.exit(
            f"SITE INDISPONÍVEL: {base_url} {reason}. Nenhum teste foi executado; "
            "tente novamente quando o site voltar.",
            returncode=pytest.ExitCode.INTERRUPTED,
        )


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


@pytest.fixture(scope="session")
def base_user(pytestconfig) -> str:
    """Usuário dos testes do standard_user: --base-user (padrão: standard_user)."""
    return pytestconfig.getoption("base_user")


@pytest.fixture
def standard_user_cookies(user_cookies, base_user: str) -> list:
    return user_cookies(base_user)


@pytest.fixture
def session_as(context: BrowserContext, user_cookies) -> Callable[[str], None]:
    """Autentica o contexto com o usuário pedido, sem abrir nenhuma página: session_as(Users.PROBLEM).

    Use junto com cart_with() e abra direto a tela do teste (carrinho, checkout),
    em vez de passar pelo inventário.
    """
    return lambda username: context.add_cookies(user_cookies(username))


@pytest.fixture
def standard_session(session_as, base_user: str) -> None:
    """Contexto autenticado como standard_user (ou o --base-user), sem abrir nenhuma página."""
    session_as(base_user)


# Roda antes dos scripts do site em toda carga de página do contexto, inclusive
# em reload. Por isso grava uma única vez por aba (marca no sessionStorage):
# sem isso, um item removido "voltaria" a cada reload. E só na origem do site,
# para não escrever no localStorage de about:blank ou de outros domínios.
_CART_SEED_SCRIPT = """
if (location.origin === %(origin)s && !sessionStorage.getItem('cart-seeded')) {
    localStorage.setItem('cart-contents', JSON.stringify(%(ids)s));
    sessionStorage.setItem('cart-seeded', '1');
}
"""


@pytest.fixture
def cart_with(context: BrowserContext, base_url: str) -> Callable[..., None]:
    """Monta o carrinho direto no localStorage, sem passar pela tela: cart_with(4, 5).

    É o equivalente do cy.request do Cypress (o saucedemo não tem API: o
    carrinho mora no localStorage, como lista de ids). Deve ser chamada antes
    de a página do teste carregar. Só aceita ids do catálogo, sem repetição:
    um carrinho que a tela não consegue produzir (RN-11) testaria outra coisa.
    """
    origin = "{0.scheme}://{0.netloc}".format(urlparse(base_url))
    seeded = False

    def seed(*product_ids: int):
        nonlocal seeded
        if seeded:
            raise RuntimeError("cart_with() só pode ser chamada uma vez por teste")
        unknown = set(product_ids) - PRODUCT_PRICES.keys()
        if unknown or len(set(product_ids)) != len(product_ids):
            raise ValueError(f"Ids fora do catálogo ou repetidos: {list(product_ids)}")
        context.add_init_script(
            _CART_SEED_SCRIPT % {"origin": json.dumps(origin), "ids": json.dumps(list(product_ids))}
        )
        seeded = True

    return seed


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
def oracle_inventory(browser: Browser, browser_context_args: dict, user_cookies):
    """Inventário do standard_user em um contexto SEPARADO, usado como oráculo.

    Testes de outros perfis comparam o que veem com o que o standard_user vê,
    em vez de fixar preços, imagens ou posições no código. O contexto é
    próprio para não misturar cookies com o usuário sob teste, mas usa as
    mesmas opções (viewport, --device) do contexto do teste, senão o layout
    dos dois não seria comparável. O oráculo é sempre o standard_user, mesmo
    com --base-user: comparar um mutante com outro não provaria nada.
    """
    context = browser.new_context(**browser_context_args)
    try:
        yield _open_inventory(context.new_page(), context, user_cookies(Users.STANDARD))
    finally:
        context.close()


@dataclass
class BrowserErrors:
    """Erros observados na página durante o teste."""

    page_errors: list[str] = field(default_factory=list)
    console_errors: list[str] = field(default_factory=list)
    failed_responses: list[str] = field(default_factory=list)


@pytest.fixture(autouse=True)
def browser_errors(page: Page, request: pytest.FixtureRequest) -> Iterator[BrowserErrors]:
    """Registra exceções JavaScript, erros de console e respostas HTTP 4xx/5xx.

    page.on() inscreve uma função que o Playwright chama a cada evento
    (≈ cy.on('uncaught:exception') e cy.intercept() juntos). Com autouse, os
    ouvintes são registrados antes de qualquer fixture que navegue, então
    nada da primeira carga da página se perde, seja qual for a ordem dos
    parâmetros do teste. Basta pedir `browser_errors` para ler os erros.

    No teardown, qualquer exceção JavaScript não tratada falha o teste (como
    o Cypress faz por padrão), a menos que ele tenha o marker allow_js_errors,
    sempre com um comentário dizendo qual bug gera o erro. Erros de console e
    respostas HTTP de terceiros não entram nessa regra (ver test_console_e_rede.py).
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
    yield errors

    if errors.page_errors and not request.node.get_closest_marker("allow_js_errors"):
        pytest.fail(
            "Erros JavaScript não tratados na página:\n" + "\n".join(errors.page_errors)
            + "\nSe forem de um bug conhecido, marque o teste com allow_js_errors e cite o bug.",
            pytrace=False,
        )


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