# TO-DO

## [ ] Robôs de simulação da operação (carga em larga escala)

Criar "robôs" que simulam operadores e clientes usando a API de verdade, para movimentar containers e executar
ações em larga escala, com **várias instâncias rodando ao mesmo tempo**.

**Para que serve**
- Pôr à prova a concorrência real das regras transacionais. Dois robôs disputando a última vaga de uma janela
  (`SELECT ... FOR UPDATE`) ou a mesma posição do pátio (`UNIQUE posicao_id`) devem resultar em exatamente
  um sucesso e um 409.
- Medir o tempo de resposta e a taxa de erros com muitos usuários simultâneos.
- Encher o pátio para demonstrar o mapa, a regra de empilhamento e o painel numa apresentação.

**Robôs (um processo por robô, vários por tipo)**

| Robô | Perfil | O que faz em loop |
| --- | --- | --- |
| `cliente` | externo | escolhe 1–2 containers aguardando ou no pátio e agenda numa janela com vaga; às vezes cancela |
| `portao` | operador | consulta pela placa os agendamentos da janela atual e registra a entrada ou a saída; às vezes erra a placa e justifica |
| `patio` | operador | move containers do topo de uma pilha para outra posição livre |
| `admin` | admin | cria janelas, bloqueia e libera containers aleatórios, cadastra containers novos |

**Como rodar (proposta)**
- Pasta `simulador/`, em Python com `asyncio` + `httpx`, ou um serviço por robô.
- Perfil próprio no compose, para não subir junto no uso normal:
  `docker compose --profile simulacao up --scale robo-portao=5 --scale robo-cliente=20`.
- Parâmetros por variável de ambiente: quantidade de robôs, ritmo (ações/min), duração e semente aleatória.
- Seed de simulação: muitos clientes e usuários, centenas de containers, mais blocos de pátio e janelas
  com relógio acelerado (ou janelas sempre "agora").

**Saída esperada**
- Relatório no fim: ações por tipo, sucessos e erros por código (409 `janela_lotada`, `posicao_ocupada` etc.) e
  latência p50/p95.
- **Verificação de invariantes** no banco ao terminar: nenhuma posição com 2 containers, `vagas_livres` entre 0 e o
  total, vagas ocupadas = agendamentos confirmados + cumpridos por janela, toda entrada com movimentação
  `gate_in`, nenhum container bloqueado com saída registrada depois do bloqueio.

**Pronto quando:** 50 robôs rodam por 5 minutos sem nenhuma invariante quebrada, e o relatório fica salvo em `docs/`.
