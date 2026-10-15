"""Gera docs/relatorio-de-bugs.pdf a partir de docs/relatorio-de-bugs.md.

Uso (na raiz do projeto, com o .venv ativo):

    python scripts/gerar_relatorio_pdf.py

Não adiciona dependências ao requirements.txt:
- o Markdown vira HTML pela API do GitHub (`gh api markdown`, modo GFM), que
  é o mesmo renderizador do site do GitHub; requer o GitHub CLI autenticado;
- o PDF é impresso pelo Chromium do Playwright, que a suíte já usa.

A primeira página é um resumo executivo montado a partir da tabela-resumo do
próprio relatório (totais por usuário e severidade, os 3 bugs mais relevantes
e links); o .md não é alterado. As screenshots citadas como evidência são
incorporadas ao PDF (data URI), e links relativos viram links absolutos para o
GitHub, para continuarem clicáveis fora do repositório.
"""

import base64
import html
import os
import re
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "docs" / "relatorio-de-bugs.md"
OUTPUT = ROOT / "docs" / "relatorio-de-bugs.pdf"
REPO_URL = "https://github.com/Arckangelo/saucedemo-playwright-python"
EVIDENCE_LINK = re.compile(r'<a href="([^"]*docs/evidencias/([^"/]+\.(?:jpg|jpeg|png)))"[^>]*>(.*?)</a>')


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def published_ref() -> str:
    """Commit já enviado ao GitHub, para os links absolutos não apontarem para algo inexistente."""
    try:
        return git("rev-parse", "@{upstream}")
    except subprocess.CalledProcessError:
        return git("rev-parse", "HEAD")


def markdown_to_html(markdown: str) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8", delete=False) as file:
        file.write(markdown)
    try:
        return subprocess.run(
            ["gh", "api", "markdown", "-f", "mode=gfm", "-F", f"text=@{file.name}"],
            check=True, capture_output=True, text=True,
        ).stdout
    finally:
        os.unlink(file.name)


# Linha da tabela-resumo: | [BUG-019](#bug-019) | Título | visual | Alta | P1 | [#20](url) |
SUMMARY_ROW = re.compile(
    r"^\| \[(BUG-\d{3})\]\(#bug-\d{3}\) \| .+? \| (\w+) \| \**(\w+)\** \| P\d \| \[#(\d+)\]\((\S+?)\) \|$", re.M
)
SEVERITIES = ["Crítica", "Alta", "Média", "Baixa"]
NO_TEST_MARKER = "**Sem teste automatizado, de propósito:**"
USERS = {
    "todos": "Todos (inclusive `standard_user`)",
    "problem": "`problem_user`",
    "error": "`error_user`",
    "visual": "`visual_user`",
}


