"""Gera docs/relatorio-de-bugs.pdf a partir de docs/relatorio-de-bugs.md.

Uso (na raiz do projeto, com o .venv ativo):

    python scripts/gerar_relatorio_pdf.py

Não adiciona dependências ao requirements.txt:
- o Markdown vira HTML pela API do GitHub (`gh api markdown`, modo GFM), que
  é o mesmo renderizador do site do GitHub; requer o GitHub CLI autenticado;
- o PDF é impresso pelo Chromium do Playwright, que a suíte já usa.

As screenshots citadas como evidência são incorporadas ao PDF (data URI), e
links relativos viram links absolutos para o GitHub, para continuarem
clicáveis fora do repositório.
"""

import base64
import html
import re
import subprocess
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


def markdown_to_html(markdown_path: Path) -> str:
    return subprocess.run(
        ["gh", "api", "markdown", "-f", "mode=gfm", "-F", f"text=@{markdown_path}"],
        check=True, capture_output=True, text=True,
    ).stdout


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
"""


def main():
    ref = published_ref()
    body = embed_evidence(fix_links(add_heading_ids(markdown_to_html(SOURCE)), ref))
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
