import { Alert, Badge, Button, Center, Group, Loader, Stack, Text, Title } from '@mantine/core';
import { IconAlertTriangle, IconInbox } from '@tabler/icons-react';
import { mensagemErro } from '../api';

/** Carregando, erro e lista vazia: o mesmo tratamento em toda tela que consome a API. */
export function Estado({ consulta, vazio = false, mensagemVazia = 'Nada encontrado.', children }) {
  if (consulta.isLoading) {
    return (
      <Center py="xl">
        <Loader aria-label="Carregando" />
      </Center>
    );
  }
  if (consulta.isError) {
    return (
      <Alert color="red" icon={<IconAlertTriangle />} title="Não foi possível carregar">
        <Stack gap="xs" align="flex-start">
          <Text size="sm">{mensagemErro(consulta.error)}</Text>
          <Button size="xs" variant="light" color="red" onClick={() => consulta.refetch()}>
            Tentar de novo
          </Button>
        </Stack>
      </Alert>
    );
  }
  if (vazio) {
    return (
      <Stack align="center" gap={4} py="xl" c="dimmed">
        <IconInbox size={32} aria-hidden />
        <Text size="sm">{mensagemVazia}</Text>
      </Stack>
    );
  }
  return children;
}

export function BadgeStatus({ mapa, valor, ...props }) {
  const item = mapa[valor] ?? { rotulo: valor, cor: 'gray' };
  return (
    <Badge color={item.cor} variant="light" {...props}>
      {item.rotulo}
    </Badge>
  );
}

export function Cabecalho({ titulo, descricao, children }) {
  return (
    <Group justify="space-between" align="flex-end" mb="md" wrap="wrap">
      <div>
        <Title order={2}>{titulo}</Title>
        {descricao && (
          <Text c="dimmed" size="sm">
            {descricao}
          </Text>
        )}
      </div>
      {children && <Group gap="sm">{children}</Group>}
    </Group>
  );
}

export function Codigo({ children, ...props }) {
  return (
    <Text component="span" className="codigo" fw={600} {...props}>
      {children}
    </Text>
  );
}
