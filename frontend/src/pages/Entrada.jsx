import { useState } from 'react';
import {
  Alert,
  Anchor,
  Button,
  Center,
  Group,
  Paper,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  ThemeIcon,
  Title,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { IconAlertTriangle, IconCircleCheck, IconContainer } from '@tabler/icons-react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { api, errosPorCampo, mensagemErro } from '../api';
import { INICIO_POR_PAPEL } from '../components/RotaProtegida';
import { useAuth } from '../contexts/AuthContext';
import { cnpjValido } from '../util/validacao';

function Moldura({ titulo, subtitulo, children }) {
  return (
    <Center mih="100vh" p="md" component="main">
      <Paper withBorder shadow="sm" p="xl" w="100%" maw={400}>
        <Group gap="xs" mb="lg">
          <ThemeIcon size="lg" radius="sm" aria-hidden>
            <IconContainer size={20} />
          </ThemeIcon>
          <div>
            <Title order={1} size="h3">
              {titulo}
            </Title>
            <Text size="sm" c="dimmed">
              {subtitulo}
            </Text>
          </div>
        </Group>
        {children}
      </Paper>
    </Center>
  );
}

export function Login() {
  const { usuario, entrar } = useAuth();
  const navegar = useNavigate();
  const local = useLocation();
  const [erro, setErro] = useState(null);
  const form = useForm({
    initialValues: { email: '', senha: '' },
    validate: {
      email: (v) => (/^\S+@\S+\.\S+$/.test(v) ? null : 'Informe um e-mail válido'),
      senha: (v) => (v ? null : 'Informe a senha'),
    },
  });

  if (usuario) return <Navigate to="/" replace />;

  const enviar = form.onSubmit(async ({ email, senha }) => {
    setErro(null);
    try {
      const u = await entrar(email.trim(), senha);
      navegar(local.state?.de ?? INICIO_POR_PAPEL[u.papel] ?? '/', { replace: true });
    } catch (e) {
      setErro(mensagemErro(e));
    }
  });

  return (
    <Moldura titulo="PortoFlow" subtitulo="Gestão de containers do terminal">
      <form onSubmit={enviar} noValidate>
        <Stack>
          {erro && (
            <Alert color="red" icon={<IconAlertTriangle />} role="alert">
              {erro}
            </Alert>
          )}
          <TextInput label="E-mail" type="email" autoComplete="username" autoFocus {...form.getInputProps('email')} />
          <PasswordInput label="Senha" autoComplete="current-password" {...form.getInputProps('senha')} />
          <Button type="submit" loading={form.submitting} fullWidth>
            Entrar
          </Button>
          <Text size="sm" ta="center">
            Transportadora ou despachante?{' '}
            <Anchor component={Link} to="/cadastro">
              Solicite acesso
            </Anchor>
          </Text>
        </Stack>
      </form>
    </Moldura>
  );
}

export function Cadastro() {
  const [enviado, setEnviado] = useState(false);
  const [erro, setErro] = useState(null);
  const form = useForm({
    initialValues: { nome: '', email: '', senha: '', cnpj: '' },
    validate: {
      nome: (v) => (v.trim().length >= 2 ? null : 'Informe seu nome'),
      email: (v) => (/^\S+@\S+\.\S+$/.test(v) ? null : 'Informe um e-mail válido'),
      senha: (v) => (v.length >= 8 ? null : 'Mínimo de 8 caracteres'),
      cnpj: (v) => (cnpjValido(v) ? null : 'CNPJ deve ter 14 dígitos'),
    },
  });

  const enviar = form.onSubmit(async (valores) => {
    setErro(null);
    try {
      await api.post('/auth/registro', valores);
      setEnviado(true);
    } catch (e) {
      form.setErrors(errosPorCampo(e));
      setErro(mensagemErro(e));
    }
  });

  if (enviado) {
    return (
      <Moldura titulo="Solicitação enviada" subtitulo="Cadastro de cliente">
        <Stack>
          <Alert color="green" icon={<IconCircleCheck />}>
            O administrador do terminal vai conferir seus dados. Assim que aprovar, você já pode entrar.
          </Alert>
          <Button component={Link} to="/entrar" variant="light">
            Voltar ao login
          </Button>
        </Stack>
      </Moldura>
    );
  }

  return (
    <Moldura titulo="Solicitar acesso" subtitulo="Para transportadoras e despachantes">
      <form onSubmit={enviar} noValidate>
        <Stack>
          {erro && (
            <Alert color="red" icon={<IconAlertTriangle />} role="alert">
              {erro}
            </Alert>
          )}
          <TextInput label="Nome" autoComplete="name" {...form.getInputProps('nome')} />
          <TextInput label="E-mail" type="email" autoComplete="email" {...form.getInputProps('email')} />
          <PasswordInput label="Senha" autoComplete="new-password" description="Mínimo de 8 caracteres" {...form.getInputProps('senha')} />
          <TextInput
            label="CNPJ da empresa"
            description="A empresa precisa já ser cliente do terminal"
            inputMode="numeric"
            placeholder="00.000.000/0000-00"
            {...form.getInputProps('cnpj')}
          />
          <Button type="submit" loading={form.submitting} fullWidth>
            Enviar solicitação
          </Button>
          <Anchor component={Link} to="/entrar" size="sm" ta="center">
            Já tenho acesso
          </Anchor>
        </Stack>
      </form>
    </Moldura>
  );
}
