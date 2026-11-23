import { AppShell, Badge, Burger, Button, Group, NavLink, Text, ThemeIcon } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import {
  IconBuildingWarehouse,
  IconCalendarPlus,
  IconCalendarTime,
  IconContainer,
  IconDoorEnter,
  IconLogout,
  IconSettings,
  IconUser,
} from '@tabler/icons-react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useSelecao } from '../contexts/SelecaoContext';
import { PAPEL } from '../util/formato';

const MENUS = {
  operador: [
    { para: '/portao', rotulo: 'Portão', icone: IconDoorEnter },
    { para: '/patio', rotulo: 'Pátio', icone: IconBuildingWarehouse },
    { para: '/containers', rotulo: 'Containers', icone: IconContainer },
    { para: '/agendamentos', rotulo: 'Agendamentos', icone: IconCalendarTime },
  ],
  admin: [
    { para: '/containers', rotulo: 'Containers', icone: IconContainer },
    { para: '/portao', rotulo: 'Portão', icone: IconDoorEnter },
    { para: '/patio', rotulo: 'Pátio', icone: IconBuildingWarehouse },
    { para: '/agendamentos', rotulo: 'Agendamentos', icone: IconCalendarTime },
    { para: '/cadastros', rotulo: 'Cadastros', icone: IconSettings },
  ],
  externo: [
    { para: '/meus-containers', rotulo: 'Meus containers', icone: IconContainer },
    { para: '/agendar', rotulo: 'Agendar', icone: IconCalendarPlus },
    { para: '/meus-agendamentos', rotulo: 'Meus agendamentos', icone: IconCalendarTime },
  ],
};

export function Layout() {
  const [aberto, { toggle, close }] = useDisclosure();
  const { usuario, sair } = useAuth();
  const { selecionados } = useSelecao();
  const { pathname } = useLocation();
  const menu = [...(MENUS[usuario.papel] ?? []), { para: '/perfil', rotulo: 'Meu perfil', icone: IconUser }];

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 220, breakpoint: 'sm', collapsed: { mobile: !aberto } }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between" wrap="nowrap">
          <Group gap="xs" wrap="nowrap">
            <Burger opened={aberto} onClick={toggle} hiddenFrom="sm" size="sm" aria-label="Abrir menu" />
            <ThemeIcon size="md" radius="sm" aria-hidden>
              <IconContainer size={18} />
            </ThemeIcon>
            <Text fw={700}>PortoFlow</Text>
          </Group>
          <Group gap="sm" wrap="nowrap">
            <Text size="sm" visibleFrom="xs" truncate maw={180}>
              {usuario.nome}
            </Text>
            <Badge variant="light" visibleFrom="xs">
              {PAPEL[usuario.papel]}
            </Badge>
            <Button variant="subtle" size="compact-sm" leftSection={<IconLogout size={16} />} onClick={sair}>
              Sair
            </Button>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="xs" component="nav" aria-label="Menu principal">
        {menu.map(({ para, rotulo, icone: Icone }) => (
          <NavLink
            key={para}
            component={Link}
            to={para}
            label={rotulo}
            leftSection={<Icone size={18} aria-hidden />}
            active={pathname.startsWith(para)}
            onClick={close}
            rightSection={
              para === '/agendar' && selecionados.length ? (
                <Badge size="sm" circle aria-label={`${selecionados.length} selecionados`}>
                  {selecionados.length}
                </Badge>
              ) : null
            }
          />
        ))}
      </AppShell.Navbar>

      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
