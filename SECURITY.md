# Política de segurança

## Escopo

Este repositório contém uma suíte de testes automatizados (Python + Playwright) para o site
público [SauceDemo](https://www.saucedemo.com), mantido pela Sauce Labs, **não por mim**.

| Situação | Onde reportar |
|---|---|
| Vulnerabilidade **neste repositório**: segredo exposto, workflow inseguro, dependência vulnerável, etc. | Aqui, pelo canal privado abaixo |
| Vulnerabilidade **no site SauceDemo** | Diretamente à Sauce Labs |

As credenciais em `data/constants.py` (por exemplo, a senha `secret_sauce`) são as de
demonstração exibidas publicamente na tela de login do SauceDemo e não são segredos.

## Como reportar

**Não abra uma issue pública** para relatar uma vulnerabilidade.

Use o reporte privado do GitHub: aba **Security** → **Report a vulnerability**
([link direto](https://github.com/Arckangelo/saucedemo-playwright-python/security/advisories/new)).

Inclua, se possível:

- descrição do problema e do impacto;
- passos para reproduzir ou prova de conceito;
- arquivos, commits ou workflows afetados.

## O que esperar

Este é um projeto pessoal de portfólio, mantido por uma pessoa. Busco:

- confirmar o recebimento em até **7 dias**;
- informar a avaliação e o plano de correção em até **30 dias**.

Se um segredo tiver sido exposto, ele é revogado assim que o reporte é confirmado, antes de
qualquer outra ação.

## Versões suportadas

Só a branch `main` recebe correções.

## Controles automatizados

O pipeline de CI aplica detecção de segredos (gitleaks), auditoria de dependências
(pip-audit + Dependabot) e análise estática (CodeQL). Detalhes na seção
[Segurança do pipeline](README.md#segurança-do-pipeline) do README.
