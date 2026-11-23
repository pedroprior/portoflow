import { useState } from 'react';
import {
  Badge,
  Button,
  Group,
  Modal,
  NumberInput,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { IconCheck, IconPencil, IconPlus, IconTrash } from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, errosPorCampo, mensagemErro } from '../api';
import { BadgeStatus, Cabecalho, Codigo, Estado } from '../components/comuns';
import { useAuth } from '../contexts/AuthContext';
import {
  PAPEL,
  STATUS_ESCALA,
  STATUS_USUARIO,
  diaLocal,
  fmtDataHora,
  fmtHora,
  isoParaLocal,
  localParaIso,
} from '../util/formato';
import { cnpjValido } from '../util/validacao';

/** Mutation com aviso de sucesso/erro e atualização das listas. */
function useAcao(fn, sucesso, chaves) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      notifications.show({ color: 'green', message: sucesso });
      chaves.forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
    },
    onError: (e) => notifications.show({ color: 'red', message: mensagemErro(e) }),
  });
}

function FormModal({ titulo, aberto, aoFechar, form, aoSalvar, children }) {
  const enviar = form.onSubmit(async (v) => {
    try {
      await aoSalvar(v);
      form.reset();
      aoFechar();
    } catch (e) {
      form.setErrors(errosPorCampo(e));
    }
  });
  return (
    <Modal opened={aberto} onClose={aoFechar} title={titulo}>
      <form onSubmit={enviar} noValidate>
        <Stack>
          {children}
          <Button type="submit" loading={form.submitting}>
            Salvar
          </Button>
        </Stack>
      </form>
    </Modal>
  );
}

// --- Escalas ----------------------------------------------------------------

const PROXIMO_STATUS = { prevista: ['atracada', 'Marcar atracada'], atracada: ['encerrada', 'Encerrar'] };

