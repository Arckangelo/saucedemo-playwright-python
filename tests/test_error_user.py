"""error_user: falhas funcionais que geram erros JavaScript.

Mesmo padrão do test_problem_user.py: o teste descreve o comportamento correto
e cada bug é tolerado apenas pela sua exceção específica.
"""

import pytest
from playwright.sync_api import Page, expect

from data.constants import CHECKOUT_INFO, PRODUCT_IDS, TOTAL_PRODUCTS, Messages, Products, Users
from pages import CheckoutCompletePage, CheckoutInformationPage, CheckoutOverviewPage
from support.bug_checks import add_remove_params, bug_check, check_add_and_remove, on_page, wait_for_render

pytestmark = pytest.mark.regression


class SortingBrokenError(AssertionError):
    """A ordenação exibiu um alerta de erro ou não reordenou a lista."""


class LastNameInputIgnoredError(AssertionError):
    """O campo de sobrenome não guardou o texto digitado."""


class MissingLastNameAcceptedError(AssertionError):
    """O formulário avançou sem sobrenome, sem mostrar o erro de campo obrigatório."""


class FinishFailedError(AssertionError):
    """O botão Finish não concluiu o pedido."""


# CT-ERROR-USER-01
@pytest.mark.xfail(
    strict=True,
    raises=SortingBrokenError,
    reason="BUG-014 (#15): a ordenação do error_user exibe 'Sorting is broken!' e não ordena",
)
def test_ordenacao_por_nome_z_a(login_as, page: Page, catalog_prices):
    # Sem um handler, o Playwright fecha os alertas sozinho e não saberíamos
    # que apareceram. Aqui guardamos a mensagem e aceitamos o alerta.
    alerts = []
    page.on("dialog", lambda dialog: (alerts.append(dialog.message), dialog.accept()))

    inventory = login_as(Users.ERROR)
    expect(inventory.items).to_have_count(TOTAL_PRODUCTS)
    expected = sorted((product["name"] for product in catalog_prices.values()), reverse=True)

    inventory.sort_by("za")
    wait_for_render(page)
    with bug_check(SortingBrokenError, lambda: f"Lista não ordenada; alertas: {alerts}"):
        assert inventory.get_item_names() == expected, "nomes na ordem Z-A"
    if alerts:
        raise SortingBrokenError(f"Alerta inesperado: {alerts}")


# BUG-015: o botão que falha lança "Failed to add item to the cart." ou
# "Failed to remove item from cart." sem tratamento.
# CT-ERROR-USER-02
@pytest.mark.allow_js_errors
@pytest.mark.parametrize("product", add_remove_params("BUG-015 (#16)", Users.ERROR))
def test_adicionar_e_remover_cada_produto(login_as, product: str):
    check_add_and_remove(login_as(Users.ERROR), product)


@pytest.fixture
def checkout_information(page: Page, session_as, cart_with):
    # Carrinho montado pelo localStorage: os testes não dependem do Add to cart (BUG-015).
    session_as(Users.ERROR)
    cart_with(PRODUCT_IDS[Products.BACKPACK])
    return CheckoutInformationPage(page).open()


# BUG-016: digitar no sobrenome lança "Cannot read properties of undefined (reading 'value')".
# CT-ERROR-USER-03
@pytest.mark.allow_js_errors
@pytest.mark.xfail(
    strict=True,
    raises=LastNameInputIgnoredError,
    reason="BUG-016 (#17): o campo de sobrenome do error_user não aceita texto",
)
def test_campo_sobrenome_aceita_texto(checkout_information):
    checkout_information.fill_information(**CHECKOUT_INFO)

    values = checkout_information.get_values()
    if values["last_name"] != CHECKOUT_INFO["last_name"]:
        raise LastNameInputIgnoredError(f"Campos após o preenchimento: {values}")


# CT-ERROR-USER-04
@pytest.mark.xfail(
    strict=True,
    raises=MissingLastNameAcceptedError,
    reason="BUG-017 (#18): o error_user avança no checkout sem sobrenome",
)
def test_checkout_exige_sobrenome(checkout_information):
    checkout_information.first_name_input.fill(CHECKOUT_INFO["first_name"])
    checkout_information.postal_code_input.fill(CHECKOUT_INFO["postal_code"])
    checkout_information.continue_button.click()

    # Ficar no passo 1 (pela URL) e mostrar o erro (esperado, não lido na hora):
    # com a tela lenta, ler o erro na hora acusaria o bug mesmo com o site certo.
    page = checkout_information.page
    with bug_check(MissingLastNameAcceptedError, lambda: f"Sem erro de validação; página atual: {page.url}"):
        assert on_page(page, CheckoutInformationPage.PATH), "o formulário avançou sem sobrenome"
        expect(checkout_information.error_message).to_have_text(Messages.LAST_NAME_REQUIRED)


# BUG-018: o clique em Finish lança "wa.cesetRart is not a function" e o pedido não conclui.
# CT-ERROR-USER-05
@pytest.mark.allow_js_errors
@pytest.mark.xfail(
    strict=True,
    raises=FinishFailedError,
    reason="BUG-018 (#19): o Finish do error_user não conclui o pedido (erro JavaScript)",
)
def test_finish_conclui_o_pedido(page: Page, session_as, cart_with, browser_errors):
    # Carrinho montado pelo localStorage: o teste não depende do Add to cart (BUG-015).
    session_as(Users.ERROR)
    cart_with(PRODUCT_IDS[Products.BACKPACK])

    # Vamos direto ao resumo para o teste não depender do formulário (BUG-016/017).
    overview = CheckoutOverviewPage(page).open()
    expect(overview.item_names, "pré-condição: o carrinho foi montado").to_have_text([Products.BACKPACK])

    complete = overview.finish()
    # A URL diz se o pedido avançou; a tela nova é esperada, não lida na hora:
    # com a tela lenta, ler na hora acusaria o bug mesmo com o site certo.
    with bug_check(
        FinishFailedError,
        lambda: f"Continua em {page.url}; erros JavaScript: {browser_errors.page_errors}",
    ):
        assert on_page(page, CheckoutCompletePage.PATH), "o Finish não levou ao pedido concluído"
        expect(complete.complete_header).to_have_text(Messages.ORDER_COMPLETE)
