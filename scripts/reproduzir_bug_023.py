"""Reprodução controlada do BUG-023: menu lateral abre invisível (condição de corrida).

O QUE FAZ
    Abre o inventário com o standard_user, deixa a CPU do navegador N vezes mais
    lenta (CDP: Emulation.setCPUThrottlingRate) e clica no botão do menu num
    atraso exato depois de a página aparecer. Depois confere se o menu ficou
    visível. Um grupo de controle repete os mesmos atrasos com a CPU normal.

POR QUE FICA FORA DA SUÍTE
    É um bug de tempo: o resultado depende da velocidade da máquina. Um
    xfail(strict=True) passaria por acaso em parte das execuções e deixaria o CI
    instável. Este script é para reproduzir e investigar sob demanda.

CAUSA (react-burger-menu)
    Ao carregar a página (e ao fechar o menu), o componente agenda um timer de
    500 ms que esconde o menu fechado (atributo `hidden`). O clique em "Open Menu"
    remove o `hidden` na hora, mas só marca o menu como aberto numa tarefa
    seguinte, que é quando o timer é cancelado. Se a máquina está lenta e o clique
    cai pouco antes dos 500 ms, o timer dispara no meio desse caminho: o menu fica
    "aberto" para o componente (aria-hidden="false") e invisível na tela
    (hidden="true").

COMO USAR (na raiz do projeto, com o .venv ativo)
    python scripts/reproduzir_bug_023.py
    python scripts/reproduzir_bug_023.py --tentativas 5 --cpu 30
    python scripts/reproduzir_bug_023.py --saida docs/evidencias/bug-023-reproducao.json

    A janela de atrasos em que a falha aparece depende da máquina: numa CPU
    mais rápida, aumente --cpu.

As esperas fixas (wait_for_timeout) são intencionais aqui: o objetivo é
controlar o instante exato do clique, o que a suíte nunca faz.
"""

import argparse
import json
import sys
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

BASE_URL = "https://www.saucedemo.com"
DELAYS_MS = list(range(300, 541, 30))  # instante do clique após a página aparecer
OBSERVE_MS = 1_500  # tempo para o menu terminar de abrir antes de conferir


def attempt(browser, cpu_rate: int, delay_ms: int) -> dict:
    context = browser.new_context(base_url=BASE_URL)
    context.add_cookies([{"name": "session-username", "value": "standard_user", "url": BASE_URL}])
    page = context.new_page()
    cdp = context.new_cdp_session(page)
    try:
        page.goto("/inventory.html")
        page.wait_for_selector('[data-test="title"]')
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": cpu_rate})
        page.wait_for_timeout(delay_ms)
        # dispatch_event dispara o clique no instante exato; click() esperaria as
        # checagens de ação e deslocaria o momento do clique.
        page.locator("#react-burger-menu-btn").dispatch_event("click")
        page.wait_for_timeout(OBSERVE_MS)
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": 1})
        wrap = page.locator(".bm-menu-wrap")
        return {
            "cpu": cpu_rate,
            "atraso_ms": delay_ms,
            "menu_visivel": page.locator('[data-test="reset-sidebar-link"]').is_visible(),
            "aria_hidden": wrap.get_attribute("aria-hidden"),
            "hidden": wrap.get_attribute("hidden"),
        }
    finally:
        context.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tentativas", type=int, default=3, help="tentativas por atraso e por grupo (padrão: 3)")
    parser.add_argument("--cpu", type=int, default=30, help="fator de lentidão da CPU no grupo de teste (padrão: 30)")
    parser.add_argument("--saida", help="arquivo JSON para salvar o resultado (opcional)")
    args = parser.parse_args()

    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for cpu_rate in (args.cpu, 1):
            for delay in DELAYS_MS:
                for _ in range(args.tentativas):
                    results.append(attempt(browser, cpu_rate, delay))
        browser.close()

    print(f"{'CPU':>4} {'atraso':>7}  invisível/tentativas")
    summary = {}
    for cpu_rate in (args.cpu, 1):
        for delay in DELAYS_MS:
            group = [r for r in results if r["cpu"] == cpu_rate and r["atraso_ms"] == delay]
            stuck = sum(not r["menu_visivel"] for r in group)
            print(f"{cpu_rate:>3}x {delay:>5}ms  {stuck}/{len(group)}")
        group = [r for r in results if r["cpu"] == cpu_rate]
        stuck = [r for r in group if not r["menu_visivel"]]
        summary[f"cpu_{cpu_rate}x"] = {
            "menu_invisivel": len(stuck),
            "tentativas": len(group),
            "estados_quando_invisivel": sorted({(r["aria_hidden"], r["hidden"]) for r in stuck}),
            "atrasos_com_falha_ms": sorted({r["atraso_ms"] for r in stuck}),
        }
    for name, data in summary.items():
        print(f"{name}: menu invisível em {data['menu_invisivel']} de {data['tentativas']} tentativas"
              f" | atrasos com falha: {data['atrasos_com_falha_ms']}"
              f" | (aria-hidden, hidden): {data['estados_quando_invisivel']}")

    if args.saida:
        with open(args.saida, "w", encoding="utf-8") as file:
            json.dump(
                {
                    "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "protocolo": {
                        "usuario": "standard_user",
                        "atrasos_ms": DELAYS_MS,
                        "tentativas_por_atraso": args.tentativas,
                        "cpu_teste": f"{args.cpu}x",
                        "cpu_controle": "1x",
                        "observacao_ms": OBSERVE_MS,
                    },
                    "resumo": summary,
                    "tentativas": results,
                },
                file, indent=2, ensure_ascii=False,
            )
        print(f"Resultado salvo em {args.saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
