"""Regra dos bugs conhecidos (regra 4 do CLAUDE.md), conferida automaticamente.

Todo bug conhecido é um `xfail` que descreve o comportamento correto. Para o
xfail não esconder outra falha nem um resultado falso, ele precisa de:

- `strict=True`: se o bug for corrigido, o XPASS vira falha e avisa;
- `raises=` com a exceção própria do bug (subclasse de AssertionError, mas
  não a própria AssertionError): uma falha de login, seletor ou tempo
  continua aparecendo como falha, em vez de ser contada como "o bug reproduz";
- motivo no formato `BUG-NNN (#issue): ...`, com o ID e a issue que constam
  na tabela do BUGS.md.

Um xfail fora da regra faz o teste terminar como ERRO no setup, com o motivo,
sem ser executado: o próprio xfail não consegue esconder esse erro. (Parar a
coleta inteira seria mais simples, mas com o pytest-xdist vira um erro
interno sem mensagem.)

Este plugin também aplica o marker `known_bug` a todo xfail com "BUG-", para
`pytest -m known_bug` funcionar sem marcar à mão.

É carregado como plugin pelo pytest.ini (`-p support.known_bugs`).
"""

import re
from pathlib import Path

import pytest

REASON_PATTERN = re.compile(r"^(BUG-\d{3}) \(#(\d+)\): \S")
BUGS_FILE = "BUGS.md"
# Linha da tabela do BUGS.md: | [BUG-005](...) | ... | [#6](...) |
_TABLE_ROW = re.compile(r"^\| \[(BUG-\d{3})\].*\[#(\d+)\]\(", re.MULTILINE)

_problems_key = pytest.StashKey[list[str]]()


def _documented_bugs(config) -> dict[str, str] | None:
    """ID -> issue, lidos da tabela do BUGS.md; None se o arquivo não existe."""
    path = Path(config.rootpath) / BUGS_FILE
    if not path.is_file():
        return None
    return dict(_TABLE_ROW.findall(path.read_text(encoding="utf-8")))


def _is_specific(raises) -> bool:
    classes = raises if isinstance(raises, tuple) else (raises,)
    return all(
        isinstance(cls, type) and issubclass(cls, AssertionError) and cls is not AssertionError
        for cls in classes
    )


def xfail_problems(mark, strict_default: bool, documented: dict[str, str] | None) -> list[str]:
    """O que está fora da regra num marker xfail (lista vazia se está certo)."""
    problems = []
    if mark.kwargs.get("strict", strict_default) is not True:
        problems.append("falta strict=True (um XPASS precisa virar falha)")
    raises = mark.kwargs.get("raises")
    if raises is None:
        problems.append("falta raises= com a exceção própria do bug")
    elif not _is_specific(raises):
        problems.append(
            f"raises={getattr(raises, '__name__', raises)} não é específico: use uma subclasse "
            "própria de AssertionError"
        )
    reason = str(mark.kwargs.get("reason", ""))
    match = REASON_PATTERN.match(reason)
    if not match:
        problems.append(f'motivo fora do formato "BUG-NNN (#issue): ...": {reason!r}')
    elif documented is not None:
        bug_id, issue = match.groups()
        if bug_id not in documented:
            problems.append(f"{bug_id} não está na tabela do {BUGS_FILE}")
        elif documented[bug_id] != issue:
            problems.append(f"{bug_id} é a issue #{documented[bug_id]} no {BUGS_FILE}, não #{issue}")
    return problems


def pytest_collection_modifyitems(config, items):
    strict_default = config.getini("xfail_strict")
    documented = _documented_bugs(config)
    for item in items:
        problems = []
        for mark in item.iter_markers("xfail"):
            problems += xfail_problems(mark, strict_default, documented)
            if str(mark.kwargs.get("reason", "")).startswith("BUG-"):
                item.add_marker(pytest.mark.known_bug)
        if problems:
            item.stash[_problems_key] = problems


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    """Um xfail fora da regra vira ERRO no setup, e o teste não é executado.

    tryfirst num wrapper o deixa por fora dos outros: ele vê o resultado depois
    que o xfail já foi avaliado, e o substitui. Com o setup marcado como falha,
    o pytest não executa o corpo do teste.
    """
    report = yield
    problems = item.stash.get(_problems_key, None)
    if report.when == "setup" and problems:
        report.outcome = "failed"
        report.longrepr = "xfail fora da regra dos bugs conhecidos (CLAUDE.md, regra 4):\n" + "\n".join(
            f"- {problem}" for problem in problems
        )
    return report
