# API REST

A documentação interativa fica no Swagger, em **http://localhost:8000/docs**, com exemplos nas rotas principais.
Para testar uma rota protegida, faça `POST /auth/login`, copie o `access_token`, clique em **Authorize** e cole o token.

## Rotas

| Método e rota | Acesso | Finalidade | Equivalente na loja |
| --- | --- | --- | --- |
| `POST /auth/registro` | Público | Cria um usuário externo **pendente** de aprovação | registro |
| `POST /auth/login` | Público | Autentica e devolve o JWT | login |
| `GET / PUT /usuarios/me` | Logado | Ver e editar o próprio perfil e a senha | editar perfil |
| `GET / POST /usuarios`, `PUT / DELETE /usuarios/{id}` | Admin | Gerenciar e aprovar usuários | — |
| `GET / POST /clientes`, `PUT /clientes/{id}` | Equipe (GET) / Admin | Clientes (empresas) | — |
| `GET / POST /navios`, `PUT / DELETE /navios/{id}` | Logado (GET) / Admin | Navios | — |
| `GET / POST /escalas`, `GET / PUT / DELETE /escalas/{id}` | Logado (GET) / Admin | **CRUD de escalas** | categorias |
| `GET /containers?busca=&status=&escala=&cliente=&pagina=&tamanho_pagina=` | Logado (externo: só os seus) | **Listagem paginada com busca e filtro** | catálogo |
| `GET /containers/{id}` | Logado (externo: só os seus) | Detalhe com posição, bloqueios e histórico | detalhe do produto |
| `POST / PUT / DELETE /containers` | Equipe | **CRUD de containers** (DELETE = soft delete) | produtos |
| `POST /containers/{id}/bloqueios`, `DELETE /containers/{id}/bloqueios/{bid}` | Admin | Bloquear e liberar | controlar estoque |
| `POST /containers/{id}/movimentacoes` | Equipe | Mover o container no pátio | — |
| `GET /patio/posicoes?livres=` | Equipe | Mapa do pátio e posições livres | — |
| `GET /janelas?data=&com_vaga=` | Logado | Janelas de atendimento | — |
| `POST / PUT / DELETE /janelas` | Admin | Gerenciar janelas e vagas | — |
| `POST /agendamentos` | Externo | **Agendar (transacional)** | fechar pedido |
| `GET /agendamentos/meus` | Externo | Agendamentos do próprio cliente | meus pedidos |
| `GET /agendamentos?status=` | Equipe | Todos os agendamentos | admin pedidos |
| `PATCH /agendamentos/{id}/status` | Dono ou equipe | Cancelar (devolve a vaga) | alterar status |
| `GET /portao/consulta?termo=` | Equipe | Pré-checagem do portão, sem gravar nada | — |
| `POST /portao/entradas` | Equipe | **Gate-in (transacional)** | — |
| `POST /portao/saidas` | Equipe | Gate-out (nega container bloqueado) | — |

## Códigos de status

| Código | Quando |
| --- | --- |
| 200 | Leitura ou atualização bem-sucedida |
| 201 | Recurso criado (cadastro, agendamento, gate-in, bloqueio) |
| 204 | Desativação ou remoção sem corpo |
| 400 | Requisição incoerente: placa divergente sem justificativa, senha atual errada, desativar o próprio usuário |
| 401 | Sem token, token inválido ou expirado, login errado |
| 403 | Papel sem permissão; cadastro pendente ou usuário inativo no login |
| 404 | Não existe, ou pertence a outro cliente (para o externo não descobrir o que existe) |
| 409 | Conflito de regra: janela lotada, container bloqueado, posição ocupada, duplicado, transição inválida |
| 422 | Validação: ISO 6346, CNPJ, peso ≤ 0, datas invertidas, campos faltando |

## Formato de erro

Todas as respostas de erro seguem o mesmo formato:

```json
{
  "erro": {
    "codigo": "janela_lotada",
    "mensagem": "A janela não tem mais vagas; escolha outra"
  }
}
```

Os erros de validação (422) listam os campos com problema:

```json
{
  "erro": {
    "codigo": "validacao",
    "mensagem": "Dados inválidos",
    "detalhes": [{ "campo": "peso_kg", "mensagem": "Input should be greater than 0" }]
  }
}
```

## Exemplo de ponta a ponta (curl)

```bash
API=http://localhost:8000

# 1. login do cliente
TOKEN=$(curl -s $API/auth/login -H 'content-type: application/json' \
  -d '{"email":"ana@transportesoeste.com.br","senha":"<SEED_SENHA_PADRAO>"}' | jq -r .access_token)

# 2. containers do cliente aguardando chegada
curl -s "$API/containers?status=aguardando_chegada" -H "Authorization: Bearer $TOKEN" | jq '.itens[].codigo'

# 3. agendar a entrega na janela 15
curl -s $API/agendamentos -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"janela_id":15,"operacao":"entrega","container_ids":[13],"placa":"ABC1D23","motorista":"João"}'

# 4. operador consulta pela placa e registra a entrada
curl -s "$API/portao/consulta?termo=ABC1D23" -H "Authorization: Bearer $TOKEN_OPERADOR"
curl -s $API/portao/entradas -H "Authorization: Bearer $TOKEN_OPERADOR" -H 'content-type: application/json' \
  -d '{"codigo_container":"CMAU3055228","placa":"ABC1D23"}'
```
