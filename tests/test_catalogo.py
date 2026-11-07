"""Teste de guarda do catálogo: avisa quando um preço do site muda.

Os testes tiram o preço esperado do catálogo do site, lido na hora (fixture
catalog_prices). Assim, uma mudança de preço não derruba os testes de checkout:
eles passam a calcular com o preço novo. Este teste é o único que compara o
catálogo com a tabela conferida em 27/10/2026 (PRODUCT_PRICES) e, se algo
mudou, falha dizendo exatamente o quê. É também a única defesa contra um preço
errado no próprio catálogo, que os outros testes aceitariam: por isso a falha
não manda simplesmente atualizar a tabela. Primeiro se confirma com quem define
os preços; se foi engano, é bug do site. Uma variação acima de 50% vem marcada
como SUSPEITO (29.99 → 2.99 parece erro de digitação, não reajuste).

Num produto com preço dinâmico (que muda todo dia), a comparação com a tabela
deixaria de fazer sentido, mas a defesa contra o preço errado não pode sumir
junto: ela passaria a ser uma regra de variação máxima, aplicada na origem do
preço (ver "Decisões técnicas" no README).
"""

from data.constants import PRODUCT_PRICES
from support.catalog import catalog_changes


# CT-CATALOGO-01
def test_catalogo_igual_ao_conferido_em_27_10_2026(catalog_prices):
    changes = catalog_changes(PRODUCT_PRICES, catalog_prices)
    assert not changes, (
        "o catálogo do site mudou desde a conferência de 27/10/2026. Os outros testes já calculam com "
        "o preço novo e não acusam nada: confirme com quem define os preços antes de aceitar. Se a "
        "mudança foi intencional, atualize PRODUCT_PRICES em data/constants.py; se foi engano, é um "
        "bug do site (regra 6 do CLAUDE.md). Variação acima de 50% vem marcada como SUSPEITO:\n"
        + "\n".join(changes)
    )
