# Regras para agentes de IA neste projeto

Suíte E2E em Python + Playwright + pytest para o site público https://www.saucedemo.com (Swag Labs,
site de prática, de terceiros, sem API). Page objects em `pages/`, testes em `tests/` (por área e por
perfil de usuário), dados e tabela de preços em `data/constants.py`, preparação compartilhada em
`conftest.py`. Bugs conhecidos ficam no próprio teste como `xfail(strict=True)`. Detalhes em
`README.md`, `BUGS.md` e `docs/`.

As regras estão em ordem de prioridade. **P1** nunca se quebra; **P2** vale em toda mudança; **P3** é
para quando o assunto aparecer.

## P1 · Crítico

1. **Nada irreversível sem pedido explícito:** commit, push, PR, merge, issue, comentário no GitHub ou
   apagar branch remota só quando a pessoa pedir. Antes do commit, mostre o que mudou e o resultado dos
   testes.
2. **Prove antes de afirmar:** rode os testes afetados antes de dizer que algo funciona. Uma proteção
   nova (checagem, marcação, regra de CI) só vale depois de simular a falha que ela deveria pegar.
3. **Nunca afrouxe uma asserção para o teste passar.** Se o site mudou, investigue; se for defeito do
   site, é bug novo (regra 6).
4. **Bug conhecido é `xfail(strict=True)` com `raises=` específico** e motivo começando pelo ID e pela
   issue: `reason="BUG-NNN (#issue): ..."`, com o ID e a issue que constam no `BUGS.md`. Assim o
   marker `known_bug` é aplicado sozinho, outra falha (login, seletor) não se esconde no xfail e um
   XPASS avisa que o bug foi corrigido. Nunca use xfail sem `raises=` nem `strict=False`. A regra é
   conferida por `support/known_bugs.py`: um xfail fora dela faz o teste terminar como ERRO.
5. **Site fora do ar não é resultado:** a proteção fica num ponto só, `support/site_guard.py`. Abra
   páginas sempre por `BasePage.open()` ou `safe_goto` (nunca `page.goto` direto) e passe status lido
   fora dela (`page.request`) por `check_status`. Queda vira "SITE INDISPONÍVEL", com disjuntor e
   código de saída 2; nunca aprovação nem bug. Teste que falha (ou dá XFAIL) com o site fora do ar
   também vira "SITE INDISPONÍVEL"; com o site no ar, falha continua falha. Não acrescente retry de teste (`pytest-rerunfailures`
   ou parecido): repetir teste que falhou esconde instabilidade. Repetir o carregamento da página,
   dentro do `safe_goto`, é outra coisa e é a única espera por tempo permitida.
6. **Bug novo, antes do commit, confira tudo que fala de bugs:**
   - `BUGS.md`: linha na tabela e contagens (total, todos os usuários × perfis especiais);
   - `docs/relatorio-de-bugs.md`: seção completa (passos, esperado, obtido, evidência, teste) e resumo;
     o PDF é gerado de novo com `python scripts/gerar_relatorio_pdf.py`;
   - `README.md`: contagens (no "Em resumo" e na tabela de engenharia reversa, com as severidades) e o
     texto alternativo da imagem-resumo; a imagem `docs/img/resumo-projeto.png` sai de
     `docs/img/resumo-projeto.html`;
   - evidência em `docs/evidencias/`, teste com o xfail da regra 4 e issue no GitHub (label `bug`);
   - a descrição do repositório no GitHub, se citar contagens;
   - procure o número anterior (ex.: "25 bugs", "BUG-025") para não deixar contagem velha.
7. **Não edite arquivos de teste com o pytest rodando.**

## P2 · Importante

8. **Rode os testes localmente só no Chromium** (o padrão do `pytest.ini`), dentro do `.venv`. Firefox e
   WebKit só quando a pessoa pedir. Durante o trabalho, rode só o arquivo afetado
   (`pytest tests/test_x.py` ou `-k termo`); a suíte completa (`pytest -n auto`), uma vez antes do
   commit.
9. **Idioma:** identificadores em inglês (classes, métodos, fixtures, variáveis, constantes). Em
   português: nomes das funções de teste (`test_usuarios_validos_acessam_o_inventario`), docstrings,
   comentários, mensagens, documentação, commits e PRs.
