# Pesquisa de processo e decisões de UI/UX

Antes de desenhar as telas, pesquisamos como terminais reais operam o portão e o pátio, e como os
sistemas do setor (TOS, *Terminal Operating Systems*, como Navis N4 e Tideworks) organizam essas tarefas.

## O que a pesquisa mostrou

1. **Exceções no portão são o maior gargalo.** Exceções viram *trouble tickets*: o caminhão é desviado para um
   guichê de atendimento. São cerca de **5% das transações**, mas somam por volta de 3 minutos ao tempo médio
   de atendimento. Alguns relatos falam em até 1 hora por caso. A APL estimou que **65% delas poderiam ter sido
   resolvidas antes de o caminhão chegar ao terminal**.
   ([National Academies – Truck Drayage Productivity Guide](https://nap.nationalacademies.org/read/14536/chapter/8),
   [FreightWaves](https://www.freightwaves.com/?p=143818))
2. **Cada minuto no portão se multiplica pela fila.** Um minuto desnecessário no atendimento é pago por todos os
   caminhões que estão atrás. Portões automatizados reduziram o pré-gate de ~30 para ~3 minutos.
   ([National Academies](https://nap.nationalacademies.org/read/14536/chapter/6),
   [Tideworks – Tips for Improving Truck Turn Times](https://tideworks.com/tips-for-improving-truck-turn-times/))
3. **Agendamento distribui a chegada e precisa de tolerância.** Sistemas de agendamento existem para espalhar as
   chegadas ao longo do dia ([EPA – Port gate management](https://19january2025snapshot.epa.gov/ports-initiative/port-gate-management-strategies-improve-air-quality-and-efficiency-ports),
   [Port Economics – tipos de TAS](https://porteconomicsmanagement.org/pemp/contents/part6/terminal-automation/types-container-terminal-appointment-systems/)).
   No Porto de Santos o agendamento é obrigatório desde 2014, e a norma atual dá **tolerância de algumas horas
   após a janela**
   ([Canal Rural](https://www.canalrural.com.br/noticias/nacional/ano-comeca-com-mudanca-no-porto-de-santos-entenda/),
   [Gazeta SP](https://www.gazetasp.com.br/estado/porto-de-santos-tem-atualizacao-na-norma-de-agendamento-de-caminhoes/)).
4. **Políticas de portão inconsistentes atrasam mais do que regras rígidas.** Quando cada atendente decide de um jeito,
   o motorista não sabe o que levar.
   ([Tideworks](https://tideworks.com/tips-for-improving-truck-turn-times/))
5. **O pátio é endereçado por bloco, fileira, pilha e altura** e mostrado como mapa, com cores por status. O
   Kalmar SmartPort, por exemplo, separa o mapa em tempo real (SmartMap) das instruções ao operador (SmartScreen).
   ([Infor – Visual Yard](https://docs.infor.com/yms/2026.x/en-us/ymsug/slp1586444879374.html),
   [YardView](https://www.yardview.com/post/container-yard-management))
6. **Avisar o cliente antes evita a viagem perdida.** No Brasil, a Santos Brasil avisa o motorista pelo app
   quando a carga é liberada pela fiscalização.
   ([Mundo Logística](https://mundologistica.com.br/noticias/santos-brasil-automatiza-centros-logisticos-industriais-aduaneiros))

## Como isso virou interface

| Insight | Decisão no PortoFlow |
| --- | --- |
| 1. Exceções são o gargalo; a maioria é evitável antes da chegada | **Pré-checagem** (`GET /portao/consulta`): antes de gravar, a tela lista cada pendência em linguagem simples e **o que fazer** com ela. Na tela **Agendar**, o cliente não consegue escolher container bloqueado nem combinação inválida, e vê o motivo; o erro aparece em casa, não no portão. |
| 2. Cada minuto multiplica pela fila | Portão operado **só pelo teclado**: o campo já vem com foco, *Enter* consulta, o botão de registrar já vem focado, e *Enter* registra. A busca aceita **placa**, o identificador que o operador tem na frente; pela placa aparecem todos os containers do caminhão. Ao terminar, o campo limpa e volta o foco. |
| 3. Janela com tolerância | A pendência distingue "chegou **antes** da janela" de "janela **encerrada**". Uma tolerância configurável (como a de Santos) é uma evolução natural; ver abaixo. |
| 4. Regras consistentes | As mesmas regras rodam na consulta, no registro e no agendamento (um serviço só no back-end), e as mensagens explicam a regra em vez de só negar. |
| 5. Mapa por bloco | Tela **Pátio**: grade por fileira e pilha, com o número da altura da pilha, borda vermelha para bloqueado e destaque laranja na busca. Só o container do **topo** tem o botão Mover; os outros explicam o motivo. |
| 5'. Empilhar gera remoção | A **posição sugerida ocupa primeiro o chão**, depois o 2º nível, e assim por diante: cada container empilhado sem necessidade vira uma remoção extra quando o de baixo precisar sair. |
| 6. Avisar antes | O número `AG...` aparece ao confirmar o agendamento, com o aviso de que é ele (ou a placa) que o portão vai pedir. |

Princípios gerais da interface: Mantine com labels em todos os campos, foco visível, alvos de toque grandes no
portão (`size="lg"`), tema claro e escuro automático, layout que funciona em 360 px, e os três estados
(carregando, erro com "tentar de novo" e lista vazia) em todas as telas que consomem a API.

## Próximos passos sugeridos (fora do escopo atual)

- **Tolerância de janela** configurável: ex.: aceitar até 2 h depois do fim, como em Santos.
- **Registro de ocorrências** (*trouble tickets*): gravar cada recusa no portão com o motivo, para o
  administrador ver quais problemas mais se repetem.
- **Notificação ao cliente** quando o container fica disponível para retirada ou é bloqueado.
- **Painel** com ocupação do pátio, tempo médio de permanência e caminhões por janela.
