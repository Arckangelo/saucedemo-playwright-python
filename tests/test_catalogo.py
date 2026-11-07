"""Teste de guarda do catálogo: avisa quando um preço do site muda.

Os testes tiram o preço esperado do catálogo do site, lido na hora (fixture
catalog_prices). Assim, uma mudança de preço não derruba os testes de checkout:
eles passam a calcular com o preço novo. Este teste é o único que compara o
catálogo com a tabela conferida em 27/10/2026 (PRODUCT_PRICES) e, se algo
mudou, falha dizendo exatamente o quê. É também a única defesa contra um preço
errado no próprio catálogo, que os outros testes aceitariam.

Num produto com preço dinâmico (que muda todo dia), este teste e a tabela
seriam removidos: mudar de preço seria o normal, não uma notícia.
"""

from data.constants import PRODUCT_PRICES
from support.catalog import catalog_changes


# CT-CATALOGO-01
def test_catalogo_igual_ao_conferido_em_27_10_2026(catalog_prices):
    changes = catalog_changes(PRODUCT_PRICES, catalog_prices)
    assert not changes, (
        "o catálogo do site mudou desde a conferência de 27/10/2026. Confirme a mudança no site e "
        "atualize PRODUCT_PRICES em data/constants.py (os outros testes já usam o preço novo):\n"
        + "\n".join(changes)
    )
