/**
 * Portão: a tela mais usada pelo operador. Pensada para ser operada só pelo
 * teclado e com o mínimo de decisões:
 *   1. digita a placa (ou o código do container, ou o nº do agendamento) e Enter;
 *   2. o sistema já mostra o que fazer e as pendências, antes de gravar;
 *   3. Enter de novo registra. O campo limpa e volta o foco para o próximo caminhão.
 */
import { useRef, useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  List,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import {
  IconAlertTriangle,
  IconArrowRight,
  IconCircleCheck,
  IconDoorEnter,
  IconDoorExit,
  IconSearch,
  IconTruck,
} from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, mensagemErro } from '../api';
import { BadgeStatus, Cabecalho, Codigo, Estado } from '../components/comuns';
import { OPERACAO, STATUS_CONTAINER, fmtHora, fmtJanela } from '../util/formato';
import { normalizar, placaValida } from '../util/validacao';

// O que o operador deve fazer diante de cada pendência.
const ORIENTACAO = {
  sem_agendamento: 'Peça ao cliente para agendar ou encaminhe ao atendimento.',
  fora_da_janela: 'Encaminhe ao pátio de espera ou peça ao cliente para reagendar.',
  container_bloqueado: 'Saída proibida até o administrador liberar.',
  container_por_baixo: 'Remova antes o container de cima (tela Pátio).',
  patio_cheio: 'Libere espaço no pátio antes de receber.',
  ja_saiu: 'Este container já deixou o terminal.',
};

function ItemPortao({ item, agendamento, focar, aoConcluir }) {
  const qc = useQueryClient();
  const entrada = item.operacao === 'entrega';
  const [placa, setPlaca] = useState(agendamento?.placa ?? '');
  const [justificativa, setJustificativa] = useState('');
  const placaDiverge = agendamento && normalizar(placa) !== agendamento.placa;

  const registrar = useMutation({
    mutationFn: () =>
      api
        .post(entrada ? '/portao/entradas' : '/portao/saidas', {
          codigo_container: item.container.codigo,
          placa: normalizar(placa),
          justificativa: placaDiverge ? justificativa : null,
        })
        .then((r) => r.data),
    onSuccess: (c) => {
      const texto = entrada
        ? `Entrada de ${c.codigo}: levar para ${c.posicao?.endereco}`
        : `Saída de ${c.codigo} registrada`;
      notifications.show({ color: 'green', icon: <IconCircleCheck />, message: texto });
      qc.invalidateQueries({ queryKey: ['patio'] });
      qc.invalidateQueries({ queryKey: ['containers'] });
      aoConcluir(texto);
    },
    onError: (e) => notifications.show({ color: 'red', title: 'Não registrado', message: mensagemErro(e) }),
  });

  const podeEnviar =
    item.pode_registrar && placaValida(placa) && (!placaDiverge || justificativa.trim().length >= 3);

  return (
    <Card withBorder padding="lg">
      <Group justify="space-between" mb="sm">
        <Group gap="xs">
          {entrada ? <IconDoorEnter aria-hidden /> : <IconDoorExit aria-hidden />}
          <Title order={3}>
            <Codigo inherit>{item.container.codigo}</Codigo>
          </Title>
        </Group>
        <Group gap={6}>
          <Badge variant="outline">{item.container.tamanho}&apos;</Badge>
          <BadgeStatus mapa={STATUS_CONTAINER} valor={item.container.status} />
        </Group>
      </Group>

      {item.operacao && (
        <Text size="sm" c="dimmed" mb="sm">
          Operação esperada: <b>{entrada ? 'ENTRADA' : 'SAÍDA'}</b>
          {!entrada && item.container.posicao && <> · retirar de <Codigo>{item.container.posicao.endereco}</Codigo></>}
        </Text>
      )}

      {item.pendencias.length > 0 ? (
        <Alert color="red" icon={<IconAlertTriangle />} title="Não liberar o caminhão">
          <List size="sm" spacing={4}>
            {item.pendencias.map((p) => (
              <List.Item key={p.codigo}>
                <b>{p.mensagem}.</b> {ORIENTACAO[p.codigo]}
              </List.Item>
            ))}
          </List>
        </Alert>
      ) : (
        <Stack gap="sm">
          {entrada && item.posicao_sugerida && (
            <Paper bg="var(--mantine-color-green-light)" p="sm">
              <Text size="sm">Posição no pátio</Text>
              <Group gap="xs">
                <IconArrowRight aria-hidden />
                <Text size="xl" fw={700} className="codigo">
                  {item.posicao_sugerida.endereco}
                </Text>
              </Group>
            </Paper>
          )}
          <TextInput
            label="Placa conferida no caminhão"
            value={placa}
            onChange={(e) => setPlaca(e.currentTarget.value)}
            error={placa && !placaValida(placa) ? 'Placa inválida' : null}
            styles={{ input: { textTransform: 'uppercase' } }}
          />
          {placaDiverge && placaValida(placa) && (
            <Textarea
              label="Justificativa (placa diferente da agendada)"
              description={`Agendada: ${agendamento.placa}`}
              value={justificativa}
              onChange={(e) => setJustificativa(e.currentTarget.value)}
              required
              autosize
            />
          )}
          <Button
            size="lg"
            color="green"
            leftSection={entrada ? <IconDoorEnter /> : <IconDoorExit />}
            disabled={!podeEnviar}
            loading={registrar.isPending}
            onClick={() => registrar.mutate()}
            autoFocus={focar}
            fullWidth
          >
            {entrada ? 'Registrar entrada' : 'Registrar saída'}
          </Button>
        </Stack>
      )}
    </Card>
  );
}