10. **Rastreabilidade:** todo teste do site tem o comentário `# CT-<ARQUIVO>-NN` na linha acima do
    primeiro decorador (ou do `def`), com ARQUIVO = nome do arquivo sem `test_` e `.py`, em
    maiúsculas e com hífen (`test_cart_checkout.py` → `CT-CART-CHECKOUT-01`), numerado na ordem do
    arquivo. Teste novo ou alterado exige atualizar `docs/casos-de-teste.md`. Bugs como `BUG-NNN`
    (com a issue) e regras de negócio como `RN-NN` (`docs/requisitos-inferidos.md`), citados no
    teste. Teste novo de regra atualiza a cobertura das regras; bug novo segue a regra 6.
11. **Como escrever testes:**
    - nunca `sleep` nem `wait_for_timeout`: o Playwright espera sozinho; para provar que algo NÃO
      aconteceu, use `wait_for_render` (dois quadros) ou um sinal direto, nunca um tempo fixo;
    - toda asserção negativa ("não aparece", "não mudou") vem depois de um controle positivo de que a
      página certa já foi desenhada; depois de um clique que troca de tela, dois quadros não bastam:
      use `on_page` (a URL decide se avançou) e `reached` (espera o elemento da tela nova);
    - seletores por `data-test` (`get_by_test_id`); exceção só com comentário explicando, como o botão
      do menu (`#react-burger-menu-btn`);
    - valor esperado vem de `PRODUCT_PRICES` em `data/constants.py`, nunca da tela testada; dinheiro em
      `Decimal`;
    - login reaproveitado (`login_as`, `session_as`, `standard_session`); carrinho montado com
      `cart_with(...)`; a tela só para o que está sendo testado;
    - estado conferido por baixo da tela (`cart_ids`, `session_cookie`) onde a tela não prova o efeito;
    - nenhum texto ou dado solto no teste: usuários, produtos e mensagens em `data/constants.py`;
    - toda `assert` tem mensagem dizendo o que é conferido (`assert total == esperado, "total do
      resumo"`); `expect` de preparação leva a mensagem `"pré-condição: ..."` ou `"controle
      positivo: ..."`; os demais `expect` usam a mensagem do Playwright, que já mostra o elemento, o
      esperado e o obtido;
    - exceção JavaScript falha o teste; `allow_js_errors` só com comentário citando o bug que a gera;
    - perfis com defeito comparados ao `standard_user` como oráculo (`oracle_inventory`), em vez de
      valores fixos no código.
    - `tests/test_convencoes.py` barra no CI, em `tests/`, `support/`, `pages/` e `conftest.py`:
      `assert` sem mensagem, espera fixa, `page.goto` direto, teste pulado (`skip`), depurador e a
      senha fora de `data/constants.py`. Exceção só em `ALLOWED`, com motivo e quantidade exata.
12. **Markers:** `smoke` para fluxos críticos, `regression` para regressão por perfil e bordas;
    `known_bug` é aplicado sozinho por `support/known_bugs.py` (não marque à mão). Com
    `--strict-markers`, marcador fora da lista do `pytest.ini` é erro.
13. **Dependências:** versões exatas no `requirements.txt`, publicadas há pelo menos duas semanas; o
    pip-audit do CI falha em severidade alta ou crítica.

## P3 · Complementar

14. **Análise de mutação:** ao alterar um teste que usa o usuário base, rode
    `pytest -m "not known_bug" --base-user problem_user` (e `error_user`) e atualize a tabela de
    `docs/analise-de-mutacao.md`. Um teste que continua passando numa funcionalidade que o perfil quebra
    tem asserção fraca.
15. **BUG-023 (condição de corrida do menu) não tem teste, de propósito:** a reprodução fica em
    `scripts/reproduzir_bug_023.py`. Não crie teste dependente de tempo para ele.
16. **Paralelismo:** o CI já roda com `pytest -n auto`. Teste novo tem que ser independente (contexto
    novo por teste); se só passar em sequência, o defeito é do teste.
17. **Commits e PRs:** em português, explicando o porquê; o PR traz a validação feita.
18. **Documentação:** mudança de comportamento atualiza o `README.md` (e as "Decisões técnicas", se
    for uma decisão) e, se for o caso, `docs/sugestoes-de-melhoria.md` e os próximos passos.

## Comandos

```bash
source .venv/bin/activate
pytest tests/test_login.py                       # um arquivo
pytest -m smoke                                  # fluxos críticos
pytest -n auto -m "not known_bug"                # só o que deve passar, em paralelo
pytest -n auto                                   # suíte completa, como no PR
pytest -m "not known_bug" --base-user problem_user   # análise de mutação
playwright show-trace test-results/<pasta>/trace.zip # depurar uma falha
python scripts/gerar_relatorio_pdf.py            # regerar o relatório de bugs em PDF
```
