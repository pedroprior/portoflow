import { useEffect } from 'react';
import { Button, Group, Modal, NumberInput, Select, SimpleGrid, Stack, Switch, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, errosPorCampo, mensagemErro } from '../api';
import { codigoContainerValido, normalizar } from '../util/validacao';

const VAZIO = { codigo: '', tamanho: '20', tipo: 'dry', peso_kg: '', cheio: true, perigoso: false, cliente_id: null, escala_id: null };

/** Cadastro (sem `container`) ou edição (com `container`) de container. */
export function FormContainer({ aberto, aoFechar, container = null }) {
  const edicao = Boolean(container);
  const qc = useQueryClient();
  const escalas = useQuery({ queryKey: ['escalas'], queryFn: () => api.get('/escalas').then((r) => r.data), enabled: aberto });
  const clientes = useQuery({ queryKey: ['clientes'], queryFn: () => api.get('/clientes').then((r) => r.data), enabled: aberto });

  const form = useForm({
    initialValues: VAZIO,
    validate: {
      codigo: (v) => (edicao || codigoContainerValido(v) ? null : 'Código ISO 6346 inválido (confira o dígito verificador)'),
      peso_kg: (v) => (Number(v) > 0 ? null : 'Peso deve ser maior que zero'),
      cliente_id: (v) => (edicao || v ? null : 'Escolha o cliente'),
      escala_id: (v) => (v ? null : 'Escolha a escala'),
    },
  });

  useEffect(() => {
    if (!aberto) return;
    form.setValues(
      container
        ? {
            codigo: container.codigo,
            tamanho: String(container.tamanho),
            tipo: container.tipo,
            peso_kg: Number(container.peso_kg),
            cheio: container.cheio,
            perigoso: container.perigoso,
            cliente_id: String(container.cliente_id),
            escala_id: String(container.escala_id),
          }
        : VAZIO,
    );
    form.resetDirty();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [aberto, container?.id]);

  const salvar = useMutation({
    mutationFn: (v) => {
      const comum = {
        tamanho: Number(v.tamanho),
        tipo: v.tipo,
        peso_kg: Number(v.peso_kg).toFixed(2),
        cheio: v.cheio,
        perigoso: v.perigoso,
        escala_id: Number(v.escala_id),
      };
      return edicao
        ? api.put(`/containers/${container.id}`, comum)
        : api.post('/containers', { ...comum, codigo: normalizar(v.codigo), cliente_id: Number(v.cliente_id) });
    },
    onSuccess: ({ data }) => {
      notifications.show({ color: 'green', message: `${data.codigo} ${edicao ? 'atualizado' : 'cadastrado'}` });
      qc.invalidateQueries({ queryKey: ['containers'] });
      qc.invalidateQueries({ queryKey: ['container'] });
      aoFechar();
    },
    onError: (e) => {
      form.setErrors(errosPorCampo(e));
      notifications.show({ color: 'red', title: 'Não salvo', message: mensagemErro(e) });
    },
  });

  return (
    <Modal opened={aberto} onClose={aoFechar} title={edicao ? `Editar ${container.codigo}` : 'Novo container'} size="lg">
      <form onSubmit={form.onSubmit((v) => salvar.mutate(v))} noValidate>
        <Stack>
          <TextInput
            label="Código (ISO 6346)"
            placeholder="CSQU3054383"
            disabled={edicao}
            description={edicao ? 'O código não muda; para corrigir, desative e cadastre de novo' : null}
            data-autofocus
            styles={{ input: { textTransform: 'uppercase', fontFamily: 'var(--mantine-font-family-monospace)' } }}
            {...form.getInputProps('codigo')}
          />
          <SimpleGrid cols={{ base: 1, xs: 3 }}>
            <Select label="Tamanho" data={[{ value: '20', label: "20'" }, { value: '40', label: "40'" }]} allowDeselect={false} {...form.getInputProps('tamanho')} />
            <Select label="Tipo" data={[{ value: 'dry', label: 'Dry' }, { value: 'reefer', label: 'Refrigerado' }]} allowDeselect={false} {...form.getInputProps('tipo')} />
            <NumberInput label="Peso (kg)" min={0.01} decimalScale={2} decimalSeparator="," thousandSeparator="." {...form.getInputProps('peso_kg')} />
          </SimpleGrid>
          <SimpleGrid cols={{ base: 1, xs: 2 }}>
            <Select
              label="Cliente"
              searchable
              disabled={edicao}
              data={(clientes.data ?? []).filter((c) => c.ativo || edicao).map((c) => ({ value: String(c.id), label: c.razao_social }))}
              {...form.getInputProps('cliente_id')}
            />
            <Select
              label="Escala (navio / viagem)"
              searchable
              data={(escalas.data ?? []).map((e) => ({ value: String(e.id), label: `${e.navio.nome} · ${e.viagem}` }))}
              {...form.getInputProps('escala_id')}
            />
          </SimpleGrid>
          <Group>
            <Switch label="Cheio" {...form.getInputProps('cheio', { type: 'checkbox' })} />
            <Switch label="Carga perigosa" color="orange" {...form.getInputProps('perigoso', { type: 'checkbox' })} />
          </Group>
          <Button type="submit" loading={salvar.isPending}>
            {edicao ? 'Salvar alterações' : 'Cadastrar'}
          </Button>
        </Stack>
      </form>
    </Modal>
  );
}
