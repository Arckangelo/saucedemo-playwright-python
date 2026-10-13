"""Autenticação: login com os diferentes perfis de usuário, erros e rotas protegidas."""

import re

import pytest
from playwright.sync_api import Page, expect

from data.constants import PASSWORD, TOTAL_PRODUCTS, Messages, Users
from pages import InventoryPage, LoginPage


@pytest.mark.smoke
@pytest.mark.parametrize(
    "username",
    [
        pytest.param(Users.STANDARD, id="standard_user"),
        pytest.param(Users.PROBLEM, id="problem_user"),
        pytest.param(Users.PERFORMANCE_GLITCH, id="performance_glitch_user"),
    ],
)
def test_usuarios_validos_acessam_o_inventario(login_page: LoginPage, username: str):
    login_page.login(username, PASSWORD)
    inventory = InventoryPage(login_page.page)

    # expect() é uma asserção "web-first": ela tenta de novo até passar ou
    # estourar o timeout (padrão: 5s), igual ao .should() do Cypress.
    # O performance_glitch_user trava a renderização do inventário por ~5s
    # de propósito, então aqui aumentamos o timeout só para estas asserções.
    expect(login_page.page).to_have_url(re.compile(r"/inventory\.html$"), timeout=15_000)
    expect(inventory.header.title).to_have_text("Products", timeout=15_000)
    expect(inventory.items).to_have_count(6)


@pytest.mark.parametrize(
    "username, password, expected_error",
    [
        pytest.param(Users.LOCKED_OUT, PASSWORD, Messages.LOCKED_OUT, id="usuario-bloqueado"),
        pytest.param(Users.STANDARD, "senha_errada", Messages.INVALID_CREDENTIALS, id="senha-incorreta"),
        pytest.param("usuario_inexistente", PASSWORD, Messages.INVALID_CREDENTIALS, id="usuario-inexistente"),
        pytest.param("", PASSWORD, Messages.USERNAME_REQUIRED, id="usuario-em-branco"),
        pytest.param(Users.STANDARD, "", Messages.PASSWORD_REQUIRED, id="senha-em-branco"),
    ],
)
def test_login_invalido_exibe_mensagem_de_erro(
    login_page: LoginPage, username: str, password: str, expected_error: str
):
    login_page.login(username, password)

    expect(login_page.error_message).to_have_text(expected_error)
    expect(login_page.page).not_to_have_url(re.compile(r"/inventory\.html"))


@pytest.mark.parametrize(
    "protected_path",
    ["/inventory.html", "/cart.html", "/checkout-step-one.html"],
)
def test_rotas_protegidas_exigem_login(page: Page, protected_path: str):
    page.goto(protected_path)
    login = LoginPage(page)

    # Sem sessão, o site redireciona para o login e explica o motivo.
    expect(login.login_button).to_be_visible()
    expect(login.error_message).to_have_text(Messages.not_logged_in(protected_path))


def test_logout_encerra_a_sessao(inventory_page: InventoryPage):
    inventory_page.header.logout()
    login = LoginPage(inventory_page.page)
    expect(login.login_button).to_be_visible()

    # Não basta voltar para a tela de login: a sessão precisa ter sido de fato
    # encerrada. Tentar acessar o inventário de novo deve ser bloqueado.
    inventory_page.open()
    expect(login.error_message).to_have_text(Messages.not_logged_in(InventoryPage.PATH))
