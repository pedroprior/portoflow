import { useState } from 'react';
import { Button, Group, Modal, Pagination, SegmentedControl, Stack, Table, Text } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconCalendarPlus, IconX } from '@tabler/icons-react';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api, mensagemErro } from '../api';
import { BadgeStatus, Cabecalho, Codigo, Estado } from '../components/comuns';
import { useAuth } from '../contexts/AuthContext';
import { OPERACAO, STATUS_AGENDAMENTO, fmtJanela } from '../util/formato';

export default function Agendamentos() {
  const { usuario } = useAuth();
  const externo = usuario.papel === 'externo';
  const qc = useQueryClient();
  const [status, setStatus] = useState(externo ? '' : 'confirmado');
  const [pagina, setPagina] = useState(1);
  const [cancelar, setCancelar] = useState(null);

  const consulta = useQuery({
    queryKey: ['agendamentos', externo, status, pagina],
    queryFn: () =>
      api
        .get(externo ? '/agendamentos/meus' : '/agendamentos', {
          params: { status: status || undefined, pagina, tamanho_pagina: 15 },
        })
        .then((r) => r.data),
    placeholderData: keepPreviousData,
  });

  const cancelamento = useMutation({
    mutationFn: (id) => api.patch(`/agendamentos/${id}/status`, { status: 'cancelado' }),
    onSuccess: () => {
      notifications.show({ color: 'green', message: 'Agendamento cancelado; a vaga voltou para a janela' });
      qc.invalidateQueries({ queryKey: ['agendamentos'] });
      qc.invalidateQueries({ queryKey: ['janelas'] });
      setCancelar(null);
    },
    onError: (e) => notifications.show({ color: 'red', message: mensagemErro(e) }),
  });

  const itens = (consulta.data?.itens ?? []).filter((a) => !externo || !status || a.status === status);

  return (
    <>
      <Cabecalho titulo={externo ? 'Meus agendamentos' : 'Agendamentos'}>
        {externo && (
          <Button component={Link} to="/agendar" leftSection={<IconCalendarPlus size={18} />}>
            Novo agendamento
          </Button>
        )}
      </Cabecalho>

      {!externo && (
        <SegmentedControl
          mb="md"
          aria-label="Filtrar por status"
          value={status}
          onChange={(v) => {
            setStatus(v);
            setPagina(1);
          }}
          data={[
            { value: 'confirmado', label: 'Confirmados' },
            { value: 'cumprido', label: 'Cumpridos' },
            { value: 'cancelado', label: 'Cancelados' },
            { value: '', label: 'Todos' },
          ]}
        />
      )}

      <Estado consulta={consulta} vazio={itens.length === 0} mensagemVazia="Nenhum agendamento.">
        <Stack>
          <Table.ScrollContainer minWidth={720}>
            <Table verticalSpacing="sm" highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Número</Table.Th>
                  <Table.Th>Janela</Table.Th>
                  <Table.Th>Operação</Table.Th>
                  <Table.Th>Containers</Table.Th>
                  <Table.Th>Caminhão</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th />
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {itens.map((a) => (
                  <Table.Tr key={a.id}>
                    <Table.Td>
                      <Codigo>{a.numero}</Codigo>
                    </Table.Td>
                    <Table.Td>{fmtJanela(a.janela)}</Table.Td>
                    <Table.Td>{OPERACAO[a.operacao]}</Table.Td>
                    <Table.Td>
                      {a.containers.map((c) => (
                        <Codigo key={c.id} display="block" fw={400}>
                          {c.codigo}
                        </Codigo>
                      ))}
                    </Table.Td>
                    <Table.Td>
                      <Codigo fw={400}>{a.placa}</Codigo>
                      <Text size="xs" c="dimmed">
                        {a.motorista}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <BadgeStatus mapa={STATUS_AGENDAMENTO} valor={a.status} />
                    </Table.Td>
                    <Table.Td>
                      {a.status === 'confirmado' && (
                        <Button size="xs" variant="subtle" color="red" leftSection={<IconX size={14} />} onClick={() => setCancelar(a)}>
                          Cancelar
                        </Button>
                      )}
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
          {consulta.data?.total_paginas > 1 && (
            <Pagination total={consulta.data.total_paginas} value={pagina} onChange={setPagina} size="sm" />
          )}
        </Stack>
      </Estado>

      <Modal opened={Boolean(cancelar)} onClose={() => setCancelar(null)} title="Cancelar agendamento?">
        <Text size="sm" mb="md">
          O agendamento <Codigo>{cancelar?.numero}</Codigo> será cancelado e a vaga volta a ficar livre.
        </Text>
        <Group justify="flex-end">
          <Button variant="default" onClick={() => setCancelar(null)}>
            Voltar
          </Button>
          <Button color="red" loading={cancelamento.isPending} onClick={() => cancelamento.mutate(cancelar.id)}>
            Cancelar agendamento
          </Button>
        </Group>
      </Modal>
    </>
  );
}
