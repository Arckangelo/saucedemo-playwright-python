"""Carrinho e checkout: persistência, validação de formulário e compra completa."""

import re
from decimal import ROUND_HALF_UP, Decimal

import pytest
from playwright.sync_api import Page, expect

from data.constants import CHECKOUT_INFO, PRODUCT_IDS, PRODUCT_PRICES, TAX_RATE, Messages, Products
from pages import CartPage, CheckoutInformationPage, CheckoutOverviewPage, InventoryPage
from support.bug_checks import bug_check, wait_for_render
from support.item_checks import assert_item
from support.state import cart_ids


class EmptyCartOrderError(AssertionError):
    """Um pedido sem nenhum item foi concluído."""


class SkippedCheckoutStepError(AssertionError):
    """O pedido foi concluído sem passar pelo passo 1 (nome, sobrenome e CEP)."""


class BlankFieldAcceptedError(AssertionError):
    """Um campo preenchido só com espaços foi aceito como válido."""


@pytest.fixture
def checkout_information_page(page: Page, standard_session, cart_with) -> CheckoutInformationPage:
    """Fixture local (vale só para este arquivo): abre o passo 1 do checkout com um item.

    Note que ela depende de outras fixtures (standard_session e cart_with, do
    conftest). O pytest resolve a cadeia sozinho: cookie -> carrinho -> checkout.
    O carrinho é montado pelo localStorage e a tela é aberta direto pela URL:
    adicionar e navegar já têm testes próprios.
    """
    cart_with(PRODUCT_IDS[Products.BACKPACK])
    return CheckoutInformationPage(page).open()


@pytest.mark.smoke
def test_compra_completa_do_inventario_ao_pedido_concluido(inventory_page: InventoryPage):
    # A única jornada inteira pela tela: adicionar, carrinho, formulário,
    # resumo e Finish. Os cálculos do resumo têm teste próprio.
    products = [Products.BACKPACK, Products.BOLT_TSHIRT, Products.ONESIE]
    for product in products:
        inventory_page.add_to_cart(product)

    cart = inventory_page.go_to_cart()
    expect(cart.item_names).to_have_text(products)

    information = cart.checkout()
    information.fill_information(**CHECKOUT_INFO)
    overview = information.continue_to_overview()
    # Cada linha conferida contra a tabela de referência, não contra a tela.
    expect(overview.items).to_have_count(len(products))  # sincroniza antes de ler
    for row, product in zip(overview.get_rows(), products, strict=True):
        assert_item(row, PRODUCT_IDS[product])

    # Que o carrinho é esvaziado depois do pedido é conferido em
    # test_concluir_o_pedido_esvazia_o_carrinho, direto no localStorage.
    complete = overview.finish()
    expect(complete.complete_header).to_have_text(Messages.ORDER_COMPLETE)


def test_resumo_calcula_subtotal_imposto_e_total(page: Page, standard_session, cart_with):
    # RN-17. Carrinho montado pelo localStorage e resumo aberto pela URL: o
    # caminho até o resumo é coberto pela jornada completa.
    products = [Products.BACKPACK, Products.BOLT_TSHIRT, Products.ONESIE]
    cart_with(*(PRODUCT_IDS[product] for product in products))
    overview = CheckoutOverviewPage(page).open()
    expect(overview.items).to_have_count(len(products))  # pré-condição: o carrinho foi montado

    # Valores esperados calculados a partir da tabela de referência, não dos
    # preços exibidos: se o site exibisse e cobrasse um preço errado de forma
    # coerente (como o BUG-019), somar a própria tela não perceberia.
    expected_subtotal = sum(PRODUCT_PRICES[PRODUCT_IDS[product]]["price"] for product in products)
    expected_tax = (expected_subtotal * Decimal(TAX_RATE)).quantize(Decimal("0.01"), ROUND_HALF_UP)

    assert overview.get_subtotal() == expected_subtotal
    assert overview.get_tax() == expected_tax
    assert overview.get_total() == expected_subtotal + expected_tax


