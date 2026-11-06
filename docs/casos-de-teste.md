# Casos de teste — saucedemo-playwright-python

Um caso de teste para cada teste automatizado, na mesma ordem em que os testes aparecem em cada arquivo de tests/, identificado pelo mesmo ID CT do comentário no código. Total: 42 casos (87 execuções, contando os parâmetros).

**Notas gerais**

- Todos os casos rodam contra o site público https://www.saucedemo.com, que não tem API. Os valores esperados vêm de `data/constants.py`: preços de `PRODUCT_PRICES`, mensagens de `Messages`, nunca da tela testada.
- O ID de cada caso é o mesmo do comentário `# CT-…` acima do teste no código; o arquivo é o da seção.
- A senha de todos os usuários é `secret_sauce`. O login é feito uma vez por usuário e o cookie de sessão é copiado para um navegador novo a cada teste: todo caso começa com o carrinho vazio.
- Quando adicionar pela tela não é o assunto do caso, o carrinho é montado direto no `localStorage` (fixture `cart_with`) e a tela é aberta pela URL.
- Dados do passo 1 do checkout, quando o caso os usa: nome "Ana", sobrenome "Souza", CEP "72980-000" (`CHECKOUT_INFO`).
- Qualquer exceção JavaScript da página reprova o caso, exceto nos marcados com `allow_js_errors`, que citam o bug que gera o erro.
- Bugs conhecidos são `xfail(strict=True)` com a exceção própria do bug: o Resultado esperado é o comportamento correto e o Resultado obtido é o do site hoje. Se o bug for corrigido, o teste avisa (XPASS vira falha). Detalhes de cada bug em [BUGS.md](../BUGS.md).
- O BUG-023 (menu lateral que abre invisível) não tem caso, de propósito: é uma condição de corrida que depende de tempo, reproduzida em `scripts/reproduzir_bug_023.py`.
- Status: execução de 06/11/2026 com `pytest -n auto`, no Chromium.

## Índice