function Escalas() {
  const escalas = useQuery({ queryKey: ['escalas'], queryFn: () => api.get('/escalas').then((r) => r.data) });
  const navios = useQuery({ queryKey: ['navios'], queryFn: () => api.get('/navios').then((r) => r.data) });
  const [modal, setModal] = useState(null); // 'escala' | 'navio'
  const [editando, setEditando] = useState(null); // escala em edição
  const avancar = useAcao(({ id, status }) => api.put(`/escalas/${id}`, { status }), 'Escala atualizada', ['escalas']);
  const desativar = useAcao((id) => api.delete(`/escalas/${id}`), 'Escala desativada', ['escalas']);
  const salvarEscala = useAcao((v) => api.post('/escalas', v), 'Escala cadastrada', ['escalas']);
  const editarEscala = useAcao(({ id, ...v }) => api.put(`/escalas/${id}`, v), 'Escala atualizada', ['escalas']);
  const salvarNavio = useAcao((v) => api.post('/navios', v), 'Navio cadastrado', ['navios']);

  const formEscala = useForm({
    initialValues: { navio_id: null, viagem: '', eta: '', etd: '' },
    validate: {
      navio_id: (v) => (v ? null : 'Escolha o navio'),
      viagem: (v) => (v.trim() ? null : 'Informe a viagem'),
      eta: (v) => (v ? null : 'Informe a previsão de atracação'),
      etd: (v, t) => (v && t.eta && v > t.eta ? null : 'Saída deve ser depois da atracação'),
    },
  });
  const formNavio = useForm({
    initialValues: { nome: '', imo: '', armador: '' },
    validate: {
      nome: (v) => (v.trim().length >= 2 ? null : 'Informe o nome'),
      imo: (v) => (/^\d{7}$/.test(v) ? null : 'IMO tem 7 dígitos'),
      armador: (v) => (v.trim().length >= 2 ? null : 'Informe o armador'),
    },
  });

  return (
    <>
      <Group mb="sm">
        <Button leftSection={<IconPlus size={16} />} onClick={() => setModal('escala')}>
          Nova escala
        </Button>
        <Button variant="default" leftSection={<IconPlus size={16} />} onClick={() => setModal('navio')}>
          Novo navio
        </Button>
      </Group>
      <Estado consulta={escalas} vazio={escalas.data?.length === 0} mensagemVazia="Nenhuma escala ativa.">
        <Table.ScrollContainer minWidth={640}>
          <Table verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Navio</Table.Th>
                <Table.Th>Viagem</Table.Th>
                <Table.Th>Atracação (prev.)</Table.Th>
                <Table.Th>Saída (prev.)</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {escalas.data?.map((e) => (
                <Table.Tr key={e.id}>
                  <Table.Td>{e.navio.nome}</Table.Td>
                  <Table.Td>
                    <Codigo fw={400}>{e.viagem}</Codigo>
                  </Table.Td>
                  <Table.Td>{fmtDataHora(e.eta)}</Table.Td>
                  <Table.Td>{fmtDataHora(e.etd)}</Table.Td>
                  <Table.Td>
                    <BadgeStatus mapa={STATUS_ESCALA} valor={e.status} />
                  </Table.Td>
                  <Table.Td>
                    <Group gap={4} wrap="nowrap" justify="flex-end">
                      {PROXIMO_STATUS[e.status] && (
                        <Button size="xs" variant="light" onClick={() => avancar.mutate({ id: e.id, status: PROXIMO_STATUS[e.status][0] })}>
                          {PROXIMO_STATUS[e.status][1]}
                        </Button>
                      )}
                      <Button
                        size="xs"
                        variant="subtle"
                        aria-label={`Editar escala ${e.viagem}`}
                        onClick={() => {
                          setEditando(e);
                          formEscala.setValues({ navio_id: String(e.navio_id), viagem: e.viagem, eta: isoParaLocal(e.eta), etd: isoParaLocal(e.etd) });
                        }}
                      >
                        <IconPencil size={14} />
                      </Button>
                      <Button size="xs" variant="subtle" color="red" aria-label={`Desativar escala ${e.viagem}`} onClick={() => desativar.mutate(e.id)}>
                        <IconTrash size={14} />
                      </Button>
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Estado>

      <FormModal
        titulo={editando ? `Editar escala ${editando.viagem}` : 'Nova escala'}
        aberto={modal === 'escala' || Boolean(editando)}
        aoFechar={() => {
          setModal(null);
          setEditando(null);
          formEscala.reset();
        }}
        form={formEscala}
        aoSalvar={(v) => {
          const datas = { viagem: v.viagem, eta: localParaIso(v.eta), etd: localParaIso(v.etd) };
          return editando
            ? editarEscala.mutateAsync({ id: editando.id, ...datas })
            : salvarEscala.mutateAsync({ ...datas, navio_id: Number(v.navio_id) });
        }}
      >
        <Select
          label="Navio"
          disabled={Boolean(editando)}
          data={(navios.data ?? []).map((n) => ({ value: String(n.id), label: `${n.nome} (IMO ${n.imo})` }))}
          searchable
          {...formEscala.getInputProps('navio_id')}
        />
        <TextInput label="Viagem" placeholder="024S" {...formEscala.getInputProps('viagem')} />
        <SimpleGrid cols={{ base: 1, xs: 2 }}>
          <TextInput type="datetime-local" label="Previsão de atracação" {...formEscala.getInputProps('eta')} />
          <TextInput type="datetime-local" label="Previsão de saída" {...formEscala.getInputProps('etd')} />
        </SimpleGrid>
      </FormModal>

      <FormModal
        titulo="Novo navio"
        aberto={modal === 'navio'}
        aoFechar={() => setModal(null)}
        form={formNavio}
        aoSalvar={(v) => salvarNavio.mutateAsync(v)}
      >
        <TextInput label="Nome" {...formNavio.getInputProps('nome')} />
        <TextInput label="Número IMO" inputMode="numeric" {...formNavio.getInputProps('imo')} />
        <TextInput label="Armador" {...formNavio.getInputProps('armador')} />
      </FormModal>
    </>
  );
}

// --- Janelas ----------------------------------------------------------------

function Janelas() {
  const [dia, setDia] = useState(diaLocal());
  const janelas = useQuery({ queryKey: ['janelas', 'todas'], queryFn: () => api.get('/janelas').then((r) => r.data) });
  const remover = useAcao((id) => api.delete(`/janelas/${id}`), 'Janela removida', ['janelas']);
  const salvar = useAcao((v) => api.post('/janelas', v), 'Janela criada', ['janelas']);
  const form = useForm({
    initialValues: { inicio: '', horas: 1, vagas_total: 5 },
    validate: { inicio: (v) => (v ? null : 'Informe o início') },
  });
  const doDia = (janelas.data ?? []).filter((j) => diaLocal(j.inicio) === dia);

  const criar = form.onSubmit(async (v) => {
    const inicio = new Date(v.inicio);
    const fim = new Date(inicio.getTime() + v.horas * 3600_000);
    try {
      await salvar.mutateAsync({ inicio: inicio.toISOString(), fim: fim.toISOString(), vagas_total: v.vagas_total });
    } catch (e) {
      form.setErrors(errosPorCampo(e));
    }
  });

  return (
    <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
      <div>
        <TextInput type="date" label="Dia" value={dia} onChange={(e) => setDia(e.currentTarget.value)} mb="sm" maw={200} />
        <Estado consulta={janelas} vazio={doDia.length === 0} mensagemVazia="Nenhuma janela neste dia.">
          <Table verticalSpacing={6}>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Horário</Table.Th>
                <Table.Th>Vagas livres</Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {doDia.map((j) => (
                <Table.Tr key={j.id}>
                  <Table.Td>
                    {fmtHora(j.inicio)}–{fmtHora(j.fim)}
                  </Table.Td>
                  <Table.Td>
                    {j.vagas_livres} / {j.vagas_total}
                  </Table.Td>
                  <Table.Td ta="right">
                    {j.vagas_livres === j.vagas_total && (
                      <Button size="xs" variant="subtle" color="red" aria-label="Remover janela" onClick={() => remover.mutate(j.id)}>
                        <IconTrash size={14} />
                      </Button>
                    )}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Estado>
      </div>
      <form onSubmit={criar} noValidate>
        <Stack>
          <Text fw={600}>Nova janela</Text>
          <TextInput type="datetime-local" label="Início" {...form.getInputProps('inicio')} />
          <SimpleGrid cols={2}>
            <NumberInput label="Duração (h)" min={1} max={12} {...form.getInputProps('horas')} />
            <NumberInput label="Vagas" min={1} max={500} {...form.getInputProps('vagas_total')} />
          </SimpleGrid>
          <Button type="submit" leftSection={<IconPlus size={16} />} loading={salvar.isPending}>
            Criar janela
          </Button>
        </Stack>
      </form>
    </SimpleGrid>
  );
}

// --- Usuários ---------------------------------------------------------------

function Usuarios() {
  const { usuario: eu } = useAuth();
  const [filtro, setFiltro] = useState(null);
  const [novo, setNovo] = useState(false);
  const usuarios = useQuery({
    queryKey: ['usuarios', filtro],
    queryFn: () => api.get('/usuarios', { params: { status: filtro || undefined } }).then((r) => r.data),
  });
  const clientes = useQuery({ queryKey: ['clientes'], queryFn: () => api.get('/clientes').then((r) => r.data) });
  const aprovar = useAcao((id) => api.put(`/usuarios/${id}`, { status: 'ativo' }), 'Acesso aprovado', ['usuarios']);
  const desativar = useAcao((id) => api.delete(`/usuarios/${id}`), 'Usuário desativado', ['usuarios']);
  const salvar = useAcao(
    (v) => api.post('/usuarios', { ...v, cliente_id: v.papel === 'externo' ? Number(v.cliente_id) : null }),
    'Usuário criado',
    ['usuarios'],
  );
  const form = useForm({
    initialValues: { nome: '', email: '', senha: '', papel: 'operador', cliente_id: null },
    validate: {
      nome: (v) => (v.trim().length >= 2 ? null : 'Informe o nome'),
      email: (v) => (/^\S+@\S+\.\S+$/.test(v) ? null : 'E-mail inválido'),
      senha: (v) => (v.length >= 8 ? null : 'Mínimo de 8 caracteres'),
      cliente_id: (v, t) => (t.papel !== 'externo' || v ? null : 'Cliente obrigatório para externo'),
    },
  });
  const nomeCliente = Object.fromEntries((clientes.data ?? []).map((c) => [c.id, c.razao_social]));

  return (
    <>
      <Group mb="sm" justify="space-between">
        <Select
          aria-label="Filtrar por status"
          placeholder="Todos os status"
          clearable
          data={[
            { value: 'pendente', label: 'Pendentes de aprovação' },
            { value: 'ativo', label: 'Ativos' },
            { value: 'inativo', label: 'Inativos' },
          ]}
          value={filtro}
          onChange={setFiltro}
        />
        <Button leftSection={<IconPlus size={16} />} onClick={() => setNovo(true)}>
          Novo usuário
        </Button>
      </Group>
      <Estado consulta={usuarios} vazio={usuarios.data?.length === 0} mensagemVazia="Nenhum usuário.">
        <Table.ScrollContainer minWidth={640}>
          <Table verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Nome</Table.Th>
                <Table.Th>Perfil</Table.Th>
                <Table.Th>Cliente</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {usuarios.data?.map((u) => (
                <Table.Tr key={u.id}>
                  <Table.Td>
                    <Text size="sm">{u.nome}</Text>
                    <Text size="xs" c="dimmed">
                      {u.email}
                    </Text>
                  </Table.Td>
                  <Table.Td>{PAPEL[u.papel]}</Table.Td>
                  <Table.Td>{nomeCliente[u.cliente_id] ?? '—'}</Table.Td>
                  <Table.Td>
                    <BadgeStatus mapa={STATUS_USUARIO} valor={u.status} />
                  </Table.Td>
                  <Table.Td>
                    <Group gap={4} justify="flex-end" wrap="nowrap">
                      {u.status === 'pendente' && (
                        <Button size="xs" color="green" leftSection={<IconCheck size={14} />} onClick={() => aprovar.mutate(u.id)}>
                          Aprovar
                        </Button>
                      )}
                      {u.status !== 'inativo' && u.id !== eu.id && (
                        <Button size="xs" variant="subtle" color="red" onClick={() => desativar.mutate(u.id)}>
                          Desativar
                        </Button>
                      )}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Estado>

      <FormModal titulo="Novo usuário" aberto={novo} aoFechar={() => setNovo(false)} form={form} aoSalvar={(v) => salvar.mutateAsync(v)}>
        <TextInput label="Nome" {...form.getInputProps('nome')} />
        <TextInput label="E-mail" type="email" {...form.getInputProps('email')} />
        <TextInput label="Senha inicial" description="O usuário troca em Meu perfil" {...form.getInputProps('senha')} />
        <Select
          label="Perfil"
          allowDeselect={false}
          data={Object.entries(PAPEL).map(([value, label]) => ({ value, label }))}
          {...form.getInputProps('papel')}
        />
        {form.values.papel === 'externo' && (
          <Select
            label="Cliente"
            searchable
            data={(clientes.data ?? []).map((c) => ({ value: String(c.id), label: c.razao_social }))}
            {...form.getInputProps('cliente_id')}
          />
        )}
      </FormModal>
    </>
  );
}

// --- Clientes ---------------------------------------------------------------

function Clientes() {
  const clientes = useQuery({ queryKey: ['clientes'], queryFn: () => api.get('/clientes').then((r) => r.data) });
  const salvar = useAcao((v) => api.post('/clientes', v), 'Cliente cadastrado', ['clientes']);
  const alternar = useAcao(({ id, ativo }) => api.put(`/clientes/${id}`, { ativo }), 'Cliente atualizado', ['clientes']);
  const form = useForm({
    initialValues: { razao_social: '', cnpj: '' },
    validate: {
      razao_social: (v) => (v.trim().length >= 2 ? null : 'Informe a razão social'),
      cnpj: (v) => (cnpjValido(v) ? null : 'CNPJ deve ter 14 dígitos'),
    },
  });
  const criar = form.onSubmit(async (v) => {
    try {
      await salvar.mutateAsync(v);
      form.reset();
    } catch (e) {
      form.setErrors(errosPorCampo(e));
    }
  });

  return (
    <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
      <Estado consulta={clientes} vazio={clientes.data?.length === 0} mensagemVazia="Nenhum cliente.">
        <Table verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Razão social</Table.Th>
              <Table.Th>CNPJ</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {clientes.data?.map((c) => (
              <Table.Tr key={c.id}>
                <Table.Td>
                  {c.razao_social} {!c.ativo && <Badge color="gray">inativo</Badge>}
                </Table.Td>
                <Table.Td>
                  <Codigo fw={400}>{c.cnpj.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5')}</Codigo>
                </Table.Td>
                <Table.Td ta="right">
                  <Button size="xs" variant="subtle" onClick={() => alternar.mutate({ id: c.id, ativo: !c.ativo })}>
                    {c.ativo ? 'Desativar' : 'Reativar'}
                  </Button>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Estado>
      <form onSubmit={criar} noValidate>
        <Stack>
          <Text fw={600}>Novo cliente</Text>
          <TextInput label="Razão social" {...form.getInputProps('razao_social')} />
          <TextInput label="CNPJ" inputMode="numeric" placeholder="00.000.000/0000-00" {...form.getInputProps('cnpj')} />
          <Button type="submit" leftSection={<IconPlus size={16} />} loading={salvar.isPending}>
            Cadastrar cliente
          </Button>
        </Stack>
      </form>
    </SimpleGrid>
  );
}

export default function Cadastros() {
  return (
    <>
      <Cabecalho titulo="Cadastros" descricao="Escalas, janelas de atendimento, usuários e clientes" />
      <Tabs defaultValue="escalas" keepMounted={false}>
        <Tabs.List mb="md">
          <Tabs.Tab value="escalas">Escalas</Tabs.Tab>
          <Tabs.Tab value="janelas">Janelas</Tabs.Tab>
          <Tabs.Tab value="usuarios">Usuários</Tabs.Tab>
          <Tabs.Tab value="clientes">Clientes</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="escalas"><Escalas /></Tabs.Panel>
        <Tabs.Panel value="janelas"><Janelas /></Tabs.Panel>
        <Tabs.Panel value="usuarios"><Usuarios /></Tabs.Panel>
        <Tabs.Panel value="clientes"><Clientes /></Tabs.Panel>
      </Tabs>
    </>
  );
}