def executive_summary(markdown: str, ref: str) -> str:
    """Página 1 do PDF, montada a partir das tabelas do relatório (nunca diverge dele)."""
    rows = SUMMARY_ROW.findall(markdown)
    if not rows:
        raise SystemExit("Tabela-resumo do relatório não encontrada; confira o formato das linhas.")
    issues = {bug: (number, url) for bug, _, _, number, url in rows}
    counts = Counter((user, severity) for _, user, severity, _, _ in rows)
    unknown = {user for _, user, _, _, _ in rows} - set(USERS) | {s for _, _, s, _, _ in rows} - set(SEVERITIES)
    if unknown:
        raise SystemExit(f"Valores fora do esperado na tabela-resumo: {unknown}")

    table = ["| Usuário | " + " | ".join(SEVERITIES) + " | Total |", "|---|" + ":-:|" * (len(SEVERITIES) + 1)]
    for key, label in USERS.items():
        cells = [counts[(key, sev)] for sev in SEVERITIES]
        table.append(f"| {label} | " + " | ".join(str(c or "–") for c in cells) + f" | **{sum(cells)}** |")
    totals = [sum(counts[(u, sev)] for u in USERS) for sev in SEVERITIES]
    table.append("| **Total** | " + " | ".join(f"**{t}**" for t in totals) + f" | **{len(rows)}** |")

    top = re.search(r"\*\*Os 3 mais relevantes:\*\*\n\n((?:\d\. .+\n?)+)", markdown)
    if not top:
        raise SystemExit("Lista 'Os 3 mais relevantes' não encontrada no relatório.")
    top3 = re.sub(
        r"^(\d\. \*\*(BUG-\d{3}):\*\*)",
        lambda m: f"{m.group(1)} ([issue #{issues[m.group(2)][0]}]({issues[m.group(2)][1]}))",
        top.group(1).strip(), flags=re.M,
    )
    date = re.search(r"^\| Data \| (.+?) \|$", markdown, re.M)
    # Bugs sem teste na suíte trazem este marcador na própria seção do relatório.
    tested = len(rows) - markdown.count(NO_TEST_MARKER)
    return "\n".join([
        "# Resumo executivo",
        "",
        f"**SauceDemo (Swag Labs)** · verificação em {date.group(1) if date else 's/d'} · "
        f"**{len(rows)} bugs confirmados**, cada um com issue no GitHub; {tested} com teste automatizado "
        "(`xfail` que avisa quando o bug for corrigido)"
        + (f" e {len(rows) - tested} sem teste, de propósito (bug de tempo, com script de reprodução)." if tested < len(rows) else "."),
        "",
        "### Bugs por usuário e severidade",
        "",
        *table,
        "",
        "### Os 3 mais relevantes",
        "",
        top3,
        "",
        "### Onde encontrar",
        "",
        f"- **Relatório completo:** nas páginas seguintes deste PDF e [no GitHub]({REPO_URL}/blob/{ref}/docs/relatorio-de-bugs.md), "
        "com passos para reproduzir e evidências de cada bug.",
        f"- **Issues:** [todos os bugs com a label `bug`]({REPO_URL}/issues?q=is%3Aissue+label%3Abug); "
        "cada linha da tabela-resumo do relatório também aponta para a sua issue.",
        "- **Testes:** `pytest -m known_bug` roda só os testes que documentam estes bugs.",
    ])


def add_heading_ids(body: str) -> str:
    """Dá aos títulos o mesmo id que o GitHub gera, para os links do sumário funcionarem no PDF."""
    seen: set[str] = set()
    first_h2 = True

    def slug(text: str) -> str:
        text = re.sub(r"<[^>]+>", "", html.unescape(text)).strip().lower()
        return re.sub(r"\s", "-", re.sub(r"[^\w\s-]", "", text))

    def add(match: re.Match) -> str:
        nonlocal first_h2
        level, attrs, text = match.groups()
        anchor = slug(text)
        if anchor in seen:
            return match.group(0)
        seen.add(anchor)
        css_class = ""
        if level == "2" and first_h2:
            css_class, first_h2 = ' class="first"', False
        return f'<h{level} id="user-content-{anchor}"{css_class}{attrs}>{text}</h{level}>'

    return re.sub(r"<h([1-4])([^>]*)>(.*?)</h\1>", add, body)


def fix_links(body: str, ref: str) -> str:
    # O GitHub prefixa os ids com "user-content-"; ajusta as âncoras internas.
    # Fragmentos com acento chegam codificados (%C3%A9); a comparação usa o texto decodificado.
    ids = set(re.findall(r'id="(user-content-[^"]+)"', body))
    body = re.sub(
        r'href="#([^"]+)"',
        lambda m: f'href="#user-content-{m.group(1)}"' if f"user-content-{unquote(m.group(1))}" in ids else m.group(0),
        body,
    )
    # Células que contêm só um ID curto (S-01, RN-05) não quebram no hífen.
    body = re.sub(r"<td>([A-Z]{1,3}-\d{2,3})</td>", r'<td style="white-space: nowrap">\1</td>', body)
    # Links relativos a outros arquivos do repositório viram absolutos.
    return re.sub(
        r'href="(?!https?:|#|mailto:)([^"]+)"',
        lambda m: f'href="{REPO_URL}/blob/{ref}/docs/{m.group(1)}"',
        body,
    )