@pytest.mark.parametrize(
    "empty_field, expected_error",
    [
        pytest.param("first_name", Messages.FIRST_NAME_REQUIRED, id="sem-nome"),
        pytest.param("last_name", Messages.LAST_NAME_REQUIRED, id="sem-sobrenome"),
        pytest.param("postal_code", Messages.POSTAL_CODE_REQUIRED, id="sem-cep"),
    ],
)
def test_checkout_exige_campos_obrigatorios(
    checkout_information_page: CheckoutInformationPage,
    empty_field: str,
    expected_error: str,
):
    checkout = checkout_information_page
    # Só o campo do caso fica vazio; os outros recebem dados válidos.
    checkout.fill_information(**{**CHECKOUT_INFO, empty_field: ""})
    checkout.continue_button.click()

    expect(checkout.error_message).to_have_text(expected_error)
    # Continua no passo 1: o formulário inválido não pode avançar.
    expect(checkout.page).to_have_url(re.compile(re.escape(checkout.PATH) + "$"))


@pytest.mark.regression
@pytest.mark.parametrize(
    "blank_field, field_label",
    [
        pytest.param("first_name", "nome", id="nome-so-espacos"),
        pytest.param("last_name", "sobrenome", id="sobrenome-so-espacos"),
        pytest.param("postal_code", "CEP", id="cep-so-espacos"),
    ],
)
@pytest.mark.xfail(
    strict=True,
    raises=BlankFieldAcceptedError,
    reason="BUG-002 (#3): o checkout aceita campos preenchidos só com espaços",
)
def test_checkout_rejeita_campos_so_com_espacos(
    checkout_information_page: CheckoutInformationPage,
    blank_field: str,
    field_label: str,
):
    checkout = checkout_information_page
    checkout.fill_information(**{**CHECKOUT_INFO, blank_field: "   "})
    checkout.continue_button.click()
    wait_for_render(checkout.page)

    with bug_check(
        BlankFieldAcceptedError,
        lambda: f"Campo {field_label} só com espaços foi aceito; página atual: {checkout.page.url}",
    ):
        assert checkout.error_message.is_visible()


def _blocked(locator) -> bool:
    """True se, depois de a tela ser renderizada, o elemento não estiver lá: a etapa foi bloqueada."""
    wait_for_render(locator.page)
    return not locator.is_visible()


@pytest.mark.regression
@pytest.mark.xfail(
    strict=True,
    raises=EmptyCartOrderError,
    reason="BUG-001 (#2): é possível concluir um pedido com o carrinho vazio",
)
def test_nao_conclui_pedido_com_carrinho_vazio(inventory_page: InventoryPage):
    cart = inventory_page.go_to_cart()
    expect(cart.items).to_have_count(0)  # pré-condição: carrinho vazio

    # A correção pode bloquear o pedido em qualquer etapa (botão Checkout
    # escondido ou desabilitado, formulário que não avança, Finish que não
    # conclui). Cada bloqueio conta como comportamento correto: o teste passa,
    # e o xfail(strict=True) avisa que o bug foi corrigido.
    if _blocked(cart.checkout_button) or not cart.checkout_button.is_enabled():
        return
    information = cart.checkout()
    information.fill_information(**CHECKOUT_INFO)
    overview = information.continue_to_overview()
    if _blocked(overview.finish_button):
        return
    complete = overview.finish()
    if _blocked(complete.complete_header):
        return
    raise EmptyCartOrderError(f"Pedido vazio concluído: {complete.complete_header.inner_text()}")


