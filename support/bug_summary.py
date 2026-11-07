"""Resumo dos bugs conhecidos, teste a teste, na página da execução do CI.

Um "todos os xfail passaram" não diz o que aconteceu com cada bug: um XFAIL
de um bug e o XPASS de outro aparecem misturados no relatório. Este plugin
escreve, no fim da execução, uma tabela com cada teste de bug conhecido e o
que aconteceu com ele:

- reproduz: o teste deu XFAIL, com a exceção própria do bug;
- CORRIGIDO?: o teste passou (XPASS). Confirme no site e tire o xfail;
- falha diferente da do bug: seletor, login, tempo... (não confere o bug);
- erro na preparação ou no encerramento: ex.: xfail fora da regra 4;
- inconclusivo: o próprio teste se pulou (ex.: BUG-006, telemetria sem
  resposta);
- SITE INDISPONÍVEL: o site caiu (support/site_guard.py).

A tabela vai para o arquivo da variável GITHUB_STEP_SUMMARY, que o GitHub
Actions mostra na página da execução, logo depois da contagem geral escrita
pelo conftest.py. Fora do CI (sem a variável), nada é
escrito. Com o pytest-xdist, os resultados chegam ao processo principal pelo
pytest_runtest_logreport, e só ele escreve.

É carregado como plugin pelo pytest.ini (`-p support.bug_summary`).
"""

import os
import re
from collections import Counter
from pathlib import Path

import pytest

from support.known_bugs import REASON_PATTERN
from support.site_guard import is_unavailable_report

SUMMARY_ENV = "GITHUB_STEP_SUMMARY"
# Vai em user_properties, que o xdist leva do processo do teste ao principal.
_PROPERTY = "known_bug_reason"
_XDIST_HEADER = re.compile(r"^\[gw\d+\] ")

# Resultado -> (nome na contagem, texto na tabela), na ordem em que aparecem na contagem.
REPRODUCES, FIXED, OTHER_FAILURE = "reproduz", "corrigido", "outra falha"
SETUP_ERROR, TEARDOWN_ERROR = "erro na preparação", "erro no encerramento"
INCONCLUSIVE, UNAVAILABLE, PASSED = "inconclusivo", "site indisponível", "passou"
LABELS = {
    REPRODUCES: ("reproduz", "reproduz"),
    FIXED: ("**CORRIGIDO?**", "**CORRIGIDO?** o teste passou: confirme no site e tire o xfail"),
    OTHER_FAILURE: ("**falha diferente da do bug**", "**falha diferente da do bug**"),
    SETUP_ERROR: ("**erro na preparação**", "**erro na preparação**"),
    TEARDOWN_ERROR: ("**erro no encerramento**", "**erro no encerramento**"),
    INCONCLUSIVE: ("inconclusivo", "inconclusivo"),
    UNAVAILABLE: ("SITE INDISPONÍVEL", "SITE INDISPONÍVEL"),
    PASSED: ("passou", "passou"),
}
# Resultados da execução que um erro no encerramento pode substituir.
_GOOD = {None, REPRODUCES, PASSED}


def pytest_collection_modifyitems(items):
    for item in items:
        for mark in item.iter_markers("xfail"):
            reason = str(mark.kwargs.get("reason", ""))
            if reason.startswith("BUG-"):
                item.user_properties.append((_PROPERTY, reason))
                break


def _reason(report) -> str | None:
    return next((value for name, value in report.user_properties if name == _PROPERTY), None)


def _lines(report) -> list[str]:
    """Linhas do motivo, sem as vazias e sem a linha "[gw1] linux -- Python ..." que o xdist acrescenta."""
    longrepr = report.longrepr
    text = str(longrepr[2]) if isinstance(longrepr, tuple) and len(longrepr) == 3 else report.longreprtext
    return [line.strip() for line in text.splitlines() if line.strip() and not _XDIST_HEADER.match(line)]


def _detail(report) -> str:
    """Mensagem curta do motivo, para caber numa célula da tabela."""
    crash = getattr(report.longrepr, "reprcrash", None)
    if crash is not None:  # exceção: a mensagem dela, e não a primeira linha do código
        line = crash.message.splitlines()[0] if crash.message else ""
    else:
        lines = _lines(report)
        line = lines[0] if lines else ""
        if line.endswith(":") and len(lines) > 1:  # "xfail fora da regra ...:" e, na linha seguinte, o problema
            line = f"{line} {lines[1]}"
    for prefix in ("Skipped: ", "SITE INDISPONÍVEL: "):
        line = line.removeprefix(prefix)
    return line[:200]


