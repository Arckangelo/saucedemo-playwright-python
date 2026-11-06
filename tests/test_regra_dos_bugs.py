"""Regra dos bugs conhecidos (support/known_bugs.py).

Uma proteção só vale depois de simular a falha que ela deveria pegar. Aqui os
xfail fora da regra são escritos de propósito:

- direto na função que confere a regra, um caso por defeito;
- numa sessão de pytest dentro do teste (pytester), para provar que o teste
  com xfail errado termina como ERRO, e não como XFAIL, inclusive com xdist.
"""

from pathlib import Path

import pytest

from support.known_bugs import xfail_problems

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCUMENTED = {"BUG-001": "2"}


class FakeBugError(AssertionError):
    """Exceção própria de um bug simulado."""


def problems_of(mark_decorator, strict_default=True, documented=DOCUMENTED) -> list[str]:
    return xfail_problems(mark_decorator.mark, strict_default, documented)


def test_xfail_dentro_da_regra_nao_tem_problemas():
    mark = pytest.mark.xfail(strict=True, raises=FakeBugError, reason="BUG-001 (#2): bug simulado")
    assert problems_of(mark) == []


@pytest.mark.parametrize(
    "mark, expected",
    [
        pytest.param(
            pytest.mark.xfail(strict=True, reason="BUG-001 (#2): x"), "falta raises=", id="sem-raises"
        ),
        pytest.param(
            pytest.mark.xfail(strict=True, raises=AssertionError, reason="BUG-001 (#2): x"),
            "não é específico",
            id="raises-assertionerror",
        ),
        pytest.param(
            pytest.mark.xfail(strict=True, raises=Exception, reason="BUG-001 (#2): x"),
            "não é específico",
            id="raises-exception",
        ),
        pytest.param(
            pytest.mark.xfail(strict=True, raises=(FakeBugError, TimeoutError), reason="BUG-001 (#2): x"),
            "não é específico",
            id="raises-tupla-com-timeout",
        ),
        pytest.param(
            pytest.mark.xfail(strict=False, raises=FakeBugError, reason="BUG-001 (#2): x"),
            "falta strict=True",
            id="strict-false",
        ),
        pytest.param(
            pytest.mark.xfail(strict=True, raises=FakeBugError, reason="bug do carrinho"),
            "motivo fora do formato",
            id="motivo-sem-id",
        ),
        pytest.param(
            pytest.mark.xfail(strict=True, raises=FakeBugError, reason="BUG-1 (#2): x"),
            "motivo fora do formato",
            id="id-com-poucos-digitos",
        ),
        pytest.param(
            pytest.mark.xfail(strict=True, raises=FakeBugError, reason="BUG-001: sem issue"),
            "motivo fora do formato",
            id="motivo-sem-issue",
        ),
        pytest.param(
            pytest.mark.xfail(strict=True, raises=FakeBugError, reason="BUG-999 (#2): x"),
            "BUG-999 não está na tabela",
            id="bug-fora-do-bugs-md",
        ),
        pytest.param(
            pytest.mark.xfail(strict=True, raises=FakeBugError, reason="BUG-001 (#9): x"),
            "BUG-001 é a issue #2",
            id="issue-diferente-do-bugs-md",
        ),
    ],
)
def test_xfail_fora_da_regra_e_apontado(mark, expected: str):
    problems = problems_of(mark)
    assert any(expected in problem for problem in problems), f"problemas encontrados: {problems}"


def test_strict_vem_do_pytest_ini_quando_nao_esta_no_marker():
    mark = pytest.mark.xfail(raises=FakeBugError, reason="BUG-001 (#2): x")
    assert problems_of(mark, strict_default=True) == []
    assert any("strict=True" in problem for problem in problems_of(mark, strict_default=False))


def test_sem_bugs_md_o_id_nao_e_conferido_na_tabela():
    mark = pytest.mark.xfail(strict=True, raises=FakeBugError, reason="BUG-999 (#2): x")
    assert problems_of(mark, documented=None) == []