@pytest.mark.regression
@pytest.mark.xfail(
    strict=True,
    raises=SkippedCheckoutStepError,
    reason="BUG-024 (#ISSUE): o resumo abre pela URL e conclui o pedido sem o passo 1 (nome, sobrenome e CEP)",
)
def test_resumo_exige_o_passo_1_preenchido(page: Page, standard_session, cart_with):
    # Carrinho com um item e o resumo aberto direto pela URL, sem nunca passar
    # pelo formulário do passo 1.
    cart_with(PRODUCT_IDS[Products.BACKPACK])
    overview = CheckoutOverviewPage(page).open()

    # A correção pode bloquear em qualquer ponto (voltar ao passo 1, esconder o
    # Finish ou não concluir). Cada bloqueio é o comportamento correto: o teste
    # passa, e o xfail(strict=True) avisa que o bug foi corrigido.
    if _blocked(overview.finish_button):
        return
    expect(overview.items).to_have_count(1)  # pré-condição: o resumo mostra o carrinho montado
    complete = overview.finish()
    if _blocked(complete.complete_header):
        return
    raise SkippedCheckoutStepError(f"Pedido concluído sem nome, sobrenome e CEP: {page.url}")


def test_carrinho_persiste_apos_recarregar_a_pagina(inventory_page: InventoryPage):
    inventory_page.add_to_cart(Products.BACKPACK)
    inventory_page.add_to_cart(Products.FLEECE_JACKET)

    inventory_page.page.reload()
    expect(inventory_page.header.cart_badge).to_have_text("2")

    # O saucedemo guarda o carrinho no localStorage (cart_ids lê por baixo da
    # tela, como cy.window().then(win => win.localStorage...) no Cypress).
    # Ids exatos, na ordem em que foram adicionados (RN-08 e RN-13): é nesse
    # formato que os testes montam o carrinho direto pelo localStorage.
    assert cart_ids(inventory_page.page) == [PRODUCT_IDS[Products.BACKPACK], PRODUCT_IDS[Products.FLEECE_JACKET]]

    cart: CartPage = inventory_page.go_to_cart()
    expect(cart.item_names).to_have_text([Products.BACKPACK, Products.FLEECE_JACKET])


def test_concluir_o_pedido_esvazia_o_carrinho(page: Page, standard_session, cart_with):
    # RN-19. Carrinho montado pelo localStorage e resumo aberto pela URL: o
    # caminho até aqui já é coberto pela jornada completa.
    cart_with(PRODUCT_IDS[Products.BACKPACK])
    overview = CheckoutOverviewPage(page).open()
    expect(overview.items).to_have_count(1)  # pré-condição: o carrinho foi montado

    complete = overview.finish()
    expect(complete.complete_header).to_have_text(Messages.ORDER_COMPLETE)

    # Não basta o contador sumir da tela: o carrinho tem de sair do localStorage,
    # senão os itens voltam na próxima visita.
    assert cart_ids(page) == []


def test_remover_do_carrinho_mantem_os_demais_apos_recarregar(page: Page, standard_session, cart_with):
    # Carrinho montado pelo localStorage: o "Add to cart" da tela já tem teste
    # próprio e não pode derrubar este, que verifica a remoção.
    backpack, fleece = PRODUCT_IDS[Products.BACKPACK], PRODUCT_IDS[Products.FLEECE_JACKET]
    cart_with(backpack, fleece)
    cart = CartPage(page).open()
    expect(cart.items).to_have_count(2)  # pré-condição: o carrinho foi montado

    cart.remove(Products.BACKPACK)
    expect(cart.items).to_have_count(1)

    # A tela pode apagar a linha sem gravar nada; só o reload prova que a
    # remoção persistiu (RN-13) e que o item removido não volta.
    page.reload()
    expect(cart.items).to_have_count(1)
    (row,) = cart.get_rows()
    assert_item(row, fleece)


def test_carrinho_mostra_cada_produto_com_nome_preco_e_quantidade_1(inventory_page: InventoryPage):
    # Nome e preço conferidos contra a tabela de referência, não contra a tela.
    # RN-11: o botão alterna entre Add to cart e Remove, então não há como
    # adicionar o mesmo produto duas vezes; a quantidade de cada linha é 1.
    products = [Products.BACKPACK, Products.FLEECE_JACKET]
    for product in products:
        inventory_page.add_to_cart(product)

    cart = inventory_page.go_to_cart()
    expect(cart.items).to_have_count(len(products))  # sincroniza antes de ler
    for row, product in zip(cart.get_rows(), products, strict=True):
        assert_item(row, PRODUCT_IDS[product])
