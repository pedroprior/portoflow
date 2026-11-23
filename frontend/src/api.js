import axios from 'axios';

export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
const CHAVE_TOKEN = 'portoflow_token';

export const armazenamento = {
  ler() {
    try {
      return localStorage.getItem(CHAVE_TOKEN);
    } catch {
      return null;
    }
  },
  gravar(token) {
    try {
      if (token) localStorage.setItem(CHAVE_TOKEN, token);
      else localStorage.removeItem(CHAVE_TOKEN);
    } catch {
      /* navegação privada: segue só em memória */
    }
  },
};

export const api = axios.create({ baseURL: API_URL, timeout: 15000 });

api.interceptors.request.use((config) => {
  const token = armazenamento.ler();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (resposta) => resposta,
  (erro) => {
    const rota = erro.config?.url ?? '';
    if (erro.response?.status === 401 && !rota.startsWith('/auth/')) {
      window.dispatchEvent(new Event('portoflow:sessao-expirada'));
    }
    return Promise.reject(erro);
  },
);

/** Mensagem legível a partir do formato padrão de erro da API. */
export function mensagemErro(erro) {
  const corpo = erro?.response?.data?.erro;
  if (!corpo) return 'Não foi possível falar com o servidor. Verifique a conexão.';
  if (corpo.detalhes?.length) {
    return corpo.detalhes.map((d) => (d.campo ? `${d.campo}: ${d.mensagem}` : d.mensagem)).join(' · ');
  }
  return corpo.mensagem;
}

/** Erros de validação por campo, no formato de form.setErrors do Mantine. */
export function errosPorCampo(erro) {
  const detalhes = erro?.response?.data?.erro?.detalhes ?? [];
  return Object.fromEntries(detalhes.filter((d) => d.campo).map((d) => [d.campo, d.mensagem]));
}