# --- Resultado da execução (sessão de pytest dentro do teste) ----------------
# Cada sessão interna roda num processo próprio: no mesmo processo, ela se
# misturaria com o pytest-playwright da sessão de fora.

INNER_TESTS = """
import pytest

class FakeBugError(AssertionError):
    pass

def test_comum():
    pass

@pytest.mark.xfail(strict=True, raises=FakeBugError, reason="BUG-001 (#2): bug simulado")
def test_bug_dentro_da_regra():
    raise FakeBugError("o bug reproduz")

@pytest.mark.xfail(strict=True, reason="BUG-001 (#2): bug simulado sem raises")
def test_bug_sem_raises():
    # Sem raises=, o xfail esconderia esta falha, que não é do bug.
    raise TimeoutError("seletor não encontrado")

@pytest.mark.xfail(strict=True, raises=FakeBugError, reason="BUG-001 (#9): issue errada")
def test_bug_com_issue_errada():
    raise FakeBugError("o bug reproduz")

@pytest.fixture
def broken_login():
    raise TimeoutError("login falhou")

@pytest.mark.xfail(strict=True, reason="BUG-001 (#2): sem raises e com o setup quebrado")
def test_bug_sem_raises_com_setup_quebrado(broken_login):
    pass
"""

BUGS_TABLE = """
| ID | Issue |
|----|:-----:|
| [BUG-001](docs/relatorio-de-bugs.md#bug-001) | [#2](https://github.com/exemplo/issues/2) |
"""


@pytest.fixture
def inner_pytest(pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch):
    """Roda uma sessão de pytest em outro processo, com o plugin known_bugs e um BUGS.md."""
    monkeypatch.setenv("PYTHONPATH", str(PROJECT_ROOT))
    pytester.makefile(".md", BUGS=BUGS_TABLE)
    pytester.makeini("[pytest]\nxfail_strict = true\nmarkers =\n    known_bug: bug conhecido\n")

    def run(*args: str) -> pytest.RunResult:
        pytester.makepyfile(INNER_TESTS)
        return pytester.runpytest_subprocess(
            "-p", "support.known_bugs", "-rA", "--junitxml=resultado.xml", *args
        )

    return run


@pytest.mark.parametrize("extra_args", [pytest.param((), id="sem-xdist"), pytest.param(("-n", "2"), id="xdist")])
def test_xfail_fora_da_regra_vira_erro_e_nao_xfail(inner_pytest, pytester: pytest.Pytester, extra_args):
    result = inner_pytest(*extra_args)

    result.assert_outcomes(passed=1, xfailed=1, errors=3)
    result.stdout.fnmatch_lines(
        [
            "*XFAIL*test_bug_dentro_da_regra*",
            "*ERROR*test_bug_sem_raises*",
            "*ERROR*test_bug_com_issue_errada*",
            "*ERROR*test_bug_sem_raises_com_setup_quebrado*",
        ]
    )
    result.stdout.fnmatch_lines(["*falta raises= com a exceção própria do bug*"])
    result.stdout.fnmatch_lines(["*BUG-001 é a issue #2 no BUGS.md, não #9*"])
    # O corpo do teste com xfail errado nem roda: a falha dele não aparece.
    result.stdout.no_fnmatch_line("*seletor não encontrado*")
    assert result.ret == pytest.ExitCode.TESTS_FAILED
    # No relatório JUnit, só o xfail dentro da regra aparece como XFAIL (skipped).
    junit = (pytester.path / "resultado.xml").read_text(encoding="utf-8")
    assert junit.count("<skipped") == 1, junit
    assert junit.count("<error") == 3, junit


def test_xfail_com_bug_recebe_o_marker_known_bug(inner_pytest):
    result = inner_pytest("-m", "known_bug", "--collect-only", "-q")

    # Os 4 xfail com "BUG-" entram; o teste comum fica de fora.
    result.stdout.fnmatch_lines(["*4/5 tests collected (1 deselected)*"])
