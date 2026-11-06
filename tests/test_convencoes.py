"""Convenções da suíte conferidas automaticamente (CLAUDE.md, regras 5 e 11).

Estes testes leem o código da própria suíte, sem abrir o site. Uma regra que
só existe por escrito acaba quebrada sem ninguém perceber; aqui ela quebra o CI.

A leitura é pela árvore sintática, e não por busca de texto: código dentro de
uma string (como o das sessões internas do pytester) e comentários não contam.
"""

import ast
from collections import Counter
from pathlib import Path

import pytest

from data.constants import PASSWORD

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHECKED_DIRS = ["tests", "support", "pages"]
CHECKED_FILES = ["conftest.py"]
# A senha pública dos usuários do site só pode aparecer na massa de dados.
CREDENTIALS_FILE = "data/constants.py"

# Atalho proibido -> por que é proibido (aparece na mensagem de falha).
SHORTCUTS = {
    "espera fixa": "espera por tempo fixo: o Playwright espera sozinho; para provar que algo não "
    "aconteceu, use wait_for_render ou um sinal direto (regra 11)",
    "page.goto direto": "abra páginas por BasePage.open() ou safe_goto, que tratam a queda do site (regra 5)",
    "teste pulado": "teste pulado não testa nada e some do resultado",
    "depurador": "breakpoint() ou pdb esquecido trava a execução no CI",
    "senha fixa": f"a senha dos usuários fica só em {CREDENTIALS_FILE} (PASSWORD)",
}

# Exceções justificadas: (arquivo, atalho) -> (quantidade permitida, motivo).
# A quantidade é exata: um segundo uso no mesmo arquivo também é barrado.
ALLOWED = {
    ("support/site_guard.py", "espera fixa"): (1, "pausa entre as tentativas de carregar a página (regra 5)"),
    ("support/site_guard.py", "page.goto direto"): (1, "é o próprio safe_goto"),
    ("tests/test_console_e_rede.py", "teste pulado"): (
        1,
        "BUG-006: telemetria enviada sem resposta é inconclusiva, nunca um falso 'corrigido'",
    ),
}


def python_files() -> list[Path]:
    paths = [path for folder in CHECKED_DIRS for path in (PROJECT_ROOT / folder).glob("*.py")]
    return sorted(paths + [PROJECT_ROOT / name for name in CHECKED_FILES])


def _dotted(node: ast.AST) -> str:
    """Nome com pontos de uma chamada ou atributo: time.sleep, self.page.goto."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_dotted(node.value)}.{node.attr}"
    return ""


def asserts_without_message(source: str) -> list[int]:
    """Linhas das `assert` sem mensagem no código-fonte dado.

    Uma `assert` dentro de uma string não conta, e uma mensagem em outra
    linha conta.
    """
    return [
        node.lineno
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Assert) and node.msg is None
    ]


def shortcuts_in(source: str, check_password: bool = True) -> list[tuple[int, str]]:
    """(linha, atalho) de cada atalho proibido no código-fonte dado."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call):
            name = _dotted(node.func)
            last = name.rsplit(".", 1)[-1]
            if name in {"time.sleep", "sleep", "asyncio.sleep"} or last == "wait_for_timeout":
                found.append((node.lineno, "espera fixa"))
            elif last == "goto" and "." in name:
                found.append((node.lineno, "page.goto direto"))
            elif name == "pytest.skip":
                found.append((node.lineno, "teste pulado"))
            elif name in {"breakpoint", "pdb.set_trace"}:
                found.append((node.lineno, "depurador"))
        elif isinstance(node, ast.Attribute) and _dotted(node).endswith(("mark.skip", "mark.skipif")):
            # Pega o decorador, o marks= do pytest.param e o pytestmark do arquivo.
            found.append((node.lineno, "teste pulado"))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name for alias in node.names]
            if "pdb" in names or getattr(node, "module", None) == "pdb":
                found.append((node.lineno, "depurador"))
        elif check_password and isinstance(node, ast.Constant) and node.value == PASSWORD:
            found.append((node.lineno, "senha fixa"))
    return sorted(found)


# --- O detector acerta? --------------------------------------------------------


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


@pytest.mark.parametrize(
    "source, expected",
    [
        pytest.param("import time\ntime.sleep(1)\n", ["espera fixa"], id="time-sleep"),
        pytest.param("from time import sleep\nsleep(1)\n", ["espera fixa"], id="sleep-importado"),
        pytest.param("page.wait_for_timeout(500)\n", ["espera fixa"], id="wait-for-timeout"),
        pytest.param("self.page.goto('/cart.html')\n", ["page.goto direto"], id="goto"),
        pytest.param("safe_goto(page, '/cart.html')\n", [], id="safe-goto-permitido"),
        pytest.param("pytest.skip('depois')\n", ["teste pulado"], id="pytest-skip"),
        pytest.param("@pytest.mark.skip\ndef test_x():\n    pass\n", ["teste pulado"], id="mark-skip"),
        pytest.param(
            "@pytest.mark.skipif(True, reason='x')\ndef test_x():\n    pass\n", ["teste pulado"], id="mark-skipif"
        ),
        pytest.param("pytest.param(1, marks=pytest.mark.skip)\n", ["teste pulado"], id="skip-no-param"),
        pytest.param("pytestmark = pytest.mark.skip\n", ["teste pulado"], id="skip-no-arquivo"),
        pytest.param("breakpoint()\n", ["depurador"], id="breakpoint"),
        pytest.param("import pdb\n", ["depurador"], id="import-pdb"),
        pytest.param(f"login(user, {PASSWORD!r})\n", ["senha fixa"], id="senha-fixa"),
        pytest.param("login(user, PASSWORD)\n", [], id="senha-pela-constante"),
        pytest.param('CODE = """\ntime.sleep(1)\npytest.skip()\n"""\n', [], id="dentro-de-string"),
        pytest.param("# time.sleep(1)\n", [], id="em-comentario"),
    ],
)
def test_detector_de_atalhos(source: str, expected: list[str]):
    assert [shortcut for _, shortcut in shortcuts_in(source)] == expected, "atalhos apontados pelo detector"


def test_senha_na_massa_de_dados_nao_conta():
    source = (PROJECT_ROOT / CREDENTIALS_FILE).read_text(encoding="utf-8")
    assert shortcuts_in(source, check_password=False) == [], "atalhos na massa de dados"


# --- A suíte segue as regras? ------------------------------------------------------


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


def test_nenhum_atalho_proibido():
    found: list[str] = []
    used = Counter()
    for path in python_files():
        relative = path.relative_to(PROJECT_ROOT).as_posix()
        for line, shortcut in shortcuts_in(path.read_text(encoding="utf-8")):
            used[relative, shortcut] += 1
            if (relative, shortcut) not in ALLOWED:
                found.append(f"{relative}:{line}: {shortcut} ({SHORTCUTS[shortcut]})")
    for (relative, shortcut), (allowed, reason) in ALLOWED.items():
        if used[relative, shortcut] != allowed:
            found.append(
                f"{relative}: {used[relative, shortcut]} uso(s) de '{shortcut}', a exceção permite "
                f"{allowed} ({reason}); se a exceção não é mais necessária, tire-a de ALLOWED"
            )
    assert not found, "atalhos proibidos:\n" + "\n".join(found)