def embed_evidence(body: str) -> str:
    """Coloca cada screenshot citada logo após o parágrafo que a cita (uma vez cada)."""
    embedded: set[str] = set()

    def figures_for(block: str) -> str:
        figures = []
        for _, filename, label in EVIDENCE_LINK.findall(block):
            image = ROOT / "docs" / "evidencias" / filename
            if filename in embedded or not image.exists():
                continue
            embedded.add(filename)
            data = base64.b64encode(image.read_bytes()).decode()
            caption = html.escape(re.sub(r"<[^>]+>", "", html.unescape(label)))
            figures.append(
                f'<figure><img src="data:image/jpeg;base64,{data}" alt="{caption}">'
                f"<figcaption>Evidência: {caption}</figcaption></figure>"
            )
        return "".join(figures)

    return re.sub(r"(<p>.*?</p>)", lambda m: m.group(1) + figures_for(m.group(1)), body, flags=re.S)


CSS = """
@page { size: A4; margin: 16mm 14mm 18mm 14mm; }
* { box-sizing: border-box; }
body { font-family: "DejaVu Sans", "Liberation Sans", Arial, sans-serif; font-size: 9.5pt;
       line-height: 1.45; color: #1f2328; }
h1 { font-size: 20pt; border-bottom: 2px solid #d0d7de; padding-bottom: 4pt; }
h2 { font-size: 14pt; border-bottom: 1px solid #d0d7de; padding-bottom: 3pt; margin-top: 18pt;
     break-before: page; }
h2.first { break-before: auto; }
h3 { font-size: 11.5pt; margin-top: 14pt; }
h2, h3, h4 { break-after: avoid; }
a { color: #0969da; text-decoration: none; word-break: break-word; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 8.5pt; background: #f6f8fa;
       padding: 0 2pt; border-radius: 3px; word-break: break-word; }
pre { white-space: pre-wrap; background: #f6f8fa; padding: 6pt; border-radius: 4px; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0; font-size: 8.5pt;
        table-layout: auto; }
th, td { border: 1px solid #d0d7de; padding: 3pt 5pt; vertical-align: top;
         overflow-wrap: break-word; }
/* Títulos de coluna e IDs (BUG-001) não quebram; só código longo (caminho de teste) quebra em qualquer ponto. */
th, td:first-child a { white-space: nowrap; }
td code { overflow-wrap: anywhere; word-break: break-all; }
th { background: #f6f8fa; }
tr { break-inside: avoid; }
figure { margin: 6pt 0 10pt; break-inside: avoid; text-align: center; }
figure img { max-width: 100%; max-height: 105mm; border: 1px solid #d0d7de; }
figcaption { font-size: 8pt; color: #59636e; margin-top: 2pt; }
.anchor, .octicon { display: none; }
.executive { break-after: page; }
.executive h1 { font-size: 22pt; }
.executive table { font-size: 10pt; }
.executive td:not(:first-child), .executive th:not(:first-child) { text-align: center; }
"""


def main():
    ref = published_ref()
    markdown = SOURCE.read_text(encoding="utf-8")
    summary_html = markdown_to_html(executive_summary(markdown, ref))
    combined = f'<section class="executive">{summary_html}</section>{markdown_to_html(markdown)}'
    body = embed_evidence(fix_links(add_heading_ids(combined), ref))
    document = (
        f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
        f"<title>Relatório de bugs: SauceDemo</title><style>{CSS}</style></head>"
        f"<body>{body}</body></html>"
    )
    footer = (
        '<div style="font-size:7pt; color:#59636e; width:100%; padding:0 14mm; display:flex; '
        'justify-content:space-between;"><span>Relatório de bugs: SauceDemo</span>'
        '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>'
    )
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_content(document, wait_until="load")
        page.pdf(
            path=str(OUTPUT), format="A4", print_background=True, display_header_footer=True,
            header_template="<span></span>", footer_template=footer,
            margin={"top": "16mm", "bottom": "18mm", "left": "14mm", "right": "14mm"},
        )
        browser.close()
    print(f"PDF gerado: {OUTPUT.relative_to(ROOT)} (links absolutos no commit {ref[:7]})")


if __name__ == "__main__":
    main()
