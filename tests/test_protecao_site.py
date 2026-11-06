"""Proteção contra instabilidade do site (support/site_guard.py).

Uma proteção só vale depois de simular a falha que ela deveria pegar. Aqui a
queda é simulada, sem depender do site:

- a rede é trocada por respostas falsas (page.route) para testar safe_goto;
- uma sessão de pytest roda dentro do teste (pytester) para provar que
  SiteUnavailable vira "SITE INDISPONÍVEL", que o disjuntor abre e que a
  execução termina com código 2, nunca verde.
"""

from pathlib import Path

import pytest
from playwright.sync_api import Page, Route

from support.site_guard import GOTO_ATTEMPTS, SiteUnavailable, check_status, safe_goto

REAL_PAGE = "<html><head><title>Swag Labs</title></head><body></body></html>"
CHALLENGE_PAGE = "<html><head><title>Just a moment...</title></head><body></body></html>"
NO_BACKOFF = (0,)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def fake_site(page: Page, *responses: tuple[int, str] | str) -> list[str]:
    """Troca a rede por respostas na ordem dada; a última se repete.

    Cada resposta é (status, html) ou "abort" (conexão recusada). Devolve a
    lista de URLs pedidas, para contar as tentativas.
    """
    requests: list[str] = []

    def handle(route: Route):
        requests.append(route.request.url)
        response = responses[min(len(requests), len(responses)) - 1]
        if response == "abort":
            route.abort("connectionrefused")
        else:
            status, body = response
            route.fulfill(status=status, content_type="text/html", body=body)

    page.route("**/*", handle)
    return requests


# --- safe_goto ---------------------------------------------------------------


@pytest.mark.parametrize(
    "response",
    [
        pytest.param((503, REAL_PAGE), id="http-503"),
        pytest.param((429, REAL_PAGE), id="http-429"),
        pytest.param((522, REAL_PAGE), id="cloudflare-522"),
        pytest.param((200, CHALLENGE_PAGE), id="pagina-de-desafio-com-200"),
        pytest.param((403, CHALLENGE_PAGE), id="pagina-de-desafio-com-403"),
        pytest.param("abort", id="conexao-recusada"),
    ],
)
def test_site_fora_do_ar_vira_site_indisponivel_depois_das_tentativas(page: Page, response):
    requests = fake_site(page, response)

    with pytest.raises(SiteUnavailable):
        safe_goto(page, "/", backoff_s=NO_BACKOFF)
    assert len(requests) == GOTO_ATTEMPTS, "o carregamento deveria ter sido tentado de novo"


def test_rota_interna_com_404_e_pagina_real_nao_e_queda(page: Page):
    # BUG-005: as rotas internas respondem 404 mesmo funcionando. A página
    # real é reconhecida pelo título, não pelo status.
    requests = fake_site(page, (404, REAL_PAGE))

    response = safe_goto(page, "/inventory.html", backoff_s=NO_BACKOFF)

    assert response is not None and response.status == 404, "deveria devolver a resposta 404"
    assert len(requests) == 1, "um 404 com a página real não pode gerar nova tentativa"


def test_site_que_volta_na_segunda_tentativa_abre_normalmente(page: Page):
    requests = fake_site(page, (503, REAL_PAGE), (200, REAL_PAGE))

    response = safe_goto(page, "/", backoff_s=NO_BACKOFF)

    assert response is not None and response.status == 200, "deveria devolver a resposta da 2ª tentativa"
    assert len(requests) == 2, "deveria parar de tentar assim que o site voltou"


@pytest.mark.parametrize("status", [503, 429])
def test_status_de_queda_em_requisicao_direta_vira_site_indisponivel(status: int):
    with pytest.raises(SiteUnavailable):
        check_status(status, "/inventory.html")


@pytest.mark.parametrize("status", [200, 404])
def test_status_comum_em_requisicao_direta_nao_e_queda(status: int):
    check_status(status, "/inventory.html")  # não lança


# --- Resultado da execução (sessão de pytest dentro do teste) ----------------
# Cada sessão interna roda num processo próprio: no mesmo processo, ela se
# misturaria com o pytest-playwright da sessão de fora.


@pytest.fixture
def inner_pytest(pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch):
    """Roda uma sessão de pytest em outro processo, com o site_guard carregado."""
    monkeypatch.setenv("PYTHONPATH", str(PROJECT_ROOT))

    def run(test_code: str, *args: str) -> pytest.RunResult:
        pytester.makepyfile(test_code)
        return pytester.runpytest_subprocess("-p", "support.site_guard", *args)

    return run


