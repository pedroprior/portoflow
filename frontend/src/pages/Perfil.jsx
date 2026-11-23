import { Badge, Button, Group, Paper, PasswordInput, Stack, Text, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { api, errosPorCampo, mensagemErro } from '../api';
import { Cabecalho } from '../components/comuns';
import { useAuth } from '../contexts/AuthContext';
import { PAPEL } from '../util/formato';

export default function Perfil() {
  const { usuario, setUsuario } = useAuth();
  const form = useForm({
    initialValues: { nome: usuario.nome, senha_atual: '', nova_senha: '' },
    validate: {
      nome: (v) => (v.trim().length >= 2 ? null : 'Informe seu nome'),
      nova_senha: (v) => (!v || v.length >= 8 ? null : 'Mínimo de 8 caracteres'),
      senha_atual: (v, valores) => (valores.nova_senha && !v ? 'Informe a senha atual' : null),
    },
  });

  const salvar = form.onSubmit(async (v) => {
    try {
      const { data } = await api.put('/usuarios/me', {
        nome: v.nome,
        ...(v.nova_senha ? { senha_atual: v.senha_atual, nova_senha: v.nova_senha } : {}),
      });
      setUsuario(data);
      form.setValues({ nome: data.nome, senha_atual: '', nova_senha: '' });
      notifications.show({ color: 'green', message: 'Perfil atualizado' });
    } catch (e) {
      form.setErrors(errosPorCampo(e));
      notifications.show({ color: 'red', message: mensagemErro(e) });
    }
  });

  return (
    <>
      <Cabecalho titulo="Meu perfil" />
      <Paper withBorder p="md" maw={480}>
        <Group mb="md" gap="xs">
          <Text size="sm">{usuario.email}</Text>
          <Badge variant="light">{PAPEL[usuario.papel]}</Badge>
        </Group>
        <form onSubmit={salvar} noValidate>
          <Stack>
            <TextInput label="Nome" {...form.getInputProps('nome')} />
            <PasswordInput label="Senha atual" autoComplete="current-password" {...form.getInputProps('senha_atual')} />
            <PasswordInput
              label="Nova senha"
              description="Deixe em branco para manter a atual"
              autoComplete="new-password"
              {...form.getInputProps('nova_senha')}
            />
            <Button type="submit" loading={form.submitting}>
              Salvar
            </Button>
          </Stack>
        </form>
      </Paper>
    </>
  );
}