export default function Portao() {
  const campo = useRef(null);
  const [termo, setTermo] = useState('');
  const [busca, setBusca] = useState(null);
  const [concluidos, setConcluidos] = useState([]);
  const [historico, setHistorico] = useState([]);

  const consulta = useQuery({
    queryKey: ['portao', busca],
    queryFn: () => api.get('/portao/consulta', { params: { termo: busca } }).then((r) => r.data),
    enabled: Boolean(busca),
    retry: false,
    staleTime: 0,
  });

  const pesquisar = (e) => {
    e.preventDefault();
    const t = normalizar(termo);
    if (t.length < 3) return;
    setConcluidos([]);
    if (t === busca) consulta.refetch();
    else setBusca(t);
  };

  const dados = consulta.data;
  const pendentes = dados?.itens.filter((i) => !concluidos.includes(i.container.codigo)) ?? [];

  const aoConcluir = (codigo, texto) => {
    setHistorico((h) => [{ texto, hora: new Date().toISOString() }, ...h].slice(0, 6));
    if (pendentes.length <= 1) {
      // Caminhão atendido por completo: limpa e prepara para o próximo.
      setTermo('');
      setBusca(null);
      setConcluidos([]);
      campo.current?.focus();
    } else {
      setConcluidos((c) => [...c, codigo]);
      consulta.refetch(); // atualiza a posição sugerida para o próximo container
    }
  };

  const primeiroLiberado = pendentes.find((i) => i.pode_registrar)?.container.codigo;

  return (
    <>
      <Cabecalho titulo="Portão" descricao="Entrada e saída de caminhões" />

      <Paper withBorder p="md" mb="md">
        <form onSubmit={pesquisar}>
          <Group align="flex-end" wrap="nowrap">
            <TextInput
              ref={campo}
              label="Placa, código do container ou nº do agendamento"
              placeholder="ABC1D23 · MSCU3054389 · AG1A2B3C4D"
              size="lg"
              leftSection={<IconTruck />}
              value={termo}
              onChange={(e) => setTermo(e.currentTarget.value)}
              styles={{ input: { textTransform: 'uppercase', fontFamily: 'var(--mantine-font-family-monospace)' } }}
              autoFocus
              style={{ flex: 1 }}
            />
            <Button type="submit" size="lg" leftSection={<IconSearch />} aria-label="Consultar">
              <Text visibleFrom="sm" inherit>
                Consultar
              </Text>
            </Button>
          </Group>
          <Text size="xs" c="dimmed" mt={6}>
            Dica: pela placa aparecem todos os containers do caminhão. Enter consulta; Enter de novo registra.
          </Text>
        </form>
      </Paper>

      {busca && (
        <Estado consulta={consulta}>
          {dados && (
            <Stack>
              {dados.agendamento && (
                <Paper withBorder p="sm">
                  <Group gap="lg" wrap="wrap">
                    <Text size="sm">
                      Agendamento <Codigo>{dados.agendamento.numero}</Codigo>
                    </Text>
                    <Text size="sm">{OPERACAO[dados.agendamento.operacao]}</Text>
                    <Text size="sm">
                      Placa <Codigo>{dados.agendamento.placa}</Codigo>
                    </Text>
                    <Text size="sm">Motorista {dados.agendamento.motorista}</Text>
                    <Text size="sm">Janela {fmtJanela(dados.agendamento.janela)}</Text>
                  </Group>
                </Paper>
              )}
              <SimpleGrid cols={{ base: 1, md: Math.min(pendentes.length, 2) || 1 }}>
                {pendentes.map((item) => (
                  <ItemPortao
                    key={item.container.id}
                    item={item}
                    agendamento={dados.agendamento}
                    focar={item.container.codigo === primeiroLiberado}
                    aoConcluir={(texto) => aoConcluir(item.container.codigo, texto)}
                  />
                ))}
              </SimpleGrid>
            </Stack>
          )}
        </Estado>
      )}

      {historico.length > 0 && (
        <Paper withBorder p="sm" mt="lg">
          <Text size="sm" fw={600} mb={4}>
            Registrados neste turno
          </Text>
          <List size="sm" spacing={2}>
            {historico.map((h) => (
              <List.Item key={h.hora}>
                {fmtHora(h.hora)} · {h.texto}
              </List.Item>
            ))}
          </List>
        </Paper>
      )}
    </>
  );
}
