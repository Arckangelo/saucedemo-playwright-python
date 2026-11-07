"""Catálogo de preços lido do site no momento do teste.

O SauceDemo não tem API, mas o JavaScript da aplicação traz o catálogo: uma
lista de objetos {id:4,name:`Sauce Labs Backpack`,desc:`...`,price:29.99,...}.
É dela que a tela do inventário, o carrinho e o resumo tiram nome e preço.
Lê-la na hora é o equivalente a consultar a API num site que tem uma: o valor
esperado vem de uma fonte independente da tela, e uma mudança de preço não
obriga a mudar o código dos testes.

Do arquivo só saem nomes e preços. A conta do checkout (o `*.08` do imposto)
fica de fora de propósito: a regra de imposto continua no teste (TAX_RATE,
RN-17); copiá-la do site faria o teste comparar o site com ele mesmo.

O arquivo tem DUAS listas nesse formato. Pelas rotas da aplicação:
- /inventory.html, o detalhe, o carrinho e o resumo usam a lista com os 6
  produtos (ids 0 a 5);
- /inventory-long.html usa outra, com variações de tamanho ("(XS)", "(M)"...).
A escolha é por critério verificável, nunca pela posição no arquivo: a lista
cujos nomes não têm sufixo de tamanho e cujos ids são 0..TOTAL_PRODUCTS-1.

Se o formato mudar e não der para ler o catálogo com segurança, a leitura
falha com "não foi possível ler o catálogo: ..." (CatalogFormatError). Nunca
há plano B silencioso com uma tabela fixa. Queda do site vira SiteUnavailable
("SITE INDISPONÍVEL"), como em toda a suíte.
"""

import re
from decimal import Decimal

from playwright.sync_api import APIRequestContext
from playwright.sync_api import Error as PlaywrightError

from data.constants import TOTAL_PRODUCTS
from support.site_guard import REAL_PAGE_TITLE, SiteUnavailable, check_status

# O hash do nome muda a cada deploy: o nome é descoberto no index.html.
SCRIPT_PATTERN = re.compile(r'src="(/assets/index-[^"/]+\.js)"')
LIST_START = "[{id:"
SIZE_SUFFIX = re.compile(r"\((?:XS|S|M|L|XL|XXL)\)$")
NUMBER = re.compile(r"\d+(?:\.\d+)?")
INTEGER = re.compile(r"\d+")
_QUOTES = "`'\""

Catalog = dict[int, dict]


class CatalogFormatError(Exception):
    """O JavaScript do site não tem o catálogo no formato esperado."""

    def __init__(self, reason: str):
        super().__init__(f"não foi possível ler o catálogo: {reason}")


# --- Leitura do JavaScript ------------------------------------------------------


def _skip_string(js: str, start: int) -> int:
    """Posição logo depois do texto que começa em `start` (crase, aspas simples ou duplas)."""
    quote = js[start]
    i = start + 1
    while i < len(js):
        if js[i] == "\\":
            i += 2
            continue
        if js[i] == quote:
            return i + 1
        i += 1
    raise CatalogFormatError(f"texto sem fim a partir da posição {start}")


def _split_top_level(js: str, start: int, opening: str, closing: str, separator: str) -> tuple[list[str], int]:
    """Partes de um bloco `opening ... closing` separadas no nível de cima, e a posição do fim.

    Ignora separadores dentro de textos e de blocos internos: um desc com
    vírgula ou chave não quebra a leitura.
    """
    assert js[start] == opening, f"esperava '{opening}' na posição {start}"
    parts, depth, i, part_start = [], 0, start, start + 1
    while i < len(js):
        char = js[i]
        if char in _QUOTES:
            i = _skip_string(js, i)
            continue
        if char in "[{(":
            depth += 1
        elif char in "]})":
            depth -= 1
            if depth == 0:
                if char != closing:
                    raise CatalogFormatError(f"bloco aberto com '{opening}' fechado com '{char}'")
                parts.append(js[part_start:i])
                return [part.strip() for part in parts if part.strip()], i + 1
        elif char == separator and depth == 1:
            parts.append(js[part_start:i])
            part_start = i + 1
        i += 1
    raise CatalogFormatError(f"bloco sem fim a partir da posição {start}")


def _parse_object(text: str) -> dict[str, str]:
    """Campos de um objeto literal simples, como texto: {id:4,name:`x`} -> {"id": "4", "name": "`x`"}."""
    pairs, _ = _split_top_level(text, 0, "{", "}", ",")
    fields = {}
    for pair in pairs:
        key, sep, value = pair.partition(":")
        if sep:
            fields[key.strip()] = value.strip()
    return fields


def _string_value(raw: str) -> str | None:
    """Conteúdo de um texto literal, ou None se não for um texto simples."""
    if len(raw) >= 2 and raw[0] in _QUOTES and raw[-1] == raw[0] and "${" not in raw:
        return raw[1:-1]
    return None


