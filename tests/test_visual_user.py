"""visual_user: diferenças visuais em relação ao standard_user.

O standard_user é o ORÁCULO: os valores esperados (preços, imagens, posição e
tamanho dos elementos) são coletados dele na hora, em outro contexto do
navegador, em vez de ficarem fixos no código. Comparar valores do DOM é mais
estável no CI do que comparar screenshots, que variam com fonte, sistema
operacional e navegador. Os screenshots ficam só como evidência no relatório.
"""

from collections.abc import Callable

import pytest
from playwright.sync_api import Locator, expect

from data.constants import TOTAL_PRODUCTS, Products, Users
from pages import InventoryPage

pytestmark = pytest.mark.regression

# Diferença máxima, em pixels, para considerar duas posições "iguais". Absorve
# arredondamentos de renderização; só divergências claras viram bug.
LAYOUT_TOLERANCE_PX = 5


class PriceMismatchError(AssertionError):
    """Preço exibido diferente do preço do catálogo."""


class ImageMismatchError(AssertionError):
    """Imagem do produto diferente da exibida ao standard_user."""


class LayoutShiftError(AssertionError):
    """Elemento fora da posição ou do tamanho exibidos ao standard_user."""


@pytest.fixture
def visual_inventory(login_as) -> InventoryPage:
    inventory = login_as(Users.VISUAL)
    expect(inventory.items).to_have_count(TOTAL_PRODUCTS)
    return inventory


@pytest.fixture
def oracle(oracle_inventory) -> InventoryPage:
    expect(oracle_inventory.items).to_have_count(TOTAL_PRODUCTS)
    return oracle_inventory


@pytest.mark.xfail(
    strict=True,
    raises=PriceMismatchError,
    reason="BUG-019: o visual_user vê preços aleatórios, diferentes dos cobrados",
)
def test_precos_iguais_aos_do_standard_user(visual_inventory, oracle):
    expected = oracle.get_prices_by_name()
    shown = visual_inventory.get_prices_by_name()

    # .get(): um produto ausente na tela aparece como None na divergência, em vez de KeyError.
    divergent = {
        name: f"{shown.get(name)} (esperado {price})"
        for name, price in expected.items()
        if shown.get(name) != price
    }
    if divergent:
        raise PriceMismatchError(f"Preços divergentes: {divergent}")


@pytest.mark.xfail(
    strict=True,
    raises=ImageMismatchError,
    reason="BUG-020: o visual_user vê a imagem de erro (sl-404) na Backpack",
)
def test_imagens_iguais_as_do_standard_user(visual_inventory, oracle):
    expected = oracle.get_images_by_name()
    shown = visual_inventory.get_images_by_name()

    divergent = {name: shown.get(name) for name, src in expected.items() if shown.get(name) != src}
    if divergent:
        raise ImageMismatchError(f"Imagens divergentes: {divergent}")


ELEMENTS: dict[str, Callable[[InventoryPage], Locator]] = {
    "icone-do-carrinho": lambda inv: inv.header.cart_link,
    "botao-do-menu": lambda inv: inv.header.menu_button,
    "titulo": lambda inv: inv.header.title,
    "ordenacao": lambda inv: inv.sort_select,
    "botao-do-primeiro-produto": lambda inv: inv.item_button(Products.BACKPACK),
    "botao-do-ultimo-produto": lambda inv: inv.item_button(Products.RED_TSHIRT),
}

KNOWN_LAYOUT_BUGS = {
    "icone-do-carrinho": "BUG-021: o ícone do carrinho do visual_user fica deslocado sobre a ordenação",
    "botao-do-ultimo-produto": "BUG-022: o botão do último produto do visual_user fica desalinhado",
}


def _layout_params() -> list:
    return [
        pytest.param(
            name,
            id=name,
            marks=(
                [pytest.mark.xfail(strict=True, raises=LayoutShiftError, reason=KNOWN_LAYOUT_BUGS[name])]
                if name in KNOWN_LAYOUT_BUGS
                else []
            ),
        )
        for name in ELEMENTS
    ]


def _wait_for_fonts(inventory: InventoryPage):
    # A largura dos textos muda quando a fonte web (DM Sans) termina de carregar.
    # Medir antes disso compara a fonte provisória de uma página com a final da
    # outra e gera falsos positivos. document.fonts.ready é a promessa do
    # navegador que resolve quando todas as fontes estão prontas.
    inventory.page.evaluate("() => document.fonts.ready.then(() => true)")


@pytest.mark.parametrize("element", _layout_params())
def test_layout_igual_ao_do_standard_user(visual_inventory, oracle, element: str):
    _wait_for_fonts(oracle)
    _wait_for_fonts(visual_inventory)
    locate = ELEMENTS[element]
    # bounding_box() devolve x, y, largura e altura do elemento na tela.
    expected = locate(oracle).bounding_box()
    actual = locate(visual_inventory).bounding_box()
    assert expected and actual, f"'{element}' não está visível"

    deltas = {key: round(actual[key] - expected[key]) for key in ("x", "y", "width", "height")}
    shifted = {key: delta for key, delta in deltas.items() if abs(delta) > LAYOUT_TOLERANCE_PX}
    if shifted:
        raise LayoutShiftError(f"'{element}' diverge do standard_user em pixels: {shifted}")
