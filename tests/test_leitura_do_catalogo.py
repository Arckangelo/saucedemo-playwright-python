"""Leitura do catálogo do site (support/catalog.py), sem rede.

O catálogo é a fonte do preço esperado de quase toda a suíte, então a leitura
tem testes próprios, com um JavaScript de exemplo no mesmo formato do site:
a lista certa é escolhida por critério, o preço vira Decimal sem passar por
float, um formato irreconhecível falha com mensagem clara e uma queda do site
vira SITE INDISPONÍVEL.
"""

from decimal import Decimal

import pytest

from support.catalog import CatalogFormatError, catalog_changes, fetch_catalog, parse_catalog, script_path
from support.site_guard import SiteUnavailable

# As duas listas do site, como no arquivo real: a do inventário (6 produtos,
# ids 0 a 5) e a das variações de tamanho, que vem DEPOIS no arquivo e tem
# alguns nomes sem tamanho. O desc tem vírgula, chave e colchete, para provar
# que eles não quebram a leitura.
INVENTORY_LIST = (
    "var Ta=[{id:0,name:`Sauce Labs Bike Light`,desc:`Luz, {vermelha} [AAA]`,price:9.99,image_url:Ce},"
    "{id:1,name:`Sauce Labs Bolt T-Shirt`,desc:`a`,price:15.99,image_url:De},"
    "{id:2,name:`Sauce Labs Onesie`,desc:`a`,price:7.99,image_url:Ee},"
    "{id:3,name:`Test.allTheThings() T-Shirt (Red)`,desc:`a`,price:15.99,image_url:Fe},"
    "{id:4,name:`Sauce Labs Backpack`,desc:`a`,price:29.99,image_url:Ge},"
    "{id:5,name:`Sauce Labs Fleece Jacket`,desc:`a`,price:49.99,image_url:He}];"
)
SIZES_LIST = (
    "var Bd=[{id:0,name:`Sauce Labs Bike Light`,desc:`a`,price:9.99,image_url:Ce},"
    "{id:1,name:`Sauce Labs Bolt T-Shirt (XS)`,desc:`a`,price:15.99,image_url:De},"
    "{id:2,name:`Sauce Labs Onesie`,desc:`a`,price:7.99,image_url:Ee},"
    "{id:3,name:`Test.allTheThings() T-Shirt (Red) (XS)`,desc:`a`,price:15.99,image_url:Fe},"
    "{id:4,name:`Sauce Labs Backpack`,desc:`a`,price:29.99,image_url:Ge},"
    "{id:5,name:`Sauce Labs Fleece Jacket (XS)`,desc:`a`,price:49.99,image_url:He},"
    "{id:6,name:`Sauce Labs Fleece Jacket (M)`,desc:`a`,price:49.99,image_url:He}];"
)
CHECKOUT_MATH = "function id(e){let n=0;for(let r in e)n+=Ta[e[r]].price;let r=(n*.08).toFixed(2)}"
SITE_JS = "var x=[1,2,3];" + INVENTORY_LIST + CHECKOUT_MATH + SIZES_LIST

EXPECTED = {
    0: {"name": "Sauce Labs Bike Light", "price": Decimal("9.99")},
    1: {"name": "Sauce Labs Bolt T-Shirt", "price": Decimal("15.99")},
    2: {"name": "Sauce Labs Onesie", "price": Decimal("7.99")},
    3: {"name": "Test.allTheThings() T-Shirt (Red)", "price": Decimal("15.99")},
    4: {"name": "Sauce Labs Backpack", "price": Decimal("29.99")},
    5: {"name": "Sauce Labs Fleece Jacket", "price": Decimal("49.99")},
}

INDEX_HTML = (
    '<!doctype html><html><head><title>Swag Labs</title>'
    '<script type="module" crossorigin src="/assets/index-DnLqFcJI.js"></script></head></html>'
)


# --- Escolha da lista e conversão do preço ----------------------------------------


def test_le_a_lista_do_inventario_e_ignora_a_das_variacoes_de_tamanho():
    assert parse_catalog(SITE_JS) == EXPECTED, "catálogo lido do JavaScript de exemplo"


def test_escolha_nao_depende_da_posicao_no_arquivo():
    # Com a lista de tamanhos ANTES, o resultado tem de ser o mesmo.
    assert parse_catalog(SIZES_LIST + INVENTORY_LIST) == EXPECTED, "catálogo com as listas na ordem inversa"


def test_preco_vira_decimal_exato_sem_passar_por_float():
    # 0.1 + 0.2 em float é 0.30000000000000004; em Decimal, é 0.3.
    js = INVENTORY_LIST.replace("price:9.99", "price:0.1").replace("price:7.99", "price:0.2")
    catalog = parse_catalog(js)
    assert isinstance(catalog[0]["price"], Decimal), "o preço deveria ser Decimal"
    assert catalog[0]["price"] + catalog[2]["price"] == Decimal("0.3"), "soma exata dos preços"


def test_conta_do_checkout_no_arquivo_nao_e_usada():
    # O arquivo tem a conta do imposto (n*.08); a leitura só tira nomes e preços.
    catalog = parse_catalog(SITE_JS)
    assert all(set(product) == {"name", "price"} for product in catalog.values()), "campos lidos do catálogo"