INNER_TESTS = """
import pytest
from support.site_guard import SiteUnavailable

def test_queda():
    raise SiteUnavailable("queda simulada")

@pytest.mark.xfail(strict=True, raises=AssertionError, reason="BUG-999 (#0): bug simulado")
def test_bug_conhecido_durante_queda():
    raise SiteUnavailable("queda simulada")

# Sem raises= (proibido no projeto, mas a proteção não pode depender disso):
# aqui o próprio xfail aceitaria qualquer exceção como "o bug reproduz".
@pytest.mark.xfail(strict=True, reason="BUG-998 (#0): bug simulado sem raises")
def test_bug_conhecido_sem_raises():
    raise SiteUnavailable("queda simulada")

def test_depois_do_disjuntor():
    pass
"""


def test_queda_vira_site_indisponivel_abre_o_disjuntor_e_a_execucao_nao_fica_verde(
    inner_pytest, pytester: pytest.Pytester
):
    result = inner_pytest(INNER_TESTS, "-v", "--junitxml=resultado.xml")

    # Nem o xfail de bug conhecido conta a queda como "o bug reproduz", e os
    # dois últimos testes nem rodam: o disjuntor abriu depois de 2 quedas.
    result.stdout.fnmatch_lines(
        [
            "*test_queda SITE INDISPONÍVEL*",
            "*test_bug_conhecido_durante_queda SITE INDISPONÍVEL*",
            "*test_bug_conhecido_sem_raises SITE INDISPONÍVEL*",
            "*test_depois_do_disjuntor SITE INDISPONÍVEL*",
            "*SITE INDISPONÍVEL em 4 teste(s)*",
        ]
    )
    result.stdout.fnmatch_lines(["*disjuntor aberto*"])
    result.stdout.no_fnmatch_line("*XFAIL*")
    result.stdout.no_fnmatch_line("*PASSED*")
    assert result.ret == pytest.ExitCode.INTERRUPTED, "a execução não pode terminar verde"
    # Relatórios (JUnit, pytest-html) também não podem mostrar a queda como XFAIL.
    junit = (pytester.path / "resultado.xml").read_text(encoding="utf-8")
    assert junit.count('type="pytest.skip" message="SITE INDISPONÍVEL') == 4, junit
    assert "pytest.xfail" not in junit, "a queda apareceu como XFAIL no relatório"


def test_uma_queda_so_nao_abre_o_disjuntor(inner_pytest):
    result = inner_pytest(
        """
        from support.site_guard import SiteUnavailable

        def test_queda():
            raise SiteUnavailable("queda simulada")

        def test_seguinte():
            pass
        """,
        "-v",
    )

    result.stdout.fnmatch_lines(["*test_queda SITE INDISPONÍVEL*", "*test_seguinte PASSED*"])
    assert result.ret == pytest.ExitCode.INTERRUPTED, "uma queda já basta para a execução não ficar verde"


def test_falha_comum_continua_falha(inner_pytest):
    result = inner_pytest(
        """
        def test_falha():
            assert 1 == 2

        def test_passa():
            pass
        """
    )

    result.assert_outcomes(passed=1, failed=1)
    assert result.ret == pytest.ExitCode.TESTS_FAILED


def test_disjuntor_e_codigo_de_saida_funcionam_com_xdist(inner_pytest):
    # Com o xdist, os testes rodam em outro processo: a contagem de quedas
    # passa por uma pasta compartilhada e o código de saída sai do processo
    # principal. Um processo só deixa a ordem dos testes previsível.
    result = inner_pytest(INNER_TESTS, "-n", "1", "-v")

    result.stdout.fnmatch_lines(["*SITE INDISPONÍVEL em 4 teste(s)*"])
    result.stdout.no_fnmatch_line("*PASSED*")
    assert result.ret == pytest.ExitCode.INTERRUPTED, "a execução não pode terminar verde"


def test_processos_do_xdist_compartilham_a_pasta_do_disjuntor(inner_pytest):
    # Sem a pasta do processo principal, cada processo contaria só as próprias
    # quedas e o disjuntor demoraria N vezes mais para abrir.
    result = inner_pytest(
        """
        from support.site_guard import _dir_key

        def test_pasta_do_processo_principal(request):
            shared = request.config.workerinput.get("site_guard_dir")
            assert shared, "o processo não recebeu a pasta do processo principal"
            assert str(request.config.stash[_dir_key]) == shared
        """,
        "-n",
        "1",
    )

    result.assert_outcomes(passed=1)
