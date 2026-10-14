"""Roda o pip-audit e falha só em vulnerabilidades de severidade alta ou crítica.

O pip-audit não tem filtro de severidade: ele falha em qualquer vulnerabilidade
conhecida. Este script usa a saída JSON dele e consulta a severidade de cada
achado na base pública OSV (https://osv.dev), que agrega os alertas do GitHub
(GHSA) e do PyPI (PYSEC).

Regra de saída:
- 1 se houver alguma vulnerabilidade HIGH ou CRITICAL;
- 1 também se a severidade não puder ser determinada (na dúvida, falha);
- 0 caso contrário (vulnerabilidades MODERATE/LOW são apenas listadas).

Uso: python .github/scripts/pip_audit_severidade.py requirements.txt
"""

import json
import subprocess
import sys
import urllib.request
from functools import cache

BLOQUEANTES = {"HIGH", "CRITICAL"}
OSV_URL = "https://api.osv.dev/v1/vulns/{}"


@cache
def severidade(vuln_id: str) -> str | None:
    """Severidade de um ID (GHSA/PYSEC/CVE) segundo o OSV, ou None se não houver."""
    with urllib.request.urlopen(OSV_URL.format(vuln_id), timeout=30) as resposta:
        dados = json.load(resposta)
    nivel = dados.get("database_specific", {}).get("severity")
    return nivel.upper() if nivel else None


def severidade_do_achado(vuln: dict) -> str | None:
    # o alias GHSA costuma trazer a classificação do GitHub Advisory Database
    ids = sorted([vuln["id"], *vuln.get("aliases", [])], key=lambda i: not i.startswith("GHSA-"))
    for vuln_id in ids:
        try:
            nivel = severidade(vuln_id)
        except OSError:
            continue
        if nivel:
            return nivel
    return None


def main() -> int:
    requirements = sys.argv[1] if len(sys.argv) > 1 else "requirements.txt"
    execucao = subprocess.run(
        ["pip-audit", "-r", requirements, "-f", "json", "--progress-spinner", "off"],
        capture_output=True,
        text=True,
    )
    # pip-audit sai com 1 quando acha vulnerabilidades; outros códigos são erro de execução
    if execucao.returncode not in (0, 1):
        print(execucao.stderr, file=sys.stderr)
        return execucao.returncode

    relatorio = json.loads(execucao.stdout)
    # o JSON pode repetir a mesma dependência; cada (pacote, versão, ID) conta uma vez
    unicos = {
        (dep["name"], dep["version"], vuln["id"]): vuln
        for dep in relatorio.get("dependencies", [])
        for vuln in dep.get("vulns", [])
    }
    achados = [(nome, versao, vuln) for (nome, versao, _), vuln in unicos.items()]
    if not achados:
        print("pip-audit: nenhuma vulnerabilidade conhecida.")
        return 0

    falhou = False
    print(f"pip-audit: {len(achados)} vulnerabilidade(s) encontrada(s):")
    for nome, versao, vuln in achados:
        nivel = severidade_do_achado(vuln)
        bloqueia = nivel is None or nivel in BLOQUEANTES
        falhou |= bloqueia
        correcao = ", ".join(vuln.get("fix_versions", [])) or "sem versão corrigida"
        marca = "BLOQUEIA" if bloqueia else "aviso"
        print(f"  [{marca}] {nome}=={versao} {vuln['id']} severidade={nivel or 'DESCONHECIDA'} correção: {correcao}")

    if falhou:
        print("Falha: há vulnerabilidade alta, crítica ou de severidade desconhecida.")
    else:
        print("Só vulnerabilidades de severidade moderada ou baixa: não bloqueia o pipeline.")
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main())
