import { Alert, Center, Loader } from '@mantine/core';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

/**
 * Esconde a tela de quem não pode vê-la. É só conveniência: a segurança de
 * verdade está na API, que devolve 401/403 de qualquer forma.
 */
export function RotaProtegida({ papeis, children }) {
  const { usuario, carregando } = useAuth();
  const local = useLocation();

  if (carregando) {
    return (
      <Center h="60vh">
        <Loader aria-label="Carregando sessão" />
      </Center>
    );
  }
  if (!usuario) return <Navigate to="/entrar" replace state={{ de: local.pathname }} />;
  if (papeis && !papeis.includes(usuario.papel)) {
    return (
      <Alert color="orange" title="Sem permissão">
        Seu perfil não tem acesso a esta tela.
      </Alert>
    );
  }
  return children;
}

export const INICIO_POR_PAPEL = { operador: '/portao', admin: '/containers', externo: '/meus-containers' };
