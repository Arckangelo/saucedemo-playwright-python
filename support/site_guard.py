"""Proteção contra instabilidade do site, num ponto só.

Site fora do ar não é resultado de teste: não aprova nada e não prova bug.
Este módulo faz quatro coisas:

- `safe_goto` abre uma página e repete só o CARREGAMENTO (nunca o teste)
  quando o site responde com um status de indisponibilidade ou não responde.
  A página real é reconhecida pelo título "Swag Labs", não pelo status HTTP:
  as rotas internas respondem 404 mesmo funcionando (BUG-005).
- O hook de relatório transforma a exceção `SiteUnavailable` num resultado
  próprio, "SITE INDISPONÍVEL" (um skip com esse motivo), seja qual for o
  xfail do teste.
- Quando um teste falha (ou um bug conhecido "reproduz"), o site é
  conferido de novo. Se estiver fora do ar, o resultado também vira
  "SITE INDISPONÍVEL": cobre a queda que acontece no meio do teste, depois
  de um clique ou de um reload, onde safe_goto não age. O teste não é
  repetido.
- Disjuntor: depois de `BREAKER_THRESHOLD` quedas, os testes seguintes nem
  começam. Com pytest-xdist, os processos compartilham a contagem por uma
  pasta temporária criada pelo processo principal.

Qualquer "SITE INDISPONÍVEL" faz a execução terminar com código 2
(interrompida): o CI nunca fica verde sem ter testado.

É carregado como plugin pelo pytest.ini (`-p support.site_guard`).
"""

import shutil
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, Response
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

# Título da página real do site (o <title> do HTML, antes de qualquer JavaScript).
REAL_PAGE_TITLE = "Swag Labs"

# Respostas de site sobrecarregado ou fora do ar: limite de requisições (429),
# gateway e proxy (502-504) e erros de borda da Cloudflare (520-524).
UNAVAILABLE_STATUSES = frozenset({429, 502, 503, 504, 520, 521, 522, 523, 524})

GOTO_ATTEMPTS = 3
# Pausa antes da 2ª e da 3ª tentativa. É a única espera por tempo da suíte, e
# fica fora dos testes: dá ao site um instante para voltar antes de desistir.
GOTO_BACKOFF_S = (1, 3)

SITE_CHECK_TIMEOUT_S = 15

BREAKER_THRESHOLD = 2

REASON_PREFIX = "SITE INDISPONÍVEL"

_GUARD_DIR = "site_guard_dir"
_dir_key = pytest.StashKey[Path]()
_owner_key = pytest.StashKey[bool]()


class SiteUnavailable(Exception):
    """O site não estava utilizável: o resultado do teste é inconclusivo."""


def _is_network_error(error: PlaywrightError) -> bool:
    """Erro de rede ou de tempo na navegação, e não um defeito do teste.

    ERR_ABORTED fica de fora: acontece quando outra navegação interrompe a
    atual, o que é comportamento da página, não queda do site.
    """
    if isinstance(error, PlaywrightTimeoutError):
        return True
    message = str(error)
    return ("net::ERR_" in message and "ERR_ABORTED" not in message) or "NS_ERROR_" in message


def check_status(status: int, url: str) -> None:
    """Lança SiteUnavailable se o status indica site fora do ar.

    Para respostas lidas fora de safe_goto (ex.: page.request.get), que não
    têm título para conferir.
    """
    if status in UNAVAILABLE_STATUSES:
        raise SiteUnavailable(f"{url} respondeu HTTP {status}")


def safe_goto(page: Page, url: str, backoff_s: tuple[float, ...] = GOTO_BACKOFF_S) -> Response | None:
    """page.goto(url) que repete o carregamento se o site estiver fora do ar.

    Tenta até GOTO_ATTEMPTS vezes. Se nenhuma tentativa chegar à página real,
    lança SiteUnavailable. Um status de erro que não é de indisponibilidade
    (ex.: o 404 das rotas internas) não conta, desde que a página seja a real.
    """
    reason = ""
    for attempt in range(GOTO_ATTEMPTS):
        if attempt:
            time.sleep(backoff_s[min(attempt, len(backoff_s)) - 1])
        try:
            response = page.goto(url)
        except PlaywrightError as error:
            if not _is_network_error(error):
                raise
            reason = f"não respondeu ({str(error).splitlines()[0]})"
            continue
        status = response.status if response else None
        if status in UNAVAILABLE_STATUSES:
            reason = f"respondeu HTTP {status}"
            continue
        title = page.title()
        if title != REAL_PAGE_TITLE:
            reason = f"respondeu HTTP {status} com uma página que não é a do site (título {title!r})"
            continue
        return response
    raise SiteUnavailable(f"{url} {reason}, em {GOTO_ATTEMPTS} tentativas")


def site_unavailable_reason(base_url: str) -> str | None:
    """Motivo pelo qual o site não está utilizável, ou None se estiver.

    Uma requisição HTTP simples, sem navegador: serve para a checagem do
    início da execução e para conferir o site depois de uma falha.
    """
    request = urllib.request.Request(base_url, headers={"User-Agent": "saucedemo-e2e-healthcheck"})
    try:
        with urllib.request.urlopen(request, timeout=SITE_CHECK_TIMEOUT_S) as response:
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        return f"respondeu HTTP {error.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return f"não respondeu ({getattr(error, 'reason', error)})"
    # Uma página de erro ou de desafio (ex.: Cloudflare) também responde 200.
    if REAL_PAGE_TITLE not in body:
        return "respondeu, mas não com a página do Swag Labs"
    return None


