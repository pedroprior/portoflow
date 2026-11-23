# Roteiro da apresentação e da arguição

## Antes de começar

```bash
docker compose down -v          # banco zerado, como pede o enunciado
docker compose up --build       # migrations + seed + API + front
```

Deixe abertos: http://localhost:5173 (uma aba anônima por perfil) e http://localhost:8000/docs.

## Demonstração (~10 min)

1. **Subida do zero.** Mostre o log do container `api`: `Running upgrade -> 0001` e `Seed aplicado`. Abra o Swagger.
2. **Cliente:** faça login como `ana@transportesoeste.com.br`.
   - Em **Meus containers**, busque e filtre. Marque 2 containers de 20' e mostre que um de 40' fica desabilitado,
     com o motivo.
   - Em **Agendar**, escolha o dia e a janela, informe a placa e confirme. Anote o número `AG...`.
3. **Janela lotada (409):** no Cadastros (admin), crie uma janela com 1 vaga; agende duas vezes. A segunda
   mostra a mensagem, e **Meus agendamentos** confirma que nada foi gravado.
4. **Operador no portão:** faça login como `operador@portoflow.com.br`.
   - Digite a placa e tecle Enter: aparecem os 2 containers, com a posição sugerida no chão.
   - Tecle Enter, Enter: as entradas são registradas e o campo volta ao início.
   - Digite o código do container bloqueado do seed: a tela mostra **Não liberar o caminhão**, o motivo e o que fazer.
5. **Pátio:** localize o container, abra a pilha e mova o do topo. Mostre que o de baixo não tem botão Mover.
6. **Administrador:**
   - Bloqueie um container agendado para retirada; o agendamento vira cancelado e a vaga volta.
   - Libere o container.
   - Aprove um cadastro pendente (crie um em **Solicitar acesso**).
7. **Segurança:**
   - No Swagger, chame `GET /usuarios` sem token (**401**) e com o token do cliente (**403**).
   - Pelo cliente, abra `/containers/{id}` de outro cliente: **404**.
8. **Celular:** abra as DevTools em 360 px e mostre o Portão e o Pátio.
9. **Testes:** rode `pytest` (216 testes) e mostre o workflow do GitHub Actions.

## Perguntas prováveis e respostas curtas

**Por que NUMERIC e não FLOAT?**
FLOAT guarda em binário; 0,1 não tem representação exata e `0.1*3` dá `0.30000000000000004`. Em somas
(peso de pilha, faturamento), o erro acumula. NUMERIC(10,2) guarda o decimal exato. Por isso a API devolve o
valor como texto: assim o JSON não o converte para float.

**O que impede duas transportadoras de pegarem a última vaga ao mesmo tempo?**
O `SELECT ... FOR UPDATE` na linha da janela. A segunda transação espera a primeira terminar e então vê
`vagas_livres = 0`, devolvendo 409. Além disso, o banco tem `CHECK (vagas_livres >= 0)` como última barreira.

**E se der erro no meio do gate-in?**
Tudo roda numa sessão só, com um `commit` no fim. Qualquer exceção antes disso faz rollback: não fica
movimentação sem container no pátio, nem posição ocupada sem registro. A posição também é `UNIQUE`, então nem
uma corrida entre dois operadores consegue colocar dois containers no mesmo lugar.

**Por que a regra fica no serviço e não na rota?**
A mesma regra é usada em três lugares: na pré-checagem do portão, no registro e no agendamento. No serviço, ela
é escrita uma vez, testada sem HTTP e não depende de quem chama.

**Proteger a rota no front não basta?**
Não. O front só esconde a tela; qualquer um pode chamar a API direto. Quem garante é a API (`requer_papel`:
401 sem token, 403 com papel errado). Os testes chamam as rotas sem passar pela interface.

**Por que soft delete?**
Container e escala têm histórico (movimentações, bloqueios, agendamentos) ligado por FK com `RESTRICT`.
Apagar fisicamente quebraria o histórico. Desativar preserva o histórico e tira o registro das listagens.

**Por que o carrinho está no front?**
A seleção só tem valor quando vira agendamento, com a vaga reservada. Guardar seleções abandonadas no banco
ocuparia vagas sem caminhão e não acrescentaria nada.

**Por que o externo recebe 404, e não 403, ao abrir o container de outro cliente?**
Com 403, ele descobriria que o código existe. Com 404, não sabe se o container existe.

**Por que a posição sugerida vai primeiro para o chão?**
Cada container posto em cima de outro vira uma remoção extra quando o de baixo precisar sair. Empilhar só quando
falta chão reduz o retrabalho, um problema clássico de pátio (ver [ux-insights.md](ux-insights.md)).
