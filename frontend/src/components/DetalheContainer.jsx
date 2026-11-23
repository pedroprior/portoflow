import { useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  Divider,
  Drawer,
  Group,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
  Timeline,
  Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import {
  IconArrowsMove,
  IconDoorEnter,
  IconDoorExit,
  IconLock,
  IconLockOpen,
  IconPencil,
  IconTrash,
} from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, mensagemErro } from '../api';
import { useAuth } from '../contexts/AuthContext';
import { STATUS_CONTAINER, fmtDataHora, fmtPeso } from '../util/formato';
import { BadgeStatus, Codigo, Estado } from './comuns';
import { FormContainer } from './FormContainer';

const ICONE_MOV = { gate_in: IconDoorEnter, gate_out: IconDoorExit, remocao: IconArrowsMove };
const ROTULO_MOV = { gate_in: 'Entrada no portão', gate_out: 'Saída pelo portão', remocao: 'Remoção no pátio' };

function Info({ rotulo, children }) {
  return (
    <div>
      <Text size="xs" c="dimmed">
        {rotulo}
      </Text>
      <Text size="sm">{children}</Text>
    </div>
  );
}

function Bloqueio({ container }) {
  const [motivo, setMotivo] = useState('');
  const qc = useQueryClient();
  const aberto = container.bloqueios.find((b) => !b.liberado_em);
  const atualizar = () => qc.invalidateQueries();

  const bloquear = useMutation({
    mutationFn: () => api.post(`/containers/${container.id}/bloqueios`, { motivo }),
    onSuccess: () => {
      notifications.show({ color: 'orange', message: `${container.codigo} bloqueado` });
      setMotivo('');
      atualizar();
    },
    onError: (e) => notifications.show({ color: 'red', message: mensagemErro(e) }),
  });
  const liberar = useMutation({
    mutationFn: () => api.delete(`/containers/${container.id}/bloqueios/${aberto.id}`),
    onSuccess: () => {
      notifications.show({ color: 'green', message: `${container.codigo} liberado` });
      atualizar();
    },
    onError: (e) => notifications.show({ color: 'red', message: mensagemErro(e) }),
  });

  if (aberto) {
    return (
      <Button color="green" leftSection={<IconLockOpen size={16} />} loading={liberar.isPending} onClick={() => liberar.mutate()}>
        Liberar container
      </Button>
    );
  }
  return (
    <Stack gap="xs">
      <Textarea
        label="Motivo do bloqueio"
        placeholder="Ex.: pendência documental, vistoria da Receita"
        value={motivo}
        onChange={(e) => setMotivo(e.currentTarget.value)}
        autosize
        minRows={2}
      />
      <Button
        color="red"
        variant="light"
        leftSection={<IconLock size={16} />}
        disabled={motivo.trim().length < 3}
        loading={bloquear.isPending}
        onClick={() => bloquear.mutate()}
      >
        Bloquear (cancela retiradas agendadas)
      </Button>
    </Stack>
  );
}

function AcoesEquipe({ container, aoDesativar }) {
  const [editando, setEditando] = useState(false);
  const [confirmar, setConfirmar] = useState(false);
  const qc = useQueryClient();
  const desativar = useMutation({
    mutationFn: () => api.delete(`/containers/${container.id}`),
    onSuccess: () => {
      notifications.show({ color: 'green', message: `${container.codigo} desativado` });
      qc.invalidateQueries({ queryKey: ['containers'] });
      aoDesativar();
    },
    onError: (e) => notifications.show({ color: 'red', title: 'Não desativado', message: mensagemErro(e) }),
  });

  return (
    <>
      <Group grow>
        <Button variant="default" leftSection={<IconPencil size={16} />} onClick={() => setEditando(true)}>
          Editar
        </Button>
        {confirmar ? (
          <Button color="red" loading={desativar.isPending} onClick={() => desativar.mutate()}>
            Confirmar desativação
          </Button>
        ) : (
          <Button
            variant="subtle"
            color="red"
            leftSection={<IconTrash size={16} />}
            disabled={container.status === 'no_patio'}
            title={container.status === 'no_patio' ? 'Container no pátio não pode ser desativado' : undefined}
            onClick={() => setConfirmar(true)}
          >
            Desativar
          </Button>
        )}
      </Group>
      <FormContainer aberto={editando} aoFechar={() => setEditando(false)} container={container} />
    </>
  );
}

