/**
 * Pátio: mapa por bloco (fileira x pilha). Cada célula mostra quantos
 * containers estão empilhados; vermelho = há container bloqueado na pilha.
 * Clicar abre a pilha; só o container do topo pode ser movido.
 */
import { useMemo, useState } from 'react';
import {
  Badge,
  Box,
  Button,
  Drawer,
  Group,
  Modal,
  Paper,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
  Tooltip,
  UnstyledButton,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconArrowsMove, IconLock, IconSearch } from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, mensagemErro } from '../api';
import { DetalheContainer } from '../components/DetalheContainer';
import { Cabecalho, Codigo, Estado } from '../components/comuns';
import { normalizar } from '../util/validacao';

const ALTURA_MAXIMA = 5;

function agrupar(posicoes) {
  const blocos = {};
  for (const p of posicoes) {
    const bloco = (blocos[p.bloco] ??= {});
    const pilha = ((bloco[p.fileira] ??= {})[p.pilha] ??= []);
    pilha.push(p);
  }
  for (const bloco of Object.values(blocos)) {
    for (const fileira of Object.values(bloco)) {
      for (const pilha of Object.values(fileira)) pilha.sort((a, b) => a.altura - b.altura);
    }
  }
  return blocos;
}

function corDaPilha(qtd) {
  if (qtd === 0) return 'var(--mantine-color-default)';
  return `var(--mantine-color-indigo-${Math.min(2 + qtd * 1.5, 8) | 0})`;
}

function MoverModal({ posicao, aoFechar }) {
  const qc = useQueryClient();
  const [destino, setDestino] = useState(null);
  const livres = useQuery({
    queryKey: ['patio', 'livres'],
    queryFn: () => api.get('/patio/posicoes', { params: { livres: true } }).then((r) => r.data),
    enabled: Boolean(posicao),
  });
  const mover = useMutation({
    mutationFn: () =>
      api.post(`/containers/${posicao.container.id}/movimentacoes`, { posicao_id: Number(destino) }),
    onSuccess: ({ data }) => {
      notifications.show({ color: 'green', message: `${data.codigo} movido para ${data.posicao.endereco}` });
      qc.invalidateQueries({ queryKey: ['patio'] });
      setDestino(null);
      aoFechar(true);
    },
    onError: (e) => notifications.show({ color: 'red', title: 'Não movido', message: mensagemErro(e) }),
  });

  const opcoes = (livres.data ?? [])
    .filter((p) => !(p.bloco === posicao?.bloco && p.fileira === posicao?.fileira && p.pilha === posicao?.pilha))
    .map((p) => ({ value: String(p.id), label: p.endereco }));

  return (
    <Modal opened={Boolean(posicao)} onClose={() => aoFechar(false)} title="Mover container">
      {posicao && (
        <Stack>
          <Text>
            <Codigo>{posicao.container.codigo}</Codigo> está em <Codigo>{posicao.endereco}</Codigo>
          </Text>
          <Estado consulta={livres} vazio={!opcoes.length} mensagemVazia="Não há posição livre.">
            <Select
              label="Nova posição"
              description="Só aparecem posições livres e com apoio embaixo"
              placeholder="Digite para filtrar, ex.: B-02"
              data={opcoes}
              value={destino}
              onChange={setDestino}
              searchable
              data-autofocus
              nothingFoundMessage="Nenhuma posição"
            />
          </Estado>
          <Button
            leftSection={<IconArrowsMove size={18} />}
            disabled={!destino}
            loading={mover.isPending}
            onClick={() => mover.mutate()}
          >
            Confirmar movimentação
          </Button>
        </Stack>
      )}
    </Modal>
  );
}