| Área | Arquivo | Casos |
|---|---|---|
| Autenticação | [test_login.py](#test_loginpy) | 5 |
| Catálogo | [test_inventory.py](#test_inventorypy) | 5 |
| Catálogo | [test_product_detail.py](#test_product_detailpy) | 4 |
| Carrinho e checkout | [test_cart_checkout.py](#test_cart_checkoutpy) | 10 |
| Menu | [test_menu.py](#test_menupy) | 2 |
| Saúde técnica | [test_console_e_rede.py](#test_console_e_redepy) | 2 |
| Perfis com defeito | [test_problem_user.py](#test_problem_userpy) | 6 |
| Perfis com defeito | [test_error_user.py](#test_error_userpy) | 5 |
| Perfis com defeito | [test_visual_user.py](#test_visual_userpy) | 3 |
| **Total** | | **42** |

Os testes da própria suíte, que não testam o site, ficam no fim: [Testes da própria suíte](#testes-da-própria-suíte).

## Autenticação

### test_login.py

#### CT-LOGIN-01 — Usuários válidos acessam o inventário

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Autenticação › Login › Usuário válido |
| **Tipo de teste** | Funcional – positivo |
| **Prioridade** | Alta |
| **Objetivo** | Garantir que cada perfil aceito pelo site entra na loja com a senha correta. |
| **Pré-condições** | Sem login; tela de login aberta. |
| **Dados de teste** | standard_user, problem_user, performance_glitch_user, error_user e visual_user (um por execução). |
| **Passos** | 1. Preencher usuário e senha e clicar em "Login".<br>2. Verificar a URL e o inventário. |
| **Resultado esperado** | A URL termina em /inventory.html e o inventário mostra os 6 produtos. |
| **Status** | Passou (5 execuções) |
| **Observações** | Tag smoke.<br>O performance_glitch_user atrasa ~5 s o inventário de propósito; só para este caso, a espera vai até 15 s. |

#### CT-LOGIN-02 — Login inválido exibe a mensagem de erro certa

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Autenticação › Login › Credenciais inválidas |
| **Tipo de teste** | Funcional – negativo (validação) |
| **Prioridade** | Alta |
| **Objetivo** | Garantir que cada credencial recusada mostra a mensagem própria e não entra na loja. |
| **Pré-condições** | Sem login; tela de login aberta. |
| **Dados de teste** | Usuário bloqueado: locked_out_user + senha correta.<br>Senha incorreta: standard_user + "senha_errada".<br>Usuário inexistente: "usuario_inexistente" + senha correta.<br>Usuário em branco: usuário vazio + senha correta.<br>Senha em branco: standard_user + senha vazia. |
| **Passos** | 1. Preencher usuário e senha e clicar em "Login".<br>2. Verificar a mensagem e a URL. |
| **Resultado esperado** | Usuário bloqueado: "Epic sadface: Sorry, this user has been locked out."<br>Senha incorreta e usuário inexistente: "Epic sadface: Username and password do not match any user in this service".<br>Usuário em branco: "Epic sadface: Username is required".<br>Senha em branco: "Epic sadface: Password is required".<br>Em todos, a URL não vai para /inventory.html. |
| **Status** | Passou (5 execuções) |
| **Observações** | Senha errada e usuário inexistente têm a mesma mensagem: o site não revela quais usuários existem. |

#### CT-LOGIN-03 — Rotas internas exigem login

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Autenticação › Acesso às rotas |
| **Tipo de teste** | Segurança – autorização |
| **Prioridade** | Alta |
| **Objetivo** | Garantir que nenhuma tela interna abre sem sessão. |
| **Pré-condições** | Sem login. |
| **Dados de teste** | /inventory.html, /inventory-item.html?id=4, /cart.html, /checkout-step-one.html, /checkout-step-two.html e /checkout-complete.html (uma por execução). |
| **Passos** | 1. Abrir a rota pela URL.<br>2. Verificar a mensagem na tela de login. |
| **Resultado esperado** | O site volta ao login com "Epic sadface: You can only access '&lt;rota&gt;' when you are logged in.", citando a rota sem a query string (para ?id=4, '/inventory-item.html'). |
| **Status** | Passou (6 execuções) |
| **Observações** | A mensagem só existe na tela de login, então ela prova o redirecionamento. |

#### CT-LOGIN-04 — Cookie de sessão adulterado não dá acesso

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Autenticação › Sessão |
| **Tipo de teste** | Segurança – sessão |
| **Prioridade** | Média |
| **Objetivo** | Garantir que um cookie de sessão forjado não abre a loja. |
| **Pré-condições** | Sem login. |
| **Dados de teste** | Cookie session-username com: "usuario_falso" (usuário inexistente), "locked_out_user" (usuário bloqueado) e "STANDARD_USER" (nome certo, mas em maiúsculas). |
| **Passos** | 1. Gravar o cookie com o valor forjado.<br>2. Abrir /inventory.html.<br>3. Verificar a mensagem. |
| **Resultado esperado** | O site volta ao login com "Epic sadface: You can only access '/inventory.html' when you are logged in." |
| **Status** | Passou (3 execuções) |
| **Observações** | A sessão do site é só o nome do usuário, em texto puro, no cookie. |

#### CT-LOGIN-05 — Logout encerra a sessão

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Autenticação › Logout |
| **Tipo de teste** | Funcional – positivo |
| **Prioridade** | Alta |
| **Objetivo** | Garantir que o logout apaga a sessão, e não só volta para a tela de login. |
| **Pré-condições** | standard_user logado, no inventário. |
| **Dados de teste** | Não se aplica. |
| **Passos** | 1. Clicar em "Logout" no menu lateral.<br>2. Verificar a tela de login.<br>3. Ler o cookie de sessão.<br>4. Abrir /inventory.html de novo. |
| **Resultado esperado** | Passo 2: o botão "Login" aparece.<br>Passo 3: o cookie session-username não existe mais.<br>Passo 4: "Epic sadface: You can only access '/inventory.html' when you are logged in." |
| **Status** | Passou |
| **Observações** | O cookie é a causa e o bloqueio do passo 4 é o efeito: o caso confere os dois. |

## Catálogo

### test_inventory.py

#### CT-INVENTORY-01 — Ordenação dos produtos

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Catálogo › Inventário › Ordenação |
| **Tipo de teste** | Funcional – positivo |
| **Prioridade** | Média |
| **Objetivo** | Garantir que as 4 ordenações deixam a lista na ordem certa, calculada a partir de PRODUCT_PRICES. |
| **Pré-condições** | standard_user logado, no inventário. |
| **Dados de teste** | az (nome de A a Z), za (nome de Z a A), lohi (preço do menor para o maior) e hilo (preço do maior para o menor). |
| **Passos** | 1. Escolher uma ordem diferente da alvo (za para o caso az; az para os demais) e conferir que a lista não está na ordem esperada.<br>2. Escolher a ordenação do caso.<br>3. Verificar a opção selecionada e a lista. |
| **Resultado esperado** | Passo 3: a opção selecionada é a do caso e a lista fica assim:<br>az: Sauce Labs Backpack, Sauce Labs Bike Light, Sauce Labs Bolt T-Shirt, Sauce Labs Fleece Jacket, Sauce Labs Onesie, Test.allTheThings() T-Shirt (Red).<br>za: a mesma lista, invertida.<br>lohi: $7.99, $9.99, $15.99, $15.99, $29.99, $49.99.<br>hilo: os mesmos preços, invertidos. |
| **Status** | Passou (4 execuções) |
| **Observações** | O passo 1 evita um falso positivo: a página abre em A–Z, então o caso az passaria mesmo com a ordenação quebrada. |

#### CT-INVENTORY-02 — Cada produto exibe a própria imagem

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Catálogo › Inventário › Imagens |
| **Tipo de teste** | Funcional – recurso |
| **Prioridade** | Média |
| **Bug relacionado** | BUG-007 |
| **Objetivo** | Garantir que os 6 produtos têm imagens diferentes e nenhuma é a imagem de erro. |
| **Pré-condições** | Sem login; tela de login aberta. |
| **Dados de teste** | standard_user e problem_user (um por execução). |
| **Passos** | 1. Fazer login pela tela.<br>2. Ler o endereço das 6 imagens do inventário. |
| **Resultado esperado** | 6 endereços diferentes, nenhum com "sl-404". |
| **Resultado obtido** | problem_user (BUG-007): os 6 produtos exibem a mesma imagem sl-404. |
| **Status** | Passou (standard_user); XFAIL (problem_user, BUG-007) |

#### CT-INVENTORY-03 — Adicionar atualiza o contador e o botão

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Catálogo › Inventário › Adicionar ao carrinho |
| **Tipo de teste** | Funcional – positivo |
| **Prioridade** | Alta |
| **Bug relacionado** | BUG-010, BUG-015 |
| **Objetivo** | Garantir que o botão "Add to cart" de cada produto leva o produto ao carrinho. |
| **Pré-condições** | standard_user logado, no inventário. |
| **Dados de teste** | Os 6 produtos do catálogo. |
| **Passos** | 1. Clicar em "Add to cart" em cada um dos 6 produtos.<br>2. Verificar o contador e os botões. |
| **Resultado esperado** | O contador do carrinho mostra "6" e os 6 botões mostram "Remove". |
| **Status** | Passou |
| **Observações** | É o caso que garante o botão "Add to cart" pela tela. Usa os 6 produtos porque, só com 2, a análise de mutação mostrou que ele passava com o problem_user e o error_user, que não adicionam 3 dos produtos (BUG-010 e BUG-015, cobertos no CT-PROBLEM-USER-02 e no CT-ERROR-USER-02). |

#### CT-INVENTORY-04 — Remover o último item esconde o contador e volta o botão

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Catálogo › Inventário › Remover do carrinho |
| **Tipo de teste** | Funcional – positivo |
| **Prioridade** | Média |
| **Objetivo** | Garantir que, com o carrinho vazio, o contador some e o botão volta a oferecer a adição. |
| **Pré-condições** | standard_user logado; Sauce Labs Backpack no carrinho. |
| **Dados de teste** | Sauce Labs Backpack. |
| **Passos** | 1. Abrir o inventário e conferir que o contador mostra "1".<br>2. Clicar em "Remove" na Backpack.<br>3. Verificar o contador e o botão. |
| **Resultado esperado** | O contador some e o botão da Backpack mostra "Add to cart". |
| **Status** | Passou |
| **Observações** | O contador é calculado a partir do localStorage, então uma remoção não gravada já faria o contador continuar na tela. |

#### CT-INVENTORY-05 — Reset App State restaura os botões

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Catálogo › Inventário › Reset App State |
| **Tipo de teste** | Funcional – consistência |
| **Prioridade** | Baixa |
| **Bug relacionado** | BUG-003 |
| **Objetivo** | Garantir que, depois do Reset App State, a tela não mostra itens que não estão mais no carrinho. |
| **Pré-condições** | standard_user logado; Sauce Labs Backpack e Sauce Labs Bike Light no carrinho. |
| **Dados de teste** | Sauce Labs Backpack e Sauce Labs Bike Light. |
| **Passos** | 1. Abrir o inventário e conferir que o contador mostra "2".<br>2. Clicar em "Reset App State" no menu lateral e fechar o menu.<br>3. Conferir que o contador sumiu.<br>4. Verificar os botões dos 2 produtos. |
| **Resultado esperado** | Passo 4: os dois botões mostram "Add to cart". |
| **Resultado obtido** | O contador some e o localStorage é limpo, mas os botões continuam em "Remove" até recarregar a página. |
| **Status** | XFAIL (bug conhecido) |

### test_product_detail.py

#### CT-PRODUCT-DETAIL-01 — Detalhe mostra o produto clicado

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Catálogo › Detalhe do produto › Navegação |
| **Tipo de teste** | Funcional – navegação |
| **Prioridade** | Média |
| **Bug relacionado** | BUG-011 |
| **Objetivo** | Garantir que clicar no nome de um produto abre o detalhe desse produto. |
| **Pré-condições** | standard_user logado, no inventário. |
| **Dados de teste** | Os 6 produtos do catálogo. |
| **Passos** | 1. Para cada produto, clicar no nome.<br>2. Verificar o nome no detalhe.<br>3. Clicar em "Back to products". |
| **Resultado esperado** | Para cada produto, o detalhe mostra o mesmo nome que foi clicado. |
| **Status** | Passou |
| **Observações** | BUG-011: no problem_user, o detalhe abre o produto seguinte; coberto no CT-PROBLEM-USER-03. |

#### CT-PRODUCT-DETAIL-02 — URL do detalhe abre o produto pelo id

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Catálogo › Detalhe do produto › URL |
| **Tipo de teste** | Funcional – positivo |
| **Prioridade** | Média |
| **Objetivo** | Garantir que /inventory-item.html?id=N abre o produto do id N. |
| **Pré-condições** | standard_user logado. |
| **Dados de teste** | id 0 = Sauce Labs Bike Light, 1 = Sauce Labs Bolt T-Shirt, 2 = Sauce Labs Onesie, 3 = Test.allTheThings() T-Shirt (Red), 4 = Sauce Labs Backpack, 5 = Sauce Labs Fleece Jacket (um por execução). |
| **Passos** | 1. Abrir /inventory-item.html?id=N.<br>2. Verificar o nome do produto. |
| **Resultado esperado** | O nome é o do id, conforme a lista dos dados de teste. |
| **Status** | Passou (6 execuções) |

#### CT-PRODUCT-DETAIL-03 — Produto inexistente não entra no carrinho

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Catálogo › Detalhe do produto › Produto inexistente |
| **Tipo de teste** | Funcional – recurso inexistente |
| **Prioridade** | Média |
| **Bug relacionado** | BUG-004 |
| **Objetivo** | Garantir que um produto que não existe no catálogo não pode ser adicionado ao carrinho. |
| **Pré-condições** | standard_user logado, com o carrinho vazio. |
| **Dados de teste** | ids "6" e "-1" (um por execução). |
| **Passos** | 1. Abrir /inventory-item.html?id=&lt;id&gt; e conferir que a página mostra "ITEM NOT FOUND".<br>2. Se o botão "Add to cart" estiver visível, clicar nele.<br>3. Verificar o contador do carrinho. |
| **Resultado esperado** | O contador do carrinho não aparece. |
| **Resultado obtido** | O contador mostra "1", mas o carrinho fica vazio. |
| **Status** | XFAIL (bug conhecido, 2 execuções) |
| **Observações** | Esconder o botão também é uma correção válida: o passo 2 só clica se ele existir. |

#### CT-PRODUCT-DETAIL-04 — Carrinho ignora ids inexistentes no localStorage

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Catálogo › Carrinho › Produto inexistente |
| **Tipo de teste** | Funcional – recurso inexistente |
| **Prioridade** | Média |
| **Bug relacionado** | BUG-004 |
| **Objetivo** | Garantir que um id desconhecido no carrinho é descartado e não é contado. |
| **Pré-condições** | standard_user logado, no inventário. |
| **Dados de teste** | localStorage cart-contents = [999]. |
| **Passos** | 1. Gravar cart-contents = [999] e recarregar a página.<br>2. Conferir que o inventário mostra os 6 produtos.<br>3. Verificar o contador do carrinho. |
| **Resultado esperado** | O contador do carrinho não aparece. |
| **Resultado obtido** | O contador mostra "1" com o carrinho vazio. |
| **Status** | XFAIL (bug conhecido) |

## Carrinho e checkout

### test_cart_checkout.py

**Notas gerais**

- Só o CT-CART-CHECKOUT-01, o 07 e o 10 adicionam produtos pela tela; os demais montam o carrinho no localStorage e abrem a tela do caso pela URL.
- Preços esperados: Sauce Labs Backpack $29.99, Sauce Labs Bolt T-Shirt $15.99, Sauce Labs Onesie $7.99, Sauce Labs Fleece Jacket $49.99 (PRODUCT_PRICES).

#### CT-CART-CHECKOUT-01 — Compra completa, do inventário ao pedido concluído

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Checkout › Jornada completa |
| **Tipo de teste** | Funcional – ponta a ponta |
| **Prioridade** | Alta |
| **Objetivo** | Garantir que a compra inteira pela tela funciona e que o resumo mostra os itens certos. |
| **Pré-condições** | standard_user logado, no inventário, com o carrinho vazio. |
| **Dados de teste** | Sauce Labs Backpack, Sauce Labs Bolt T-Shirt e Sauce Labs Onesie; dados do passo 1 (CHECKOUT_INFO). |
| **Passos** | 1. Clicar em "Add to cart" nos 3 produtos.<br>2. Abrir o carrinho e clicar em "Checkout".<br>3. Preencher nome, sobrenome e CEP e clicar em "Continue".<br>4. Verificar as linhas do resumo.<br>5. Clicar em "Finish". |
| **Resultado esperado** | Passo 4: 3 linhas, na ordem em que foram adicionadas: Backpack $29.99, Bolt T-Shirt $15.99 e Onesie $7.99, cada uma com quantidade 1.<br>Passo 5: "Thank you for your order!". |
| **Status** | Passou |
| **Observações** | Tag smoke.<br>Os cálculos do resumo são conferidos no CT-CART-CHECKOUT-02 e o carrinho vazio depois do pedido, no CT-CART-CHECKOUT-08. |

#### CT-CART-CHECKOUT-02 — Resumo calcula subtotal, imposto e total

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Checkout › Resumo do pedido |
| **Tipo de teste** | Funcional – regra de negócio |
| **Prioridade** | Alta |
| **Regra de negócio** | RN-17 |
| **Objetivo** | Garantir que o resumo calcula o subtotal, o imposto de 8% e o total a partir dos preços do catálogo. |
| **Pré-condições** | standard_user logado; Sauce Labs Backpack, Sauce Labs Bolt T-Shirt e Sauce Labs Onesie no carrinho. |
| **Dados de teste** | Os 3 produtos acima; imposto de 8% (TAX_RATE). |
| **Passos** | 1. Abrir /checkout-step-two.html e conferir que o resumo mostra 3 itens.<br>2. Ler subtotal, imposto e total. |
| **Resultado esperado** | Subtotal $53.97; imposto $4.32 (8% do subtotal, arredondado a 2 casas); total $58.29. |
| **Status** | Passou |
| **Observações** | O esperado vem de PRODUCT_PRICES, não dos preços exibidos: somar a própria tela não pegaria um preço errado exibido e cobrado de forma coerente (como no BUG-019). |

#### CT-CART-CHECKOUT-03 — Checkout exige nome, sobrenome e CEP

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Checkout › Passo 1 › Campos obrigatórios |
| **Tipo de teste** | Funcional – negativo (validação) |
| **Prioridade** | Alta |
| **Objetivo** | Garantir que o passo 1 não avança com um campo obrigatório vazio e informa qual falta. |
| **Pré-condições** | standard_user logado; Sauce Labs Backpack no carrinho; passo 1 aberto pela URL. |
| **Dados de teste** | Dados do passo 1 com um campo vazio por execução: sem nome, sem sobrenome e sem CEP. |
| **Passos** | 1. Preencher os campos, deixando vazio o do caso.<br>2. Clicar em "Continue".<br>3. Verificar a mensagem e a URL. |
| **Resultado esperado** | Sem nome: "Error: First Name is required".<br>Sem sobrenome: "Error: Last Name is required".<br>Sem CEP: "Error: Postal Code is required".<br>Em todos, a URL continua /checkout-step-one.html. |
| **Status** | Passou (3 execuções) |

#### CT-CART-CHECKOUT-04 — Checkout rejeita campos só com espaços

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Checkout › Passo 1 › Campos obrigatórios |
| **Tipo de teste** | Funcional – borda |
| **Prioridade** | Média |
| **Bug relacionado** | BUG-002 |
| **Objetivo** | Garantir que um campo preenchido só com espaços é tratado como vazio. |
| **Pré-condições** | standard_user logado; Sauce Labs Backpack no carrinho; passo 1 aberto pela URL. |
| **Dados de teste** | Dados do passo 1 com três espaços ("   ") em um campo por execução: nome, sobrenome e CEP. |
| **Passos** | 1. Preencher os campos, com espaços no do caso.<br>2. Clicar em "Continue".<br>3. Verificar a URL e a mensagem de erro. |
| **Resultado esperado** | A URL continua /checkout-step-one.html e aparece uma mensagem de erro. |
| **Resultado obtido** | O formulário avança para o resumo nos três casos. |
| **Status** | XFAIL (bug conhecido, 3 execuções) |

#### CT-CART-CHECKOUT-05 — Não conclui pedido com o carrinho vazio

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Checkout › Carrinho vazio |
| **Tipo de teste** | Funcional – regra de negócio |
| **Prioridade** | Média |
| **Bug relacionado** | BUG-001 |
| **Objetivo** | Garantir que um pedido sem itens não pode ser concluído. |
| **Pré-condições** | standard_user logado, no inventário, com o carrinho vazio. |
| **Dados de teste** | Carrinho vazio; dados do passo 1. |
| **Passos** | 1. Abrir o carrinho e conferir que ele está vazio.<br>2. Clicar em "Checkout", se o botão estiver visível e habilitado.<br>3. Preencher o passo 1 e clicar em "Continue".<br>4. Clicar em "Finish", se o resumo abrir. |
| **Resultado esperado** | O pedido é bloqueado em alguma etapa: botão "Checkout" escondido ou desabilitado, passo 1 que não avança ou "Finish" que não leva a "Thank you for your order!". |
| **Resultado obtido** | O resumo mostra "Item total: $0" e "Total: $0.00", e o pedido é concluído com "Thank you for your order!". |
| **Status** | XFAIL (bug conhecido) |
| **Observações** | Qualquer bloqueio conta como correção. Antes de concluir que uma etapa foi bloqueada, o caso confere que a tela já foi desenhada, para uma página lenta não parecer correção. |

#### CT-CART-CHECKOUT-06 — Resumo exige o passo 1 preenchido

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Checkout › Resumo do pedido › Acesso |
| **Tipo de teste** | Funcional – regra de negócio |
| **Prioridade** | Média |
| **Bug relacionado** | BUG-024 |
| **Objetivo** | Garantir que o pedido não é concluído sem nome, sobrenome e CEP. |
| **Pré-condições** | standard_user logado; Sauce Labs Backpack no carrinho; o passo 1 nunca foi preenchido. |
| **Dados de teste** | Sauce Labs Backpack. |
| **Passos** | 1. Abrir /checkout-step-two.html direto pela URL.<br>2. Se o resumo abrir, conferir o item e clicar em "Finish". |
| **Resultado esperado** | O pedido é bloqueado: o site volta ao passo 1, esconde o "Finish" ou não leva a "Thank you for your order!". |
| **Resultado obtido** | O resumo abre com o item, o pagamento, a entrega e o total, e o pedido é concluído com "Thank you for your order!". |
| **Status** | XFAIL (bug conhecido) |
| **Observações** | Como no CT-CART-CHECKOUT-05, qualquer bloqueio conta como correção. |

#### CT-CART-CHECKOUT-07 — Carrinho persiste após recarregar a página

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Carrinho › Persistência |
| **Tipo de teste** | Funcional – positivo |
| **Prioridade** | Alta |
| **Regra de negócio** | RN-08, RN-13 |
| **Objetivo** | Garantir que os itens adicionados continuam no carrinho depois de recarregar a página. |
| **Pré-condições** | standard_user logado, no inventário, com o carrinho vazio. |
| **Dados de teste** | Sauce Labs Backpack (id 4) e Sauce Labs Fleece Jacket (id 5). |
| **Passos** | 1. Clicar em "Add to cart" nos 2 produtos.<br>2. Recarregar a página.<br>3. Verificar o contador e o localStorage.<br>4. Abrir o carrinho. |
| **Resultado esperado** | Passo 3: contador "2" e cart-contents = [4, 5], na ordem em que foram adicionados.<br>Passo 4: Sauce Labs Backpack e Sauce Labs Fleece Jacket, nessa ordem. |
| **Status** | Passou |

#### CT-CART-CHECKOUT-08 — Concluir o pedido esvazia o carrinho

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Checkout › Pedido concluído |
| **Tipo de teste** | Funcional – positivo |
| **Prioridade** | Alta |
| **Bug relacionado** | BUG-013 |
| **Regra de negócio** | RN-19 |
| **Objetivo** | Garantir que, depois do pedido, o carrinho sai do localStorage, e não só da tela. |
| **Pré-condições** | standard_user logado; Sauce Labs Backpack no carrinho. |
| **Dados de teste** | Sauce Labs Backpack. |
| **Passos** | 1. Abrir /checkout-step-two.html e conferir que o resumo mostra 1 item.<br>2. Clicar em "Finish".<br>3. Ler o localStorage. |
| **Resultado esperado** | Passo 2: "Thank you for your order!".<br>Passo 3: cart-contents = [] (vazio). |
| **Status** | Passou |
| **Observações** | BUG-013: no problem_user o carrinho continua cheio; coberto no CT-PROBLEM-USER-05. |

#### CT-CART-CHECKOUT-09 — Remover do carrinho mantém os demais após recarregar

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Carrinho › Remover |
| **Tipo de teste** | Funcional – positivo |
| **Prioridade** | Média |
| **Regra de negócio** | RN-13 |
| **Objetivo** | Garantir que remover um item tira só ele e que a remoção persiste. |
| **Pré-condições** | standard_user logado; Sauce Labs Backpack e Sauce Labs Fleece Jacket no carrinho. |
| **Dados de teste** | Sauce Labs Backpack e Sauce Labs Fleece Jacket. |
| **Passos** | 1. Abrir /cart.html e conferir as 2 linhas.<br>2. Clicar em "Remove" na Backpack.<br>3. Recarregar a página.<br>4. Verificar as linhas. |
| **Resultado esperado** | Passo 2: 1 linha.<br>Passo 4: 1 linha, Sauce Labs Fleece Jacket, $49.99, quantidade 1. |
| **Status** | Passou |
| **Observações** | A tela pode apagar a linha sem gravar nada; só o recarregamento prova que a remoção persistiu. |

#### CT-CART-CHECKOUT-10 — Carrinho mostra nome, preço e quantidade 1 de cada produto

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Carrinho › Itens |
| **Tipo de teste** | Funcional – positivo |
| **Prioridade** | Alta |
| **Regra de negócio** | RN-11 |
| **Objetivo** | Garantir que cada linha do carrinho mostra o nome e o preço do catálogo, com quantidade 1. |
| **Pré-condições** | standard_user logado, no inventário, com o carrinho vazio. |
| **Dados de teste** | Sauce Labs Backpack e Sauce Labs Fleece Jacket. |
| **Passos** | 1. Clicar em "Add to cart" nos 2 produtos.<br>2. Abrir o carrinho.<br>3. Verificar as linhas. |
| **Resultado esperado** | 2 linhas, na ordem em que foram adicionadas: Backpack $29.99 e Fleece Jacket $49.99, cada uma com quantidade 1. |
| **Status** | Passou |
| **Observações** | O botão alterna entre "Add to cart" e "Remove" (RN-11), então não há como adicionar o mesmo produto duas vezes: a quantidade é sempre 1. |

## Menu

### test_menu.py

#### CT-MENU-01 — All Items volta para o inventário

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Menu lateral › All Items |
| **Tipo de teste** | Funcional – navegação |
| **Prioridade** | Baixa |
| **Objetivo** | Garantir que o link "All Items" do menu leva de volta ao inventário. |
| **Pré-condições** | standard_user logado, no inventário. |
| **Dados de teste** | Não se aplica. |
| **Passos** | 1. Abrir o carrinho.<br>2. Clicar em "All Items" no menu lateral.<br>3. Verificar a URL e o título. |
| **Resultado esperado** | A URL termina em /inventory.html e o título é "Products". |
| **Status** | Passou |

#### CT-MENU-02 — Link About aponta para a Sauce Labs

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Menu lateral › About |
| **Tipo de teste** | Funcional – navegação |
| **Prioridade** | Baixa |
| **Bug relacionado** | BUG-012 |
| **Objetivo** | Garantir que o link "About" leva ao site da Sauce Labs. |
| **Pré-condições** | Usuário do caso logado, no inventário. |
| **Dados de teste** | standard_user e problem_user (um por execução). |
| **Passos** | 1. Abrir o menu lateral.<br>2. Ler o destino do link "About". |
| **Resultado esperado** | O link aponta para https://saucelabs.com/. |
| **Resultado obtido** | problem_user (BUG-012): aponta para https://saucelabs.com/error/404. |
| **Status** | Passou (standard_user); XFAIL (problem_user, BUG-012) |
| **Observações** | O caso só lê o destino do link: seguir para o site da Sauce Labs testaria um sistema de terceiros. |

## Saúde técnica

### test_console_e_rede.py

#### CT-CONSOLE-E-REDE-01 — Rotas internas respondem HTTP 200

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Saúde técnica › Rotas HTTP |
| **Tipo de teste** | Contrato – status HTTP |
| **Prioridade** | Baixa |
| **Bug relacionado** | BUG-005 |
| **Objetivo** | Garantir que as rotas do site respondem 200 a quem acessa o link direto. |
| **Pré-condições** | Sem login. |
| **Dados de teste** | /, /inventory.html, /cart.html, /checkout-step-one.html e /inventory-item.html?id=4. |
| **Passos** | 1. Pedir cada rota por HTTP, sem renderizar a página.<br>2. Verificar o status de cada uma. |
| **Resultado esperado** | Status HTTP 200 em todas. |
| **Resultado obtido** | HTTP 404 em todas, menos /. A página aparece porque o JavaScript a monta mesmo assim. |
| **Status** | XFAIL (bug conhecido) |
| **Observações** | Um status de site fora do ar (429 ou 5xx) termina como "SITE INDISPONÍVEL", nunca como "o bug reproduz". |

#### CT-CONSOLE-E-REDE-02 — Telemetria não gera erros HTTP

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Saúde técnica › Telemetria |
| **Tipo de teste** | Contrato – status HTTP |
| **Prioridade** | Baixa |
| **Bug relacionado** | BUG-006 |
| **Objetivo** | Garantir que a telemetria enviada pelo site (Backtrace) não recebe resposta de erro. |
| **Pré-condições** | Sem login; navegador novo (a telemetria sai só na primeira carga). |
| **Dados de teste** | Não se aplica. |
| **Passos** | 1. Abrir a página inicial, esperando até 10 s pela requisição a backtrace.io.<br>2. Verificar o status da resposta. |
| **Resultado esperado** | A resposta não tem status de erro (400 ou mais). Se nenhuma telemetria for enviada, o caso também passa. |
| **Resultado obtido** | A requisição usa as credenciais literais de exemplo (UNIVERSE e TOKEN) e recebe 401 Unauthorized. |
| **Status** | XFAIL (bug conhecido) |
| **Observações** | Se a telemetria sai mas não recebe resposta (o Backtrace demora mais que o limite de 15 s do próprio site), o caso é pulado como inconclusivo, para não dar um falso "corrigido". |

## Perfis com defeito

Os perfis problem_user, error_user e visual_user têm defeitos injetados de propósito pelo site, para treino. Cada caso descreve o comportamento do standard_user, que é o correto.

### test_problem_user.py

**Notas gerais**

- Todos os casos usam o problem_user e são bugs conhecidos.
- Os casos de checkout montam o carrinho no localStorage, para não depender do "Add to cart" deste perfil (BUG-010).

#### CT-PROBLEM-USER-01 — Ordenação por nome de Z a A

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Perfis › problem_user › Ordenação |
| **Tipo de teste** | Funcional – positivo |
| **Prioridade** | Média |
| **Bug relacionado** | BUG-008 |
| **Objetivo** | Garantir que a ordenação Z–A reordena a lista. |
| **Pré-condições** | problem_user logado, no inventário. |
| **Dados de teste** | Opção za. |
| **Passos** | 1. Conferir que o inventário mostra os 6 produtos.<br>2. Escolher "Name (Z to A)".<br>3. Verificar a opção selecionada e a lista. |
| **Resultado esperado** | A opção selecionada é za e a lista fica: Test.allTheThings() T-Shirt (Red), Sauce Labs Onesie, Sauce Labs Fleece Jacket, Sauce Labs Bolt T-Shirt, Sauce Labs Bike Light, Sauce Labs Backpack. |
| **Resultado obtido** | A lista não muda e o seletor volta para "Name (A to Z)". |
| **Status** | XFAIL (bug conhecido) |

#### CT-PROBLEM-USER-02 — Adicionar e remover cada produto

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Perfis › problem_user › Carrinho |
| **Tipo de teste** | Funcional – positivo |
| **Prioridade** | Alta |
| **Bug relacionado** | BUG-010 |
| **Objetivo** | Garantir que cada produto entra e sai do carrinho pelos botões do inventário. |
| **Pré-condições** | problem_user logado, no inventário, com o carrinho vazio. |
| **Dados de teste** | Os 6 produtos do catálogo (um por execução). |
| **Passos** | 1. Clicar em "Add to cart" no produto.<br>2. Verificar o contador e o botão.<br>3. Clicar em "Remove".<br>4. Verificar o contador e o botão. |
| **Resultado esperado** | Passo 2: contador "1" e botão "Remove".<br>Passo 4: o contador some e o botão volta a "Add to cart". |
| **Resultado obtido** | Sauce Labs Bolt T-Shirt, Sauce Labs Fleece Jacket e Test.allTheThings() T-Shirt (Red): o "Add to cart" não faz nada (falha no passo 2).<br>Sauce Labs Backpack, Sauce Labs Bike Light e Sauce Labs Onesie: entram no carrinho, mas o "Remove" não faz nada (falha no passo 4).<br>A falha é silenciosa, sem mensagem. |
| **Status** | XFAIL (bug conhecido, 6 execuções) |

#### CT-PROBLEM-USER-03 — Detalhe mostra o produto clicado

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Perfis › problem_user › Detalhe do produto |
| **Tipo de teste** | Funcional – navegação |
| **Prioridade** | Média |
| **Bug relacionado** | BUG-011 |
| **Objetivo** | Garantir que clicar no nome de um produto abre o detalhe desse produto. |
| **Pré-condições** | problem_user logado, no inventário. |
| **Dados de teste** | Os 6 produtos do catálogo. |
| **Passos** | Os mesmos do CT-PRODUCT-DETAIL-01. |
| **Resultado esperado** | Para cada produto, o detalhe mostra o mesmo nome que foi clicado. |
| **Resultado obtido** | O link usa o id seguinte: a Backpack abre o Fleece Jacket (id 5), a Bike Light abre o Bolt T-Shirt (id 1), e assim por diante. O Fleece Jacket abre o id 6, que não existe ("ITEM NOT FOUND"). |
| **Status** | XFAIL (bug conhecido) |

#### CT-PROBLEM-USER-04 — Sobrenome fica no campo de sobrenome

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Perfis › problem_user › Checkout › Passo 1 |
| **Tipo de teste** | Funcional – positivo |
| **Prioridade** | Alta |
| **Bug relacionado** | BUG-009 |
| **Objetivo** | Garantir que o texto digitado no sobrenome fica no campo de sobrenome. |
| **Pré-condições** | problem_user logado; Sauce Labs Backpack no carrinho; passo 1 aberto pela URL. |
| **Dados de teste** | Sobrenome "Souza". |
| **Passos** | 1. Preencher só o sobrenome.<br>2. Ler os três campos. |
| **Resultado esperado** | Nome vazio, sobrenome "Souza" e CEP vazio. |
| **Resultado obtido** | "Souza" vai para o campo de nome, e o sobrenome fica vazio. O erro "Last Name is required" impede concluir a compra. |
| **Status** | XFAIL (bug conhecido) |

#### CT-PROBLEM-USER-05 — Carrinho esvazia após concluir o pedido

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Perfis › problem_user › Pedido concluído |
| **Tipo de teste** | Funcional – positivo |
| **Prioridade** | Média |
| **Bug relacionado** | BUG-013 |
| **Objetivo** | Garantir que, depois do pedido, o carrinho fica vazio. |
| **Pré-condições** | problem_user logado; Sauce Labs Backpack no carrinho. |
| **Dados de teste** | Sauce Labs Backpack. |
| **Passos** | 1. Abrir /checkout-step-two.html e conferir que o contador mostra "1".<br>2. Clicar em "Finish" e conferir "Thank you for your order!".<br>3. Verificar o contador do carrinho. |
| **Resultado esperado** | Passo 3: o contador não aparece. |
| **Resultado obtido** | O pedido é concluído, mas o contador continua em 1 e o item fica no localStorage. |
| **Status** | XFAIL (bug conhecido) |
| **Observações** | Vai direto ao resumo porque o passo 1 está quebrado para este perfil (BUG-009). |

#### CT-PROBLEM-USER-06 — Resumo calcula o subtotal pela soma dos itens

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Perfis › problem_user › Checkout › Resumo |
| **Tipo de teste** | Funcional – regra de negócio |
| **Prioridade** | Alta |
| **Bug relacionado** | BUG-025 |
| **Objetivo** | Garantir que o subtotal do resumo é a soma dos preços dos itens. |
| **Pré-condições** | problem_user logado; Sauce Labs Backpack e Sauce Labs Onesie no carrinho. |
| **Dados de teste** | Sauce Labs Backpack ($29.99) e Sauce Labs Onesie ($7.99). |
| **Passos** | 1. Abrir /checkout-step-two.html e conferir que o resumo mostra 2 itens.<br>2. Ler o subtotal. |
| **Resultado esperado** | Subtotal $37.98. |
| **Resultado obtido** | O subtotal é o dobro: $75.96; o imposto ($6.08) e o total ($82.04) são calculados sobre ele. Os preços de cada item estão certos. |
| **Status** | XFAIL (bug conhecido) |
| **Observações** | Encontrado pela análise de mutação (docs/analise-de-mutacao.md). O resumo abre sem o passo 1 pelo BUG-024. |

### test_error_user.py

**Notas gerais**

- Todos os casos usam o error_user e são bugs conhecidos.
- Os casos de checkout montam o carrinho no localStorage, para não depender do "Add to cart" deste perfil (BUG-015).

#### CT-ERROR-USER-01 — Ordenação por nome de Z a A

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Perfis › error_user › Ordenação |
| **Tipo de teste** | Funcional – positivo |
| **Prioridade** | Média |
| **Bug relacionado** | BUG-014 |
| **Objetivo** | Garantir que a ordenação Z–A reordena a lista sem alerta de erro. |
| **Pré-condições** | error_user logado, no inventário. |
| **Dados de teste** | Opção za. |
| **Passos** | 1. Conferir que o inventário mostra os 6 produtos.<br>2. Escolher "Name (Z to A)", aceitando qualquer alerta.<br>3. Verificar a lista e os alertas. |
| **Resultado esperado** | A lista fica na ordem Z–A (a mesma do CT-PROBLEM-USER-01) e nenhum alerta aparece. |
| **Resultado obtido** | Aparece o alerta "Sorting is broken! This error has been reported to Backtrace.", a lista não muda e o seletor volta para A–Z. |
| **Status** | XFAIL (bug conhecido) |

#### CT-ERROR-USER-02 — Adicionar e remover cada produto

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Perfis › error_user › Carrinho |
| **Tipo de teste** | Funcional – positivo |
| **Prioridade** | Alta |
| **Bug relacionado** | BUG-015 |
| **Objetivo** | Garantir que cada produto entra e sai do carrinho pelos botões do inventário. |
| **Pré-condições** | error_user logado, no inventário, com o carrinho vazio. |
| **Dados de teste** | Os 6 produtos do catálogo (um por execução). |
| **Passos** | Os mesmos do CT-PROBLEM-USER-02. |
| **Resultado esperado** | Os mesmos do CT-PROBLEM-USER-02. |
| **Resultado obtido** | Os mesmos produtos do BUG-010 falham, mas cada falha lança um erro JavaScript não tratado ("Failed to add item to the cart." ou "Failed to remove item from cart."), sem mensagem ao usuário. |
| **Status** | XFAIL (bug conhecido, 6 execuções) |
| **Observações** | Marcado com allow_js_errors por causa desses erros. |

#### CT-ERROR-USER-03 — Campo de sobrenome aceita texto

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Perfis › error_user › Checkout › Passo 1 |
| **Tipo de teste** | Funcional – positivo |
| **Prioridade** | Média |
| **Bug relacionado** | BUG-016 |
| **Objetivo** | Garantir que o campo de sobrenome guarda o texto digitado. |
| **Pré-condições** | error_user logado; Sauce Labs Backpack no carrinho; passo 1 aberto pela URL. |
| **Dados de teste** | Dados do passo 1. |
| **Passos** | 1. Preencher nome, sobrenome e CEP.<br>2. Ler o campo de sobrenome. |
| **Resultado esperado** | O sobrenome é "Souza". |
| **Resultado obtido** | O campo continua vazio. Digitar nele lança o erro JavaScript "Cannot read properties of undefined (reading 'value')". |
| **Status** | XFAIL (bug conhecido) |
| **Observações** | Marcado com allow_js_errors por causa desse erro. |

#### CT-ERROR-USER-04 — Checkout exige sobrenome

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Perfis › error_user › Checkout › Passo 1 |
| **Tipo de teste** | Funcional – negativo (validação) |
| **Prioridade** | Média |
| **Bug relacionado** | BUG-017 |
| **Objetivo** | Garantir que o passo 1 não avança sem sobrenome. |
| **Pré-condições** | error_user logado; Sauce Labs Backpack no carrinho; passo 1 aberto pela URL. |
| **Dados de teste** | Nome "Ana" e CEP "72980-000"; sobrenome vazio. |
| **Passos** | 1. Preencher nome e CEP.<br>2. Clicar em "Continue".<br>3. Verificar a URL e a mensagem. |
| **Resultado esperado** | A URL continua /checkout-step-one.html e aparece "Error: Last Name is required". |
| **Resultado obtido** | Avança para o resumo sem sobrenome. |
| **Status** | XFAIL (bug conhecido) |

#### CT-ERROR-USER-05 — Finish conclui o pedido

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Perfis › error_user › Pedido |
| **Tipo de teste** | Funcional – positivo |
| **Prioridade** | Alta |
| **Bug relacionado** | BUG-018 |
| **Objetivo** | Garantir que o botão "Finish" conclui o pedido. |
| **Pré-condições** | error_user logado; Sauce Labs Backpack no carrinho. |
| **Dados de teste** | Sauce Labs Backpack. |
| **Passos** | 1. Abrir /checkout-step-two.html e conferir que o resumo mostra a Backpack.<br>2. Clicar em "Finish".<br>3. Verificar a URL e a mensagem. |
| **Resultado esperado** | A URL termina em /checkout-complete.html e aparece "Thank you for your order!". |
| **Resultado obtido** | Nada acontece na tela: o usuário continua no resumo, sem mensagem, e o clique lança um erro JavaScript ("… is not a function"). A compra não pode ser concluída. |
| **Status** | XFAIL (bug conhecido) |
| **Observações** | Vai direto ao resumo para não depender do passo 1 (BUG-016 e BUG-017). Marcado com allow_js_errors. |

### test_visual_user.py

**Notas gerais**

- Todos os casos usam o visual_user. O standard_user é o oráculo: preços, imagens e posições esperados são lidos dele na hora, em outro navegador, e não ficam fixos no código.
- Os valores comparados são os do DOM, e não screenshots, que variam com fonte, sistema e navegador.

#### CT-VISUAL-USER-01 — Preços iguais aos do standard_user

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Perfis › visual_user › Preços |
| **Tipo de teste** | Funcional – consistência |
| **Prioridade** | Alta |
| **Bug relacionado** | BUG-019 |
| **Objetivo** | Garantir que o visual_user vê os mesmos preços que o standard_user. |
| **Pré-condições** | visual_user logado; standard_user logado em outro navegador; os dois no inventário. |
| **Dados de teste** | Os 6 produtos do catálogo. |
| **Passos** | 1. Ler o preço de cada produto nos dois inventários.<br>2. Conferir que os 6 produtos foram lidos dos dois lados.<br>3. Comparar os preços por produto. |
| **Resultado esperado** | Os 6 preços são iguais aos do standard_user. |
| **Resultado obtido** | Os preços mudam a cada carregamento e nenhum coincide com o catálogo (a Backpack já apareceu a $21.45, $98.47 e $67.68). O carrinho e o resumo mostram o preço real, que é o cobrado. |
| **Status** | XFAIL (bug conhecido) |
| **Observações** | Com os 6 comparados, um XPASS por coincidência exigiria que todos os preços aleatórios batessem com os reais ao mesmo tempo. |

#### CT-VISUAL-USER-02 — Imagens iguais às do standard_user

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Perfis › visual_user › Imagens |
| **Tipo de teste** | Funcional – consistência |
| **Prioridade** | Baixa |
| **Bug relacionado** | BUG-020 |
| **Objetivo** | Garantir que o visual_user vê a mesma imagem de cada produto que o standard_user. |
| **Pré-condições** | Iguais às do CT-VISUAL-USER-01. |
| **Dados de teste** | Os 6 produtos do catálogo. |
| **Passos** | 1. Ler o endereço da imagem de cada produto nos dois inventários.<br>2. Comparar por produto. |
| **Resultado esperado** | Os 6 endereços são iguais aos do standard_user. |
| **Resultado obtido** | A Backpack exibe a imagem de erro sl-404 em vez da mochila; os outros 5 estão certos. |
| **Status** | XFAIL (bug conhecido) |

#### CT-VISUAL-USER-03 — Layout igual ao do standard_user

| Campo | Descrição |
|---|---|
| **Módulo / Área** | Perfis › visual_user › Layout |
| **Tipo de teste** | Visual – posição e tamanho |
| **Prioridade** | Média |
| **Bug relacionado** | BUG-021, BUG-022 |
| **Objetivo** | Garantir que os elementos principais do inventário ficam na mesma posição e no mesmo tamanho que no standard_user. |
| **Pré-condições** | Iguais às do CT-VISUAL-USER-01. |
| **Dados de teste** | Ícone do carrinho, botão do menu, título, seletor de ordenação, botão do primeiro produto (Backpack) e botão do último produto (T-Shirt (Red)), um por execução; tolerância de 5 px. |
| **Passos** | 1. Esperar as fontes web carregarem nas duas páginas.<br>2. Medir posição (x, y), largura e altura do elemento nas duas.<br>3. Comparar. |
| **Resultado esperado** | Nenhuma diferença maior que 5 px em x, y, largura ou altura. |
| **Resultado obtido** | Ícone do carrinho (BUG-021): 186 px à esquerda e 29 px abaixo, colado ao seletor de ordenação.<br>Botão do último produto (BUG-022): 54 px à direita dos demais, passando da borda do card. |
| **Status** | Passou (título, botão do menu, seletor de ordenação e botão do primeiro produto); XFAIL (ícone do carrinho, BUG-021; botão do último produto, BUG-022) |
| **Observações** | A espera pelas fontes evita um falso positivo: medir antes compararia a fonte provisória de uma página com a final da outra. |

## Testes da própria suíte

Estes arquivos testam a própria suíte, e não o site: não têm ID CT nem caso completo.

### test_protecao_site.py

| O que garante | Testes |
|---|---|
| Site fora do ar (429, 502–504, 520–524, sem resposta ou página sem o título "Swag Labs") termina como "SITE INDISPONÍVEL", nunca como aprovado nem bug; o 404 das rotas internas (BUG-005) não é queda; o disjuntor abre depois de 2 quedas; a execução termina com código 2; uma falha com o site no ar continua falha. A queda é simulada, sem depender do site. | 19 |

### test_regra_dos_bugs.py

| O que garante | Testes |
|---|---|
| Todo xfail de bug conhecido tem strict=True, raises= com exceção própria e motivo "BUG-NNN (#issue): ..." com ID e issue iguais aos do BUGS.md; um xfail fora da regra termina como ERRO, também com pytest-xdist. | 16 |

### test_convencoes.py

| O que garante | Testes |
|---|---|
| Toda assert de tests/ e support/ tem mensagem dizendo o que é conferido. | 6 |
