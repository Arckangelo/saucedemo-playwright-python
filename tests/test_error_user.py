"""error_user: falhas funcionais que geram erros JavaScript.

Mesmo padrão do test_problem_user.py: o teste descreve o comportamento correto
e cada bug é tolerado apenas pela sua exceção específica.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from data.constants import TOTAL_PRODUCTS, Messages, Products, Users
from pages import CheckoutOverviewPage
from support.bug_checks import add_remove_params, bug_check, check_add_and_remove, wait_for_render

pytestmark = pytest.mark.regression


class SortingBrokenError(AssertionError):
    """A ordenação exibiu um alerta de erro ou não reordenou a lista."""


class LastNameInputIgnoredError(AssertionError):
    """O campo de sobrenome não guardou o texto digitado."""


class MissingLastNameAcceptedError(AssertionError):
    """O formulário avançou sem sobrenome, sem mostrar o erro de campo obrigatório."""


class FinishFailedError(AssertionError):
    """O botão Finish não concluiu o pedido."""


@pytest.mark.xfail(
    strict=True,
    raises=SortingBrokenError,
    reason="BUG-014 (#15): a ordenação do error_user exibe 'Sorting is broken!' e não ordena",
)
def test_ordenacao_por_nome_z_a(login_as, page: Page):
    # Sem um handler, o Playwright fecha os alertas sozinho e não saberíamos
    # que apareceram. Aqui guardamos a mensagem e aceitamos o alerta.
    alerts = []
    page.on("dialog", lambda dialog: (alerts.append(dialog.message), dialog.accept()))

    inventory = login_as(Users.ERROR)
    expect(inventory.items).to_have_count(TOTAL_PRODUCTS)
    expected = sorted(inventory.get_item_names(), reverse=True)

    inventory.sort_by("za")
    wait_for_render(page)
    with bug_check(SortingBrokenError, lambda: f"Lista não ordenada; alertas: {alerts}"):
        assert inventory.get_item_names() == expected
    if alerts:
        raise SortingBrokenError(f"Alerta inesperado: {alerts}")


@pytest.mark.parametrize("product", add_remove_params("BUG-015 (#16)", Users.ERROR))
def test_adicionar_e_remover_cada_produto(login_as, product: str):
    check_add_and_remove(login_as(Users.ERROR), product)


@pytest.fixture
def checkout_information(login_as):
    inventory = login_as(Users.ERROR)
    inventory.add_to_cart(Products.BACKPACK)  # este produto o error_user consegue adicionar
    return inventory.go_to_cart().checkout()


@pytest.mark.xfail(
    strict=True,
    raises=LastNameInputIgnoredError,
    reason="BUG-016 (#17): o campo de sobrenome do error_user não aceita texto",
)
def test_campo_sobrenome_aceita_texto(checkout_information):
    checkout_information.fill_information("Ana", "Souza", "72980-000")

    values = checkout_information.get_values()
    if values["last_name"] != "Souza":
        raise LastNameInputIgnoredError(f"Campos após o preenchimento: {values}")


@pytest.mark.xfail(
    strict=True,
    raises=MissingLastNameAcceptedError,
    reason="BUG-017 (#18): o error_user avança no checkout sem sobrenome",
)
def test_checkout_exige_sobrenome(checkout_information):
    checkout_information.first_name_input.fill("Ana")
    checkout_information.postal_code_input.fill("72980-000")
    checkout_information.continue_button.click()

    page = checkout_information.page
    wait_for_render(page)
    error = checkout_information.error_message
    with bug_check(MissingLastNameAcceptedError, lambda: f"Sem erro de validação; página atual: {page.url}"):
        assert error.all_inner_texts() == [Messages.LAST_NAME_REQUIRED]


@pytest.mark.xfail(
    strict=True,
    raises=FinishFailedError,
    reason="BUG-018 (#19): o Finish do error_user não conclui o pedido (erro JavaScript)",
)
def test_finish_conclui_o_pedido(login_as, page: Page, browser_errors):
    inventory = login_as(Users.ERROR)
    inventory.add_to_cart(Products.BACKPACK)
    expect(inventory.header.cart_badge).to_have_text("1")

    # Vamos direto ao resumo para o teste não depender do formulário (BUG-016/017).
    overview = CheckoutOverviewPage(page).open()
    expect(overview.item_names).to_have_text([Products.BACKPACK])

    complete = overview.finish()
    wait_for_render(page)
    with bug_check(
        FinishFailedError,
        lambda: f"Continua em {page.url}; erros JavaScript: {browser_errors.page_errors}",
    ):
        assert re.search(r"/checkout-complete\.html$", page.url)
        assert complete.complete_header.all_inner_texts() == [Messages.ORDER_COMPLETE]