export default function Patio() {
  const consulta = useQuery({
    queryKey: ['patio', 'mapa'],
    queryFn: () => api.get('/patio/posicoes').then((r) => r.data),
  });
  const [pilhaAberta, setPilhaAberta] = useState(null); // {bloco, fileira, pilha}
  const [mover, setMover] = useState(null);
  const [detalhe, setDetalhe] = useState(null);
  const [busca, setBusca] = useState('');

  const blocos = useMemo(() => agrupar(consulta.data ?? []), [consulta.data]);
  const alvo = normalizar(busca);
  const achado = alvo.length >= 4 ? consulta.data?.find((p) => p.container?.codigo.includes(alvo)) : null;
  const ocupadas = consulta.data?.filter((p) => p.ocupada).length ?? 0;
  const total = consulta.data?.length ?? 0;

  const pilha = pilhaAberta ? blocos[pilhaAberta.bloco][pilhaAberta.fileira][pilhaAberta.pilha] : [];
  const topo = [...pilha].reverse().find((p) => p.ocupada);

  return (
    <>
      <Cabecalho
        titulo="Pátio"
        descricao={total ? `${ocupadas} de ${total} posições ocupadas (${Math.round((ocupadas / total) * 100)}%)` : null}
      >
        <TextInput
          placeholder="Localizar container"
          aria-label="Localizar container no pátio"
          leftSection={<IconSearch size={16} />}
          value={busca}
          onChange={(e) => setBusca(e.currentTarget.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && achado) {
              setPilhaAberta({ bloco: achado.bloco, fileira: achado.fileira, pilha: achado.pilha });
            }
          }}
          error={alvo.length >= 4 && !achado ? 'Não está no pátio' : null}
        />
      </Cabecalho>

      <Group gap="md" mb="sm" c="dimmed" fz="xs">
        <Group gap={4}>
          <Box w={14} h={14} bg="var(--mantine-color-default)" bd="1px solid var(--mantine-color-default-border)" /> vazia
        </Group>
        <Group gap={4}>
          <Box w={14} h={14} bg="var(--mantine-color-indigo-5)" /> ocupada (número = altura da pilha)
        </Group>
        <Group gap={4}>
          <Box w={14} h={14} bd="2px solid var(--mantine-color-red-6)" /> tem container bloqueado
        </Group>
      </Group>

      <Estado consulta={consulta} vazio={!total} mensagemVazia="Nenhuma posição de pátio cadastrada.">
        <Stack>
          {Object.entries(blocos).map(([bloco, fileiras]) => {
            const numPilhas = Math.max(...Object.values(fileiras).map((f) => Object.keys(f).length));
            return (
              <Paper withBorder p="sm" key={bloco}>
                <Title order={3} size="h4" mb="xs">
                  Bloco {bloco}
                </Title>
                <Table.ScrollContainer minWidth={420}>
                  <Table withRowBorders={false} verticalSpacing={4} horizontalSpacing={4}>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th w={70}>Fileira</Table.Th>
                        {Array.from({ length: numPilhas }, (_, i) => (
                          <Table.Th key={i} ta="center">
                            Pilha {i + 1}
                          </Table.Th>
                        ))}
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {Object.entries(fileiras).map(([fileira, pilhas]) => (
                        <Table.Tr key={fileira}>
                          <Table.Th>{fileira}</Table.Th>
                          {Object.entries(pilhas).map(([numPilha, posicoes]) => {
                            const qtd = posicoes.filter((p) => p.ocupada).length;
                            const bloqueado = posicoes.some((p) => p.container?.bloqueado);
                            const destaque = achado && posicoes.some((p) => p.id === achado.id);
                            const rotulo = `Bloco ${bloco}, fileira ${fileira}, pilha ${numPilha}: ${qtd} de ${ALTURA_MAXIMA}`;
                            return (
                              <Table.Td key={numPilha}>
                                <UnstyledButton
                                  className="celula-patio"
                                  data-bloqueado={bloqueado}
                                  data-destaque={Boolean(destaque)}
                                  style={{ background: corDaPilha(qtd), color: qtd > 2 ? 'white' : undefined }}
                                  aria-label={rotulo}
                                  title={rotulo}
                                  onClick={() => setPilhaAberta({ bloco, fileira, pilha: numPilha })}
                                >
                                  <Text fw={700} inherit>
                                    {qtd || '·'}
                                  </Text>
                                </UnstyledButton>
                              </Table.Td>
                            );
                          })}
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                </Table.ScrollContainer>
              </Paper>
            );
          })}
        </Stack>
      </Estado>

      <Drawer
        opened={Boolean(pilhaAberta)}
        onClose={() => setPilhaAberta(null)}
        position="right"
        title={pilhaAberta && `Pilha ${pilhaAberta.bloco}-${String(pilhaAberta.fileira).padStart(2, '0')}-${String(pilhaAberta.pilha).padStart(2, '0')}`}
      >
        <Stack gap="xs">
          {[...pilha].reverse().map((p) => (
            <Paper key={p.id} withBorder p="xs">
              <Group justify="space-between" wrap="nowrap">
                <div>
                  <Text size="xs" c="dimmed">
                    Altura {p.altura}
                  </Text>
                  {p.container ? (
                    <Group gap={6}>
                      <UnstyledButton onClick={() => setDetalhe(p.container.id)} aria-label={`Ver ${p.container.codigo}`}>
                        <Codigo c="indigo">{p.container.codigo}</Codigo>
                      </UnstyledButton>
                      {p.container.bloqueado && (
                        <Badge color="red" size="sm" leftSection={<IconLock size={10} />}>
                          bloqueado
                        </Badge>
                      )}
                    </Group>
                  ) : (
                    <Text size="sm" c="dimmed">
                      livre
                    </Text>
                  )}
                </div>
                {p.container &&
                  (p.id === topo?.id ? (
                    <Button size="xs" variant="light" leftSection={<IconArrowsMove size={14} />} onClick={() => setMover(p)}>
                      Mover
                    </Button>
                  ) : (
                    <Tooltip label="Há container em cima">
                      <Button size="xs" variant="default" disabled>
                        Mover
                      </Button>
                    </Tooltip>
                  ))}
              </Group>
            </Paper>
          ))}
        </Stack>
      </Drawer>

      <MoverModal posicao={mover} aoFechar={() => setMover(null)} />
      <DetalheContainer containerId={detalhe} onClose={() => setDetalhe(null)} />
    </>
  );
}
