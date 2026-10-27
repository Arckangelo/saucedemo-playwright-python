# Sugestões de melhoria

Propostas que surgiram da engenharia reversa do SauceDemo ([requisitos](requisitos-inferidos.md)
e [bugs](relatorio-de-bugs.md)). Esforço e impacto são estimativas qualitativas.

| Escala | Esforço | Impacto |
|---|---|---|
| Baixo | Menos de meio dia | Melhoria pontual |
| Médio | 1 a 2 dias | Melhora um fluxo ou a confiança na suíte |
| Alto | Mais de 2 dias | Muda a forma de trabalhar ou evita uma classe inteira de problemas |

---

## Parte A: melhorias para a aplicação

### Validações e regras de negócio

| # | Sugestão | Resolve | Esforço | Impacto |
|---|---|---|---|---|
| A1 | Desabilitar **Checkout** com o carrinho vazio e bloquear o acesso direto ao checkout nesse caso. | BUG-001 | Baixo | Alto |
| A2 | Aplicar `trim()` antes de validar nome, sobrenome e CEP, e validar o formato do CEP (hoje qualquer texto é aceito, RN-16). | BUG-002 | Baixo | Médio |
| A3 | Normalizar o carrinho ao ler o `localStorage`: descartar ids fora do catálogo e repetidos, e tratar JSON inválido sem erro. Esconder **Add to cart** na página "ITEM NOT FOUND". | BUG-004, S-03 | Baixo | Médio |
| A4 | Fazer o **Reset App State** atualizar o estado da interface (botões), não só o armazenamento. | BUG-003 | Baixo | Baixo |
| A5 | Ao voltar para um resumo de pedido já concluído, redirecionar para o inventário ou desabilitar **Finish**. | S-01 | Baixo | Médio |
| A6 | Preservar os dados do formulário ao voltar do passo 2 para o passo 1 (RN-20). | UX | Baixo | Baixo |
| A7 | Remover ou concluir o item de menu **Dynamic Catalog**, que hoje não faz nada. | S-02 | Baixo | Baixo |

### Experiência do usuário e tratamento de erros

| # | Sugestão | Resolve | Esforço | Impacto |
|---|---|---|---|---|
| A8 | Mostrar mensagem ao usuário quando adicionar, remover, ordenar ou finalizar falhar, em vez de falhar em silêncio ou só no console. Trocar o `alert()` nativo por uma notificação na página. | BUG-010, BUG-014, BUG-015, BUG-018 | Médio | Alto |
| A9 | Configurar a telemetria com credenciais reais por variável de ambiente, ou desligá-la. Hoje os erros "reportados ao Backtrace" nunca chegam. | BUG-006 | Baixo | Médio |
| A10 | Servir as rotas da aplicação com HTTP 200 (fallback de SPA configurado no servidor), em vez de 404. | BUG-005 | Baixo | Médio |
| A15 | No menu lateral, cancelar o timer que esconde o menu no próprio clique em "Open Menu" (ou conferir o estado atual quando o timer dispara, em vez do valor capturado ao agendá-lo). | BUG-023 | Baixo | Baixo |

### Acessibilidade

| # | Sugestão | Resolve | Esforço | Impacto |
|---|---|---|---|---|
| A11 | Aumentar a área de toque do botão do menu para pelo menos 24×24 px (WCAG 2.2, 2.5.8), de preferência 44×44 px no celular. | S-04 | Baixo | Médio |
| A12 | Anunciar mudanças do carrinho para leitores de tela (região `aria-live` no contador) e mover o foco para a mensagem de erro do formulário. | — | Baixo | Médio |
| A13 | Usar elementos nativos: os links de produto são `<a>` com `role="button"`, o que confunde leitores de tela e exigiu um seletor especial na suíte. | — | Médio | Médio |

O axe-core não encontrou violações sérias ou críticas nas 6 telas avaliadas. As sugestões A11 a
A13 vêm de inspeção manual, fora do que a verificação automática cobre.

### Segurança (contexto: site de demonstração)

| # | Sugestão | Esforço | Impacto |
|---|---|---|---|
| A14 | A sessão é o nome do usuário em texto puro no cookie: quem edita o cookie troca de perfil sem senha (RN-06). Num produto real, usar um token assinado e emitido pelo servidor, com `HttpOnly`, `Secure` e `SameSite`. | Alto | Alto |

---

## Parte B: melhorias para este projeto

Situação na primeira entrega (15/10/2026): **78 execuções, ~108 s em série** (42 passam e 36
são `xfail` de bugs conhecidos), só no Chromium. B2, B6 e B10 já foram implementados, e a espera fixa
de 2 s dos testes de bug foi trocada pela espera da renderização: hoje a suíte completa leva ~81 s
em série e ~24 s em paralelo, medidos localmente com 8 núcleos.