def outcome_of(report) -> tuple[str, str] | None:
    """(resultado, detalhe) que este relatório decide para o teste, ou None se não decide nada.

    Setup e encerramento só decidem quando dão errado; a execução sempre decide.
    """
    if is_unavailable_report(report):
        return UNAVAILABLE, _detail(report)
    if report.when == "setup" and report.failed:
        return SETUP_ERROR, _detail(report)
    if report.when == "teardown" and report.failed:
        return TEARDOWN_ERROR, _detail(report)
    if report.when != "call":
        if report.skipped:  # pulado no setup (ex.: skip dentro de uma fixture)
            return INCONCLUSIVE, _detail(report)
        return None
    if report.skipped and hasattr(report, "wasxfail"):
        return REPRODUCES, ""
    if report.skipped:
        return INCONCLUSIVE, _detail(report)
    if report.failed and next(iter(_lines(report)), "").startswith("[XPASS(strict)]"):
        return FIXED, ""
    if report.failed:
        return OTHER_FAILURE, _detail(report)
    if hasattr(report, "wasxfail"):  # XPASS não estrito; a regra 4 não deixa chegar aqui
        return FIXED, ""
    return PASSED, ""


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


class _Summary:
    def __init__(self, path: Path):
        self.path = path
        self.results: dict[str, dict] = {}

    def pytest_runtest_logreport(self, report):
        reason = _reason(report)
        if reason is None:
            return
        outcome = outcome_of(report)
        entry = self.results.setdefault(report.nodeid, {"reason": reason, "outcome": None, "detail": ""})
        # O encerramento não apaga um resultado ruim da execução, só um bom.
        if outcome and not (report.when == "teardown" and entry["outcome"] not in _GOOD):
            entry["outcome"], entry["detail"] = outcome

    # trylast: a tabela vem depois da contagem geral que o conftest.py escreve.
    @pytest.hookimpl(trylast=True)
    def pytest_terminal_summary(self):
        with self.path.open("a", encoding="utf-8") as summary:
            summary.write(render(self.results, _issue_url()))


def _issue_url() -> str | None:
    server, repository = os.environ.get("GITHUB_SERVER_URL"), os.environ.get("GITHUB_REPOSITORY")
    return f"{server}/{repository}/issues/" if server and repository else None


def render(results: dict[str, dict], issue_url: str | None = None) -> str:
    """Markdown do resumo: contagem, avisos e uma linha por teste, em ordem de bug."""
    lines = ["### Bugs conhecidos, teste a teste", ""]
    if not results:
        lines += ["Os testes de bugs conhecidos não rodaram nesta execução.", ""]
        return "\n".join(lines)
    counts = Counter(entry["outcome"] or OTHER_FAILURE for entry in results.values())
    lines.append(
        f"{len(results)} teste(s) de bugs conhecidos · "
        + " · ".join(f"{name}: {counts[outcome]}" for outcome, (name, _) in LABELS.items() if counts[outcome])
    )
    if counts[FIXED]:
        lines += ["", f"> **Atenção:** {counts[FIXED]} bug(s) parece(m) corrigido(s): o teste passou."]
    problems = sum(counts[o] for o in (OTHER_FAILURE, SETUP_ERROR, TEARDOWN_ERROR))
    if problems:
        lines += ["", f"> **Atenção:** {problems} teste(s) de bug não chegaram a conferir o bug (falha ou erro)."]
    lines += ["", "| Bug | Issue | Teste | Resultado |", "|-----|:-----:|-------|-----------|"]

    def sort_key(item):
        nodeid, entry = item
        return entry["reason"][:7], nodeid

    for nodeid, entry in sorted(results.items(), key=sort_key):
        match = REASON_PATTERN.match(entry["reason"])
        bug_id, issue = match.groups() if match else (entry["reason"][:7], "")
        issue_cell = f"[#{issue}]({issue_url}{issue})" if issue and issue_url else (f"#{issue}" if issue else "")
        result = LABELS[entry["outcome"] or OTHER_FAILURE][1] + (f": {entry['detail']}" if entry["detail"] else "")
        lines.append(f"| {bug_id} | {issue_cell} | `{_cell(nodeid.removeprefix('tests/'))}` | {_cell(result)} |")
    lines.append("")
    return "\n".join(lines)


def pytest_configure(config):
    path = os.environ.get(SUMMARY_ENV)
    if path and not hasattr(config, "workerinput"):
        config.pluginmanager.register(_Summary(Path(path)), "bug_summary_writer")