# --- Formato irreconhecível: falha clara, nunca plano B silencioso ---------------


@pytest.mark.parametrize(
    "js, reason",
    [
        pytest.param("var x=[1,2,3];" + CHECKOUT_MATH, "nenhuma lista de produtos", id="sem-lista"),
        pytest.param(SIZES_LIST, "nenhuma lista sem variações de tamanho", id="so-a-lista-de-tamanhos"),
        pytest.param(
            INVENTORY_LIST + INVENTORY_LIST.replace("var Ta", "var Tb"),
            "mais de uma lista candidata",
            id="duas-candidatas",
        ),
        pytest.param(
            INVENTORY_LIST.replace(",{id:5,name:`Sauce Labs Fleece Jacket`,desc:`a`,price:49.99,image_url:He}", ""),
            "esperava os ids 0 a 5",
            id="cinco-produtos",
        ),
        pytest.param(INVENTORY_LIST.replace("price:29.99", "price:Xe*2"), "preço ilegível", id="preco-calculado"),
        pytest.param(INVENTORY_LIST.replace("price:29.99", "price:`29.99`"), "preço ilegível", id="preco-em-texto"),
        pytest.param(
            INVENTORY_LIST.replace("name:`Sauce Labs Onesie`", "name:Je"), "fora do formato", id="nome-calculado"
        ),
        pytest.param(
            INVENTORY_LIST.replace("Sauce Labs Onesie", "Sauce Labs Backpack"), "nomes repetidos", id="nome-repetido"
        ),
    ],
)
def test_formato_irreconhecivel_falha_com_mensagem_clara(js: str, reason: str):
    with pytest.raises(CatalogFormatError) as error:
        parse_catalog(js)
    message = str(error.value)
    assert message.startswith("não foi possível ler o catálogo: "), f"mensagem: {message}"
    assert reason in message, f"mensagem: {message}"


def test_caminho_do_javascript_vem_do_index_html():
    assert script_path(INDEX_HTML) == "/assets/index-DnLqFcJI.js", "caminho lido do index.html"


def test_index_html_sem_o_javascript_falha_com_mensagem_clara():
    with pytest.raises(CatalogFormatError, match="não foi possível ler o catálogo: esperava 1 arquivo"):
        script_path("<html><title>Swag Labs</title></html>")


# --- Download: proteção contra queda do site ---------------------------------------


class FakeResponse:
    def __init__(self, status: int, body: str = ""):
        self.status, self._body = status, body

    def text(self) -> str:
        return self._body


class FakeRequest:
    """Faz o papel do APIRequestContext do Playwright, sem rede."""

    def __init__(self, responses: dict[str, FakeResponse]):
        self.responses, self.paths = responses, []

    def get(self, path: str) -> FakeResponse:
        self.paths.append(path)
        return self.responses[path]


def test_baixa_o_index_html_e_o_javascript_e_le_o_catalogo():
    request = FakeRequest(
        {"/": FakeResponse(200, INDEX_HTML), "/assets/index-DnLqFcJI.js": FakeResponse(200, SITE_JS)}
    )
    assert fetch_catalog(request) == EXPECTED, "catálogo baixado"
    assert request.paths == ["/", "/assets/index-DnLqFcJI.js"], "requisições feitas"


@pytest.mark.parametrize(
    "responses",
    [
        pytest.param({"/": FakeResponse(503)}, id="index-503"),
        pytest.param({"/": FakeResponse(429)}, id="index-429"),
        pytest.param({"/": FakeResponse(200, "<title>Just a moment...</title>")}, id="pagina-de-desafio"),
        pytest.param(
            {"/": FakeResponse(200, INDEX_HTML), "/assets/index-DnLqFcJI.js": FakeResponse(502)}, id="javascript-502"
        ),
    ],
)
def test_queda_do_site_vira_site_indisponivel(responses):
    with pytest.raises(SiteUnavailable):
        fetch_catalog(FakeRequest(responses))


def test_javascript_que_sumiu_falha_com_mensagem_clara():
    # Um 404 no JavaScript (ex.: deploy no meio da leitura) não é queda do site.
    request = FakeRequest({"/": FakeResponse(200, INDEX_HTML), "/assets/index-DnLqFcJI.js": FakeResponse(404)})
    with pytest.raises(CatalogFormatError, match="respondeu HTTP 404"):
        fetch_catalog(request)


# --- Diagnóstico do teste de guarda ------------------------------------------------


def test_diferencas_do_catalogo_dizem_exatamente_o_que_mudou():
    current = {**EXPECTED, 4: {"name": "Sauce Labs Backpack", "price": Decimal("31.99")}}
    del current[0]
    current[6] = {"name": "Sauce Labs Cap", "price": Decimal("12.00")}
    assert catalog_changes(EXPECTED, current) == [
        "id 0 (Sauce Labs Bike Light): saiu do catálogo",
        "Sauce Labs Backpack: 29.99 → 31.99",
        "id 6 (Sauce Labs Cap): entrou no catálogo, a 12.00",
    ], "diferenças descritas"
    assert catalog_changes(EXPECTED, EXPECTED) == [], "catálogo igual não tem diferenças"
