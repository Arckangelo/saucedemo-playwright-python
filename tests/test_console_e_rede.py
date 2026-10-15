"""Saúde técnica da página: erros JavaScript, de console e respostas HTTP."""

from urllib.parse import urlparse

import pytest
from playwright.sync_api import Page, expect

from data.constants import Messages, Products
from pages import InventoryPage


class InternalRouteStatusError(AssertionError):
    """Uma rota interna respondeu com status HTTP de erro."""


class TelemetryError(AssertionError):
    """A telemetria do site gerou respostas HTTP de erro."""


def test_compra_completa_sem_erros_de_javascript(browser_errors, inventory_page: InventoryPage):
    inventory_page.add_to_cart(Products.BACKPACK)
    information = inventory_page.go_to_cart().checkout()
    information.fill_information("Ana", "Souza", "72980-000")
    complete = information.continue_to_overview().finish()
    expect(complete.complete_header).to_have_text(Messages.ORDER_COMPLETE)

    assert browser_errors.page_errors == []


@pytest.mark.regression
@pytest.mark.xfail(
    strict=True,
    raises=InternalRouteStatusError,
    reason="BUG-005: rotas internas respondem HTTP 404 e dependem do JavaScript para abrir",
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
    reason="BUG-006: a telemetria (Backtrace) usa credenciais de exemplo e recebe HTTP 401",
)
def test_telemetria_nao_gera_erros_http(browser_errors, inventory_page: InventoryPage):
    # A telemetria é enviada em segundo plano; esperar a rede ficar ociosa
    # garante que as respostas já chegaram antes de conferir.
    inventory_page.page.wait_for_load_state("networkidle")

    telemetry = [r for r in browser_errors.failed_responses if "backtrace.io" in urlparse(r.split(" ", 1)[1]).netloc]
    if telemetry:
        raise TelemetryError(f"Respostas de erro da telemetria: {telemetry}")