| # | Sugestão | Esforço | Impacto |
|---|---|---|---|
| B1 | **Matriz de navegadores no CI:** rodar Chromium, Firefox e WebKit em jobs paralelos (`strategy.matrix`) no `e2e-tests.yml`. | Baixo | Alto |
| B2 | **Execução paralela com pytest-xdist** (`pytest -n auto`). **Implementado.** | Baixo | Médio |
| B3 | **Checagem de acessibilidade no CI** com axe-core. | Médio | Alto |
| B4 | **Testes visuais com screenshot de referência** só para componentes estáveis. | Médio | Médio |
| B5 | **Relatório Allure.** | Médio | Médio |
| B6 | **Execução agendada (nightly) contra produção.** **Implementado.** | Baixo | Alto |
| B7 | **Regressão por usuário como matriz única.** | Médio | Médio |
| B8 | **Linter e formatação no CI** (ruff). | Baixo | Médio |
| B9 | **Detecção de flakiness agendada.** | Baixo | Médio |
| B10 | **Estado preparado sem interface.** **Implementado.** | Baixo | Médio |

### Detalhes

**B1. Matriz de navegadores.** Hoje só o Chromium é testado. Vários bugs desta análise dependem de
layout e eventos (BUG-021, BUG-022, BUG-009), que podem variar entre motores. Com `strategy.matrix`
os três navegadores rodam em paralelo; o tempo total do CI quase não muda, só o consumo de minutos.

**B2. pytest-xdist (implementado).** A suíte já era independente por teste (contexto novo e
carrinho vazio a cada teste), pré-requisito para paralelizar. Medido localmente, 8 núcleos: suíte
completa de ~81 s em série para ~24 s com `-n auto`; a execução do push (`-m "not known_bug"`)
leva ~14 s. Cada worker faz o próprio login de sessão (`user_cookies` tem escopo de sessão por
processo). O paralelismo expôs uma condição de corrida no menu do site (BUG-023), documentada nas decisões
técnicas do README e contornada esperando um sinal concreto, sem retry.

**B3. Acessibilidade no CI (com justificativa).** Nesta análise, o axe-core foi usado só na
exploração, para não adicionar dependência. Vale levar para o CI porque:
- é uma das classes de defeito mais caras de corrigir depois do lançamento, e as diretrizes WCAG
  são exigência legal em vários mercados (no Brasil, a Lei Brasileira de Inclusão);
- o custo é baixo: uma dependência (`axe-playwright-python`) e um teste parametrizado por tela,
  reaproveitando as fixtures de login que já existem;
- hoje o resultado é zero violações sérias ou críticas, então o teste entra verde e passa a
  **proteger** esse estado contra regressões, em vez de só relatar;
- filtrar por impacto sério e crítico evita ruído: os alertas menores ficam no relatório, sem
  quebrar o build.

Limitação a registrar: ferramentas automáticas detectam só parte dos problemas de acessibilidade
(S-04 é um exemplo); a revisão manual continua necessária.

**B4. Testes visuais.** Os testes do `visual_user` comparam valores do DOM com o oráculo, o que
é estável no CI. Screenshots de referência pegariam diferenças que o DOM não mostra (cor, fonte,
sobreposição), mas variam entre sistemas e navegadores. Se adotados, gerar as referências dentro do
próprio contêiner do CI e limitar a componentes estáveis (cabeçalho, card de produto).

**B5. Allure.** Agrupa os resultados por perfil, área e bug; mostra histórico entre execuções e
anexa trace e screenshot. O pytest-html atual atende, mas não mostra tendência ao longo do tempo.

**B6. Nightly contra produção (implementado).** O SauceDemo é um sistema de terceiros que muda sem
aviso (o item "Dynamic Catalog" é um exemplo). Com `xfail(strict=True)`, a execução diária (09:00
UTC) detecta quando um bug some (XPASS) ou quando surge um comportamento novo, sem depender de
push no repositório. Em repositórios públicos, o GitHub desativa o agendamento após 60 dias sem
atividade; é preciso reativá-lo pela aba Actions.

**B7. Matriz de regressão por usuário.** Hoje cada perfil tem seu arquivo. Uma matriz única
"funcionalidade × usuário", com o `standard_user` como oráculo, tornaria trivial incluir um perfil
novo e geraria a [matriz de divergências](requisitos-inferidos.md#matriz-usuário--funcionalidade)
automaticamente a partir dos resultados.

**B8. Ruff.** Não há linter no projeto. Nesta entrega, os imports sem uso foram conferidos à mão;
um `ruff check` no CI (e no `pre-commit`) faz isso sempre, em segundos.

**B9. Flakiness.** Cada teste novo foi rodado 3 vezes sem variação. Para manter isso, agendar
semanalmente `pytest --count=5` (pytest-repeat) e acompanhar os resultados que mudam entre
execuções. Não usar re-execução automática de falhas: ela esconde a instabilidade em vez de
mostrá-la.

**B10. Estado sem interface (implementado em 27/10/2026).** Os testes que precisam de itens no
carrinho gravam o `localStorage` diretamente, pela fixture `cart_with` (e a sessão pelo cookie, com
`session_as`), quando a adição pela interface não é o objeto do teste. Só os testes do botão Add to
cart e a jornada completa clicam na tela. Resultado: os testes do checkout, do Reset App State, do
`problem_user` e do `error_user` deixaram de depender dos botões quebrados (BUG-010 e BUG-015), e
os 12 testes migrados ficaram ~17% mais rápidos em série. A fixture grava uma única vez por aba,
para um item removido não "voltar" no reload, e recusa ids fora do catálogo ou repetidos.