def is_unavailable_report(report) -> bool:
    """O resultado é um "SITE INDISPONÍVEL" (vale também para relatórios vindos do xdist)."""
    longrepr = getattr(report, "longrepr", None)
    return (
        report.skipped
        and isinstance(longrepr, tuple)
        and len(longrepr) == 3
        and str(longrepr[2]).startswith(REASON_PREFIX)
    )


# --- Disjuntor ---------------------------------------------------------------


def _breaker_open(config) -> bool:
    return len(list(config.stash[_dir_key].iterdir())) >= BREAKER_THRESHOLD


def _record_outage(config) -> None:
    # Um arquivo por queda: criar arquivos com nomes únicos não tem condição de
    # corrida entre processos, ao contrário de um contador num arquivo só.
    (config.stash[_dir_key] / uuid.uuid4().hex).touch()


class _XdistHooks:
    """Hook que só existe com o pytest-xdist instalado."""

    @staticmethod
    def pytest_configure_node(node):
        node.workerinput[_GUARD_DIR] = str(node.config.stash[_dir_key])


def pytest_configure(config):
    workerinput = getattr(config, "workerinput", None)
    if workerinput and _GUARD_DIR in workerinput:
        config.stash[_dir_key] = Path(workerinput[_GUARD_DIR])
    else:
        config.stash[_dir_key] = Path(tempfile.mkdtemp(prefix="site-guard-"))
        config.stash[_owner_key] = True
    if config.pluginmanager.hasplugin("xdist"):
        config.pluginmanager.register(_XdistHooks())
    if not workerinput:
        config.pluginmanager.register(_Tracker())


def pytest_unconfigure(config):
    if config.stash.get(_owner_key, False):
        shutil.rmtree(config.stash[_dir_key], ignore_errors=True)


def pytest_runtest_setup(item):
    if _breaker_open(item.config):
        raise SiteUnavailable(
            f"disjuntor aberto depois de {BREAKER_THRESHOLD} quedas do site; o teste não foi executado"
        )


# --- Resultado ---------------------------------------------------------------


def _base_url(config) -> str | None:
    try:
        return config.getoption("base_url", None) or config.getini("base_url") or None
    except ValueError:  # sem o plugin pytest-base-url, a opção não existe
        return None


def _outage_after_failure(item, call, report) -> str | None:
    """Se o teste falhou ou deu XFAIL e o site está fora do ar agora, o motivo.

    Uma falha comum com o site no ar continua falha. O XFAIL também é
    conferido: um bug conhecido que "reproduz" porque a página não carregou
    seria um resultado falso.
    """
    xfailed = report.skipped and hasattr(report, "wasxfail")
    if not (report.failed or xfailed):
        return None
    base_url = _base_url(item.config)
    if not base_url:
        return None
    reason = site_unavailable_reason(base_url)
    if reason is None:
        return None
    outcome = "deu XFAIL" if xfailed else "falhou"
    if call.excinfo is not None:
        original = call.excinfo.exconly()
    else:  # ex.: XPASS estrito, que falha sem exceção
        original = report.longreprtext
    original = (original.strip().splitlines() or [""])[0][:300]
    return f"o teste {outcome} e, logo depois, {base_url} {reason}. Falha original: {original}"


def _mark_unavailable(item, report, message: str):
    path, line, _ = item.reportinfo()
    report.outcome = "skipped"
    report.longrepr = (str(path), (line or 0) + 1, f"{REASON_PREFIX}: {message}")
    if hasattr(report, "wasxfail"):
        del report.wasxfail


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    """Transforma queda do site em "SITE INDISPONÍVEL".

    tryfirst num wrapper o deixa por fora dos outros: ele vê o resultado final,
    depois que o xfail já foi avaliado, e o substitui.
    """
    report = yield
    if call.excinfo is not None and call.excinfo.errisinstance(SiteUnavailable):
        message = str(call.excinfo.value)
        if "disjuntor aberto" not in message:
            _record_outage(item.config)
        _mark_unavailable(item, report, message)
        return report
    message = _outage_after_failure(item, call, report)
    if message:
        _record_outage(item.config)
        _mark_unavailable(item, report, message)
    return report


class _Tracker:
    """Conta os "SITE INDISPONÍVEL" no processo principal e ajusta o código de saída.

    Com o xdist, os relatórios dos processos chegam aqui pelo
    pytest_runtest_logreport do processo principal.
    """

    def __init__(self):
        self.reports = []

    def pytest_runtest_logreport(self, report):
        if is_unavailable_report(report):
            self.reports.append(report)

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self, session):
        if self.reports:
            session.exitstatus = pytest.ExitCode.INTERRUPTED

    def pytest_terminal_summary(self, terminalreporter):
        if not self.reports:
            return
        terminalreporter.write_sep(
            "=",
            f"{REASON_PREFIX} em {len(self.reports)} teste(s): resultado inconclusivo, rode de novo "
            "quando o site voltar (código de saída 2)",
            red=True,
            bold=True,
        )
        for report in self.reports:
            reason = str(report.longrepr[2])[len(REASON_PREFIX) + 2 :]
            terminalreporter.write_line(f"{report.nodeid}: {reason}")


def pytest_report_teststatus(report, config):
    if is_unavailable_report(report):
        return "site indisponível", "U", "SITE INDISPONÍVEL"
    return None
