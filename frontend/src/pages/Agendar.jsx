/**
 * Agendamento pelo cliente, em 3 passos numa página só:
 * containers (o "carrinho") -> dia e janela -> caminhão. As regras que dariam
 * erro no portão (bloqueio, mistura de operações, 2x20' ou 1x40') aparecem aqui,
 * antes de o caminhão sair, porque a maior parte dos problemas no gate pode ser
 * resolvida antes da chegada.
 */
import { useMemo, useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  CloseButton,
  Group,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Title,
  UnstyledButton,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconCalendarCheck, IconInfoCircle } from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { api, mensagemErro } from '../api';
import { Cabecalho, Codigo, Estado } from '../components/comuns';
import { useSelecao } from '../contexts/SelecaoContext';
import { OPERACAO, diaLocal, fmtHora } from '../util/formato';
import { normalizar, placaValida } from '../util/validacao';

function Passo({ numero, titulo, children }) {
  return (
    <Paper withBorder p="md">
      <Group gap="xs" mb="sm">
        <Badge circle size="lg">
          {numero}
        </Badge>
        <Title order={3} size="h4">
          {titulo}
        </Title>
      </Group>
      {children}
    </Paper>
  );
}

function proximosDias(qtd) {
  return Array.from({ length: qtd }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() + i);
    return diaLocal(d.toISOString());
  });
}

const rotuloDia = (iso) =>
  new Date(`${iso}T12:00:00`).toLocaleDateString('pt-BR', { weekday: 'short', day: '2-digit', month: '2-digit' });

export default function Agendar() {
  const { selecionados, alternar, limpar, operacao } = useSelecao();
  const navegar = useNavigate();
  const qc = useQueryClient();
  const dias = useMemo(() => proximosDias(8), []);
  const [dia, setDia] = useState(dias[0]);
  const [janelaId, setJanelaId] = useState(null);
  const [placa, setPlaca] = useState('');
  const [motorista, setMotorista] = useState('');

  const janelas = useQuery({
    queryKey: ['janelas', 'com-vaga'],
    queryFn: () => api.get('/janelas', { params: { com_vaga: true } }).then((r) => r.data),
  });
  const agora = Date.now();
  const doDia = (janelas.data ?? []).filter((j) => diaLocal(j.inicio) === dia && new Date(j.fim).getTime() > agora);

  const agendar = useMutation({
    mutationFn: () =>
      api
        .post('/agendamentos', {
          janela_id: janelaId,
          operacao,
          container_ids: selecionados.map((c) => c.id),
          placa: normalizar(placa),
          motorista: motorista.trim(),
        })
        .then((r) => r.data),
    onSuccess: (ag) => {
      notifications.show({
        color: 'green',
        icon: <IconCalendarCheck />,
        title: `Agendamento ${ag.numero} confirmado`,
        message: 'Informe este número ou a placa ao motorista: é o que o portão vai pedir.',
        autoClose: 10000,
      });
      limpar();
      qc.invalidateQueries();
      navegar('/meus-agendamentos');
    },
    onError: (e) => {
      notifications.show({ color: 'red', title: 'Não foi possível agendar', message: mensagemErro(e) });
      qc.invalidateQueries({ queryKey: ['janelas'] }); // a janela pode ter lotado
    },
  });

  const pronto = selecionados.length && janelaId && placaValida(placa) && motorista.trim().length >= 2;

  return (
    <>
      <Cabecalho titulo="Agendar" descricao="Reserve a janela de entrada ou saída do caminhão" />
      <Stack>
        <Passo numero={1} titulo="Containers">
          {selecionados.length === 0 ? (
            <Alert icon={<IconInfoCircle />} color="indigo">
              Nenhum container escolhido.{' '}
              <Text component={Link} to="/meus-containers" c="indigo" fw={600} inherit>
                Escolha em Meus containers
              </Text>{' '}
              (até 2 de 20&apos; ou 1 de 40&apos; por caminhão).
            </Alert>
          ) : (
            <Stack gap="xs">
              {selecionados.map((c) => (
                <Group key={c.id} justify="space-between" wrap="nowrap">
                  <Group gap="xs">
                    <Codigo>{c.codigo}</Codigo>
                    <Badge variant="outline">{c.tamanho}&apos;</Badge>
                  </Group>
                  <CloseButton aria-label={`Remover ${c.codigo}`} onClick={() => alternar(c)} />
                </Group>
              ))}
              <Text size="sm">
                Operação: <b>{OPERACAO[operacao]}</b>
                {operacao === 'retirada' ? ' (o caminhão vem buscar)' : ' (o caminhão vem deixar)'}
              </Text>
            </Stack>
          )}
        </Passo>

        <Passo numero={2} titulo="Dia e janela">
          <Group gap="xs" mb="md" wrap="wrap" role="radiogroup" aria-label="Dia">
            {dias.map((d) => (
              <Button
                key={d}
                size="xs"
                variant={d === dia ? 'filled' : 'default'}
                role="radio"
                aria-checked={d === dia}
                onClick={() => {
                  setDia(d);
                  setJanelaId(null);
                }}
              >
                {rotuloDia(d)}
              </Button>
            ))}
          </Group>
          <Estado consulta={janelas} vazio={doDia.length === 0} mensagemVazia="Sem janelas com vaga neste dia.">
            <SimpleGrid cols={{ base: 2, xs: 3, sm: 4, md: 6 }} role="radiogroup" aria-label="Janela">
              {doDia.map((j) => {
                const escolhida = j.id === janelaId;
                return (
                  <UnstyledButton
                    key={j.id}
                    role="radio"
                    aria-checked={escolhida}
                    onClick={() => setJanelaId(j.id)}
                    p="xs"
                    style={{
                      borderRadius: 'var(--mantine-radius-md)',
                      border: `2px solid var(--mantine-color-${escolhida ? 'indigo-6' : 'default-border'})`,
                      background: escolhida ? 'var(--mantine-color-indigo-light)' : undefined,
                    }}
                  >
                    <Text fw={600} size="sm">
                      {fmtHora(j.inicio)}–{fmtHora(j.fim)}
                    </Text>
                    <Text size="xs" c={j.vagas_livres <= 1 ? 'orange' : 'dimmed'}>
                      {j.vagas_livres} vaga(s)
                    </Text>
                  </UnstyledButton>
                );
              })}
            </SimpleGrid>
          </Estado>
        </Passo>

        <Passo numero={3} titulo="Caminhão">
          <SimpleGrid cols={{ base: 1, sm: 2 }}>
            <TextInput
              label="Placa"
              placeholder="ABC1D23"
              value={placa}
              onChange={(e) => setPlaca(e.currentTarget.value)}
              error={placa && !placaValida(placa) ? 'Use ABC1234 ou ABC1D23' : null}
              styles={{ input: { textTransform: 'uppercase' } }}
            />
            <TextInput label="Motorista" value={motorista} onChange={(e) => setMotorista(e.currentTarget.value)} />
          </SimpleGrid>
        </Passo>

        <Group justify="flex-end">
          <Button size="md" leftSection={<IconCalendarCheck />} disabled={!pronto} loading={agendar.isPending} onClick={() => agendar.mutate()}>
            Confirmar agendamento
          </Button>
        </Group>
      </Stack>
    </>
  );
}
