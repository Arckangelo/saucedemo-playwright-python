"""Convenções da suíte conferidas automaticamente (CLAUDE.md, regra 11).

Estes testes leem o código da própria suíte, sem abrir o site. Uma regra que
só existe por escrito acaba quebrada sem ninguém perceber; aqui ela quebra o CI.
"""

import ast
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHECKED_DIRS = ["tests", "support"]


def python_files() -> list[Path]:
    return sorted(path for folder in CHECKED_DIRS for path in (PROJECT_ROOT / folder).glob("*.py"))


def asserts_without_message(source: str) -> list[int]:
    """Linhas das `assert` sem mensagem no código-fonte dado.

    Usa a árvore sintática, e não busca por texto: assim, uma `assert` dentro
    de uma string (como o código das sessões internas do pytester) não conta,
    e uma mensagem em outra linha conta.
    """
    return [
        node.lineno
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Assert) and node.msg is None
    ]


@pytest.mark.parametrize(
    "source, expected",
    [
        pytest.param("assert total == 10\n", [1], id="sem-mensagem"),
        pytest.param('assert total == 10, "total do resumo"\n', [], id="com-mensagem"),
        pytest.param('assert (\n    total == 10\n), (\n    "total do resumo"\n)\n', [], id="mensagem-em-outra-linha"),
        pytest.param('CODE = """\nassert x\n"""\n', [], id="assert-dentro-de-string"),
        pytest.param("def f():\n    assert ok\n", [2], id="dentro-de-funcao"),
    ],
)
def test_detector_de_assert_sem_mensagem(source: str, expected: list[int]):
    # A checagem só vale se o detector acerta: um caso por situação.
    assert asserts_without_message(source) == expected, "linhas apontadas pelo detector"


def test_toda_assert_tem_mensagem():
    missing = [
        f"{path.relative_to(PROJECT_ROOT)}:{line}"
        for path in python_files()
        for line in asserts_without_message(path.read_text(encoding="utf-8"))
    ]
    assert not missing, (
        "assert sem mensagem (diga o que é conferido: assert valor == esperado, \"o que é\"):\n"
        + "\n".join(missing)
    )