def product_lists(js: str) -> list[list[dict]]:
    """Todas as listas de objetos {id, name, price} do JavaScript, com os campos convertidos.

    Uma lista que começa como produto, mas tem um campo fora do formato (id
    que não é inteiro, nome que não é texto, preço que não é número), é erro:
    seria um catálogo que não dá para ler com segurança.
    """
    lists = []
    position = js.find(LIST_START)
    while position != -1:
        items, end = _split_top_level(js, position, "[", "]", ",")
        objects = [_parse_object(item) for item in items if item.startswith("{")]
        if objects and len(objects) == len(items) and all({"id", "name", "price"} <= o.keys() for o in objects):
            lists.append([_product(fields) for fields in objects])
        position = js.find(LIST_START, end)
    return lists


def _product(fields: dict[str, str]) -> dict:
    raw_id, raw_name, raw_price = fields["id"], fields["name"], fields["price"]
    name = _string_value(raw_name)
    if not INTEGER.fullmatch(raw_id) or name is None:
        raise CatalogFormatError(f"produto com id ou nome fora do formato: id={raw_id} name={raw_name}")
    if not NUMBER.fullmatch(raw_price):
        raise CatalogFormatError(f"preço ilegível em '{name}': {raw_price}")
    # Do texto direto para Decimal, sem passar por float: "29.99" -> Decimal("29.99").
    return {"id": int(raw_id), "name": name, "price": Decimal(raw_price)}


def parse_catalog(js: str) -> Catalog:
    """{id: {"name": ..., "price": Decimal}} da lista de produtos do inventário."""
    lists = product_lists(js)
    if not lists:
        raise CatalogFormatError("nenhuma lista de produtos {id, name, price} no JavaScript")
    candidates = [items for items in lists if not any(SIZE_SUFFIX.search(p["name"]) for p in items)]
    if not candidates:
        raise CatalogFormatError(f"nenhuma lista sem variações de tamanho entre as {len(lists)} encontradas")
    if len(candidates) > 1:
        raise CatalogFormatError(
            f"mais de uma lista candidata ({len(candidates)}), com "
            + " e ".join(f"{len(items)} itens" for items in candidates)
        )
    (items,) = candidates
    ids = [p["id"] for p in items]
    if sorted(ids) != list(range(TOTAL_PRODUCTS)):
        raise CatalogFormatError(f"esperava os ids 0 a {TOTAL_PRODUCTS - 1}, encontrou {ids}")
    names = [p["name"] for p in items]
    if len(set(names)) != len(names):
        raise CatalogFormatError(f"nomes repetidos na lista: {names}")
    return {p["id"]: {"name": p["name"], "price": p["price"]} for p in items}


def script_path(index_html: str) -> str:
    """Caminho do JavaScript da aplicação, lido do index.html."""
    paths = set(SCRIPT_PATTERN.findall(index_html))
    if len(paths) != 1:
        raise CatalogFormatError(f"esperava 1 arquivo /assets/index-*.js no index.html, encontrou {sorted(paths)}")
    return paths.pop()


# --- Comparação ---------------------------------------------------------------


def catalog_changes(reference: Catalog, current: Catalog) -> list[str]:
    """O que mudou do catálogo de referência para o atual, uma linha por diferença."""
    changes = []
    for product_id in sorted(reference.keys() | current.keys()):
        before, now = reference.get(product_id), current.get(product_id)
        if now is None:
            changes.append(f"id {product_id} ({before['name']}): saiu do catálogo")
        elif before is None:
            changes.append(f"id {product_id} ({now['name']}): entrou no catálogo, a {now['price']}")
        else:
            if before["name"] != now["name"]:
                changes.append(f"id {product_id}: nome '{before['name']}' → '{now['name']}'")
            if before["price"] != now["price"]:
                changes.append(f"{now['name']}: {before['price']} → {now['price']}")
    return changes


# --- Download ------------------------------------------------------------------


def _get(request: APIRequestContext, path: str) -> str:
    """Corpo de uma requisição ao site, com a mesma proteção contra queda do resto da suíte."""
    try:
        response = request.get(path)
    except PlaywrightError as error:
        raise SiteUnavailable(f"{path} não respondeu ({str(error).splitlines()[0]})") from error
    check_status(response.status, path)
    if response.status != 200:
        raise CatalogFormatError(f"{path} respondeu HTTP {response.status}")
    return response.text()


def fetch_catalog(request: APIRequestContext) -> Catalog:
    """Baixa o index.html e o JavaScript da aplicação e lê o catálogo."""
    index_html = _get(request, "/")
    # Uma página de erro ou de desafio (ex.: Cloudflare) também responde 200.
    if REAL_PAGE_TITLE not in index_html:
        raise SiteUnavailable("/ respondeu, mas não com a página do Swag Labs")
    return parse_catalog(_get(request, script_path(index_html)))
