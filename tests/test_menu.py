"""Menu lateral: navegação e links."""

import re

import pytest
from playwright.sync_api import expect

from data.constants import ABOUT_URL, Users
from pages import InventoryPage


class BrokenAboutLinkError(AssertionError):
    """O link About não aponta para o site da Sauce Labs."""


def test_all_items_volta_para_o_inventario(inventory_page: InventoryPage):
    cart = inventory_page.go_to_cart()
    cart.header.go_to_all_items()

    expect(cart.page).to_have_url(re.compile(r"/inventory\.html$"))
    expect(inventory_page.header.title).to_have_text("Products")


@pytest.mark.parametrize(
    "username",
    [
        pytest.param(Users.STANDARD, id="standard_user"),
        pytest.param(
            Users.PROBLEM,
            id="problem_user",
            marks=pytest.mark.xfail(
                strict=True,
                raises=BrokenAboutLinkError,
                reason="BUG-012: o About do problem_user aponta para saucelabs.com/error/404",
            ),
        ),
    ],
)
def test_link_about_aponta_para_a_sauce_labs(login_as, username: str):
    href = login_as(username).header.get_about_url()
    if href != ABOUT_URL:
        raise BrokenAboutLinkError(f"About aponta para {href}")
