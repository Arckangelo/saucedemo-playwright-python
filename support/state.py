"""Leitura do estado que o site guarda no navegador, por baixo da tela.

O saucedemo não tem back-end: o carrinho mora no localStorage e a sessão em um
cookie. Conferir esse estado (e não só o DOM) é o equivalente a consultar a
API depois da ação, como no Cypress.
"""

import json

from playwright.sync_api import BrowserContext, Page

CART_KEY = "cart-contents"
SESSION_COOKIE = "session-username"


def cart_ids(page: Page) -> list[int]:
    """Ids gravados no carrinho, na ordem em que foram adicionados ([] se não houver carrinho)."""
    raw = page.evaluate(f"() => localStorage.getItem('{CART_KEY}')")
    return json.loads(raw) if raw else []


def session_cookie(context: BrowserContext) -> dict | None:
    """O cookie de sessão do contexto, ou None se ele não existir."""
    return next((cookie for cookie in context.cookies() if cookie["name"] == SESSION_COOKIE), None)
