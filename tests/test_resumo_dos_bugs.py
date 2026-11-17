"""Resumo dos bugs teste a teste na página do CI (support/bug_summary.py).

Uma proteção só vale depois de simular o que ela deveria mostrar. Aqui uma
sessão de pytest roda dentro do teste (pytester), com um teste para cada
resultado possível de um bug conhecido, e o resumo escrito no arquivo do
GITHUB_STEP_SUMMARY é conferido linha a linha, com e sem pytest-xdist.
"""

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent

INNER_TESTS = """
import pytest

from support.site_guard import SiteUnavailable

class FakeBugError(AssertionError):
    pass

def bug(number, **kwargs):
    kwargs.setdefault("raises", FakeBugError)
    return pytest.mark.xfail(strict=True, reason=f"BUG-00{number} (#{number + 1}): bug simulado", **kwargs)

def test_comum():
    pass

@bug(1)
def test_reproduz():
    raise FakeBugError("o bug reproduz")

@bug(1)
@pytest.mark.parametrize("product", ["a|b"])
def test_nome_com_barra(product):
    raise FakeBugError("o bug reproduz")

@bug(2)
def test_corrigido():
    pass

@bug(3)
def test_outra_falha():
    raise TimeoutError("seletor não encontrado")

@bug(4)
def test_inconclusivo():
    pytest.skip("telemetria sem resposta")

@bug(5)
def test_site_fora_do_ar():
    raise SiteUnavailable("/cart.html respondeu HTTP 503")

@pytest.fixture
def broken_cleanup():
    yield
    raise RuntimeError("limpeza falhou")

@bug(6)
def test_erro_no_encerramento(broken_cleanup):
    raise FakeBugError("o bug reproduz")

@bug(7, raises=None)
def test_fora_da_regra():
    raise FakeBugError("o bug reproduz")
"""

BUGS_TABLE = "| ID | Issue |\n|----|:-----:|\n" + "".join(
    f"| [BUG-00{n}](x) | [#{n + 1}](https://exemplo/issues/{n + 1}) |\n" for n in range(1, 8)
)

EXPECTED_ROWS = [
    "| BUG-001 | [#2](https://github.com/exemplo/repo/issues/2) | `test_resumo.py::test_nome_com_barra[a\\|b]` | reproduz |",
    "| BUG-001 | [#2](https://github.com/exemplo/repo/issues/2) | `test_resumo.py::test_reproduz` | reproduz |",
    "| BUG-002 | [#3](https://github.com/exemplo/repo/issues/3) | `test_resumo.py::test_corrigido` | **CORRIGIDO?** o "
    "teste passou: confirme no site e tire o xfail |",
    "| BUG-003 | [#4](https://github.com/exemplo/repo/issues/4) | `test_resumo.py::test_outra_falha` | **falha diferente "
    "da do bug**: TimeoutError: seletor não encontrado |",
    "| BUG-004 | [#5](https://github.com/exemplo/repo/issues/5) | `test_resumo.py::test_inconclusivo` | inconclusivo: "
    "telemetria sem resposta |",
    "| BUG-005 | [#6](https://github.com/exemplo/repo/issues/6) | `test_resumo.py::test_site_fora_do_ar` | SITE "
    "INDISPONÍVEL: /cart.html respondeu HTTP 503 |",
    "| BUG-006 | [#7](https://github.com/exemplo/repo/issues/7) | `test_resumo.py::test_erro_no_encerramento` | **erro no "
    "encerramento**: RuntimeError: limpeza falhou |",
    "| BUG-007 | [#8](https://github.com/exemplo/repo/issues/8) | `test_resumo.py::test_fora_da_regra` | **erro na "
    "preparação**: xfail fora da regra dos bugs conhecidos (CLAUDE.md, regra 4): - falta raises= com a exceção "
    "própria do bug |",
]


@pytest.fixture
def inner_pytest(pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch):
    """Roda uma sessão de pytest em outro processo, com os plugins da suíte e um BUGS.md."""
    monkeypatch.setenv("PYTHONPATH", str(PROJECT_ROOT))
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
    monkeypatch.setenv("GITHUB_REPOSITORY", "exemplo/repo")
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    pytester.makefile(".md", BUGS=BUGS_TABLE)
    pytester.makeini("[pytest]\nxfail_strict = true\nmarkers =\n    known_bug: bug conhecido\n")
    pytester.makepyfile(test_resumo=INNER_TESTS)

    def run(*args: str, summary: bool = True) -> tuple[pytest.RunResult, Path]:
        path = pytester.path / "resumo.md"
        if summary:
            monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(path))
        result = pytester.runpytest_subprocess(
            "-p", "support.site_guard", "-p", "support.known_bugs", "-p", "support.bug_summary", *args
        )
        return result, path

    return run


@pytest.mark.parametrize("extra_args", [pytest.param((), id="sem-xdist"), pytest.param(("-n", "2"), id="xdist")])
def test_resumo_mostra_o_resultado_de_cada_teste_de_bug(inner_pytest, extra_args):
    result, path = inner_pytest(*extra_args)

    # Controle positivo: a sessão interna teve mesmo cada um dos resultados.
    result.assert_outcomes(passed=1, xfailed=3, failed=2, skipped=1, errors=2)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "### Bugs conhecidos, teste a teste", f"título do resumo: {lines}"
    rows = [line for line in lines if line.startswith("| BUG-")]
    for row, expected in zip(rows, EXPECTED_ROWS, strict=True):
        assert row == expected, f"linha do resumo:\n{row}\nesperava:\n{expected}"
    assert "test_comum" not in path.read_text(encoding="utf-8"), "teste comum não entra no resumo"
    text = "\n".join(lines)
    assert (
        "8 teste(s) de bugs conhecidos · reproduz: 2 · **CORRIGIDO?**: 1 · **falha diferente da do bug**: 1 · "
        "**erro na preparação**: 1 · **erro no encerramento**: 1 · inconclusivo: 1 · SITE INDISPONÍVEL: 1"
    ) in text, f"contagem do resumo:\n{text}"
    assert "> **Atenção:** 1 bug(s) parece(m) corrigido(s)" in text, f"aviso de bug corrigido:\n{text}"
    assert "> **Atenção:** 3 teste(s) de bug não chegaram a conferir o bug" in text, f"aviso de falhas:\n{text}"


def test_execucao_sem_os_testes_de_bugs_diz_que_eles_nao_rodaram(inner_pytest):
    result, path = inner_pytest("-m", "not known_bug")

    result.assert_outcomes(passed=1)
    text = path.read_text(encoding="utf-8")
    assert "Os testes de bugs conhecidos não rodaram nesta execução." in text, f"resumo:\n{text}"


def test_fora_do_ci_nada_e_escrito(inner_pytest):
    result, path = inner_pytest(summary=False)

    result.assert_outcomes(passed=1, xfailed=3, failed=2, skipped=1, errors=2)
    assert not path.exists(), "sem GITHUB_STEP_SUMMARY, o resumo não deveria ser escrito"
