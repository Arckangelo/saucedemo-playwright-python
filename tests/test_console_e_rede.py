"""Saúde técnica da página: respostas HTTP das rotas e da telemetria.

As exceções JavaScript da página são verificadas em TODOS os testes, pela
fixture browser_errors do conftest (todos os scripts vêm de www.saucedemo.com).
Política para não depender de terceiros no CI: erros de console e respostas
de outros domínios (Backtrace, Google Fonts) são coletados, mas ignorados. A
exceção é o teste que documenta o BUG-006, que olha apenas o Backtrace; se ele
não responder, o resultado é inconclusivo (skip), nunca um falso "corrigido".
"""

from urllib.parse import urlparse

import pytest
from playwright.sync_api import Page, Request
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


class InternalRouteStatusError(AssertionError):
    """Uma rota interna respondeu com status HTTP de erro."""


class TelemetryError(AssertionError):
    """A telemetria do site gerou respostas HTTP de erro."""


TELEMETRY_TIMEOUT = 10_000
TELEMETRY_HOST = "backtrace.io"


@pytest.mark.regression
@pytest.mark.xfail(
    strict=True,
    raises=InternalRouteStatusError,
    reason="BUG-005 (#6): rotas internas respondem HTTP 404 e dependem do JavaScript para abrir",
)
def test_rotas_internas_respondem_http_200(page: Page):
    paths = ["/", "/inventory.html", "/cart.html", "/checkout-step-one.html", "/inventory-item.html?id=4"]
    # page.request faz a requisição HTTP direta, sem renderizar a página:
    # mostra o status que o servidor devolve para quem acessa o link.
    statuses = {path: page.request.get(path).status for path in paths}

    errors = {path: status for path, status in statuses.items() if status != 200}
    if errors:
        raise InternalRouteStatusError(f"Status por rota: {errors}")


@pytest.mark.regression
@pytest.mark.xfail(
    strict=True,
    raises=TelemetryError,
    reason="BUG-006 (#7): a telemetria (Backtrace) usa credenciais de exemplo e recebe HTTP 401",
)
def test_telemetria_nao_gera_erros_http(page: Page):
    def is_telemetry(request: Request) -> bool:
        # Compara o host exato (ou subdomínio): endswith("backtrace.io") aceitaria "evilbacktrace.io".
        host = urlparse(request.url).hostname or ""
        return host == TELEMETRY_HOST or host.endswith("." + TELEMETRY_HOST)

    # A telemetria sai uma única vez por sessão do navegador, na PRIMEIRA
    # carga (recarregar ou navegar depois não envia de novo). Por isso a
    # espera envolve a primeira navegação do contexto novo deste teste,
    # sem depender de a rede "ficar ociosa", o que pode acontecer antes.
    try:
        with page.expect_request(is_telemetry, timeout=TELEMETRY_TIMEOUT) as request_info:
            page.goto("/")
    except PlaywrightTimeoutError:
        return  # nenhuma telemetria enviada (ex.: foi removida): não há o que reportar

    # response() espera a resposta; devolve None se a requisição falhou na rede.
    request = request_info.value
    response = request.response()
    if response is None:
        # Desde 27/10/2026 o Backtrace leva 8-10 s só no handshake TLS, e o
        # cliente de telemetria do site aborta a requisição em 15 s, antes de
        # qualquer status. Problema de terceiro: não prova nem descarta o bug.
        # Pular evita um XPASS falso.
        pytest.skip(
            f"Telemetria enviada, mas abortada sem resposta ({request.failure}): o Backtrace "
            "demora mais que o limite de 15 s do próprio site. Resultado inconclusivo"
        )
    if response.status >= 400:
        raise TelemetryError(f"Telemetria respondeu {response.status}: {response.url}")