export function DetalheContainer({ containerId, onClose }) {
  const { usuario } = useAuth();
  const equipe = usuario.papel !== 'externo';
  const consulta = useQuery({
    queryKey: ['container', containerId],
    queryFn: () => api.get(`/containers/${containerId}`).then((r) => r.data),
    enabled: Boolean(containerId),
  });
  const c = consulta.data;
  const aberto = c?.bloqueios.find((b) => !b.liberado_em);

  return (
    <Drawer opened={Boolean(containerId)} onClose={onClose} position="right" size="md" title="Detalhe do container">
      <Estado consulta={consulta}>
        {c && (
          <Stack>
            <Group justify="space-between">
              <Title order={3}>
                <Codigo inherit>{c.codigo}</Codigo>
              </Title>
              <Group gap={6}>
                <BadgeStatus mapa={STATUS_CONTAINER} valor={c.status} />
                {c.bloqueado && (
                  <Badge color="red" leftSection={<IconLock size={12} />}>
                    Bloqueado
                  </Badge>
                )}
              </Group>
            </Group>

            {aberto && (
              <Alert color="red" title="Bloqueado" icon={<IconLock />}>
                {aberto.motivo} · desde {fmtDataHora(aberto.criado_em)}
              </Alert>
            )}

            <SimpleGrid cols={2} spacing="sm">
              <Info rotulo="Posição">{c.posicao ? <Codigo>{c.posicao.endereco}</Codigo> : '—'}</Info>
              <Info rotulo="Navio / viagem">
                {c.escala.navio_nome} · {c.escala.viagem}
              </Info>
              <Info rotulo="Tamanho e tipo">
                {c.tamanho}&apos; {c.tipo === 'reefer' ? 'refrigerado' : 'dry'}
              </Info>
              <Info rotulo="Peso">{fmtPeso(c.peso_kg)}</Info>
              <Info rotulo="Carga">{c.cheio ? 'Cheio' : 'Vazio'}</Info>
              <Info rotulo="Perigoso">{c.perigoso ? 'Sim' : 'Não'}</Info>
            </SimpleGrid>

            {equipe && <AcoesEquipe key={c.id} container={c} aoDesativar={onClose} />}

            {usuario.papel === 'admin' && (
              <>
                <Divider label="Bloqueio" labelPosition="left" />
                <Bloqueio container={c} />
              </>
            )}

            <Divider label="Histórico" labelPosition="left" />
            {c.movimentacoes.length === 0 ? (
              <Text size="sm" c="dimmed">
                Ainda não entrou no terminal.
              </Text>
            ) : (
              <Timeline bulletSize={24} lineWidth={2} active={c.movimentacoes.length}>
                {[...c.movimentacoes].reverse().map((m) => {
                  const Icone = ICONE_MOV[m.tipo];
                  return (
                    <Timeline.Item key={m.id} bullet={<Icone size={14} />} title={ROTULO_MOV[m.tipo]}>
                      <Text size="sm">
                        {m.origem ? m.origem.endereco : 'portão'} → {m.destino ? m.destino.endereco : 'portão'}
                      </Text>
                      {m.observacao && (
                        <Text size="xs" c="orange">
                          {m.observacao}
                        </Text>
                      )}
                      <Text size="xs" c="dimmed">
                        {fmtDataHora(m.criado_em)}
                      </Text>
                    </Timeline.Item>
                  );
                })}
              </Timeline>
            )}
          </Stack>
        )}
      </Estado>
    </Drawer>
  );
}
