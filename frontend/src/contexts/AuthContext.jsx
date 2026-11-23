import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api, armazenamento } from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [carregando, setCarregando] = useState(Boolean(armazenamento.ler()));
  const queryClient = useQueryClient();

  const sair = useCallback(() => {
    armazenamento.gravar(null);
    setUsuario(null);
    queryClient.clear();
  }, [queryClient]);

  // Restaura a sessão ao recarregar a página.
  useEffect(() => {
    if (!armazenamento.ler()) return;
    api
      .get('/usuarios/me')
      .then((r) => setUsuario(r.data))
      .catch(() => armazenamento.gravar(null))
      .finally(() => setCarregando(false));
  }, []);

  useEffect(() => {
    window.addEventListener('portoflow:sessao-expirada', sair);
    return () => window.removeEventListener('portoflow:sessao-expirada', sair);
  }, [sair]);

  const entrar = useCallback(async (email, senha) => {
    const { data } = await api.post('/auth/login', { email, senha });
    armazenamento.gravar(data.access_token);
    const me = await api.get('/usuarios/me');
    setUsuario(me.data);
    return me.data;
  }, []);

  const valor = useMemo(
    () => ({ usuario, setUsuario, carregando, entrar, sair }),
    [usuario, carregando, entrar, sair],
  );
  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
