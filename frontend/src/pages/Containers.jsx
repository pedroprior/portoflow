import { useState } from 'react';
import {
  Badge,
  Button,
  Checkbox,
  Group,
  Pagination,
  Paper,
  SegmentedControl,
  Stack,
  Table,
  Text,
  TextInput,
  Tooltip,
} from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { IconCalendarPlus, IconLock, IconPlus, IconSearch } from '@tabler/icons-react';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { DetalheContainer } from '../components/DetalheContainer';
import { FormContainer } from '../components/FormContainer';
import { BadgeStatus, Cabecalho, Codigo, Estado } from '../components/comuns';
import { useAuth } from '../contexts/AuthContext';
import { motivoBloqueioSelecao, useSelecao } from '../contexts/SelecaoContext';
import { STATUS_CONTAINER } from '../util/formato';
import { normalizar } from '../util/validacao';

const FILTROS_STATUS = [
  { value: '', label: 'Todos' },
  { value: 'aguardando_chegada', label: 'Aguardando' },
  { value: 'no_patio', label: 'No pátio' },
  { value: 'saiu', label: 'Saiu' },
];

export default function Containers() {
  const { usuario } = useAuth();
  const externo = usuario.papel === 'externo';
  const { selecionados, alternar } = useSelecao();
  const [busca, setBusca] = useState('');
  const [buscaAtrasada] = useDebouncedValue(normalizar(busca), 300);
  const [status, setStatus] = useState('');
  const [pagina, setPagina] = useState(1);
  const [detalhe, setDetalhe] = useState(null);
  const [novo, setNovo] = useState(false);

  const consulta = useQuery({
    queryKey: ['containers', buscaAtrasada, status, pagina],
    queryFn: () =>
      api
        .get('/containers', {
          params: { busca: buscaAtrasada || undefined, status: status || undefined, pagina, tamanho_pagina: 15 },
        })
        .then((r) => r.data),
    placeholderData: keepPreviousData,
  });
  const dados = consulta.data;

  return (
    <>
      <Cabecalho
        titulo={externo ? 'Meus containers' : 'Containers'}
        descricao={externo ? 'Marque até 2 containers e agende a janela do caminhão' : null}
      >
        {externo ? (
          <Button component={Link} to="/agendar" leftSection={<IconCalendarPlus size={18} />} disabled={!selecionados.length}>
            Agendar selecionados ({selecionados.length})
          </Button>
        ) : (
          <Button leftSection={<IconPlus size={18} />} onClick={() => setNovo(true)}>
            Novo container
          </Button>
        )}
      </Cabecalho>

      <Paper withBorder p="sm" mb="md">
        <Group wrap="wrap">
          <TextInput
            aria-label="Buscar por código"
            placeholder="Buscar por código"
            leftSection={<IconSearch size={16} />}
            value={busca}
            onChange={(e) => {
              setBusca(e.currentTarget.value);
              setPagina(1);
            }}
            style={{ flex: '1 1 220px' }}
          />
          <SegmentedControl
            aria-label="Filtrar por status"
            data={FILTROS_STATUS}
            value={status}
            onChange={(v) => {
              setStatus(v);
              setPagina(1);
            }}
          />
        </Group>
      </Paper>

      <Estado consulta={consulta} vazio={dados?.itens.length === 0} mensagemVazia="Nenhum container encontrado.">
        {dados && (
          <Stack>
            <Table.ScrollContainer minWidth={560}>
              <Table highlightOnHover verticalSpacing="sm">
                <Table.Thead>
                  <Table.Tr>
                    {externo && <Table.Th w={40}><Text size="xs" c="dimmed">Agendar</Text></Table.Th>}
                    <Table.Th>Código</Table.Th>
                    <Table.Th>Tipo</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th>Posição</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {dados.itens.map((c) => {
                    const marcado = selecionados.some((s) => s.id === c.id);
                    const motivo = motivoBloqueioSelecao(c, selecionados);
                    return (
                      <Table.Tr key={c.id} className="linha-clicavel" onClick={() => setDetalhe(c.id)}>
                        {externo && (
                          <Table.Td onClick={(e) => e.stopPropagation()}>
                            <Tooltip label={motivo} disabled={!motivo || marcado}>
                              <span>
                                <Checkbox
                                  aria-label={`Selecionar ${c.codigo} para agendar`}
                                  checked={marcado}
                                  disabled={Boolean(motivo) && !marcado}
                                  onChange={() => alternar(c)}
                                />
                              </span>
                            </Tooltip>
                          </Table.Td>
                        )}
                        <Table.Td>
                          <Codigo>{c.codigo}</Codigo>
                        </Table.Td>
                        <Table.Td>
                          {c.tamanho}&apos; {c.tipo === 'reefer' ? 'refrig.' : 'dry'}
                        </Table.Td>
                        <Table.Td>
                          <Group gap={4}>
                            <BadgeStatus mapa={STATUS_CONTAINER} valor={c.status} />
                            {c.bloqueado && (
                              <Badge color="red" variant="filled" leftSection={<IconLock size={10} />}>
                                bloqueado
                              </Badge>
                            )}
                          </Group>
                        </Table.Td>
                        <Table.Td>{c.posicao ? <Codigo fw={400}>{c.posicao.endereco}</Codigo> : '—'}</Table.Td>
                      </Table.Tr>
                    );
                  })}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                {dados.total} container(s)
              </Text>
              <Pagination total={dados.total_paginas} value={pagina} onChange={setPagina} size="sm" />
            </Group>
          </Stack>
        )}
      </Estado>

      <DetalheContainer containerId={detalhe} onClose={() => setDetalhe(null)} />
      {!externo && <FormContainer aberto={novo} aoFechar={() => setNovo(false)} />}
    </>
  );
}
