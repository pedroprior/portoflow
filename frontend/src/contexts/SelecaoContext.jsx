import { createContext, useCallback, useContext, useMemo, useState } from 'react';

/**
 * "Carrinho" do PortoFlow: containers escolhidos pelo cliente antes de agendar.
 * Fica só no front-end porque só vira dado quando a vaga da janela é reservada.
 */
const SelecaoContext = createContext(null);

export const LIMITE_POR_CAMINHAO = 2;

export function operacaoDo(container) {
  if (container.status === 'aguardando_chegada') return 'entrega';
  if (container.status === 'no_patio' && !container.bloqueado) return 'retirada';
  return null;
}

/** Devolve o motivo de não poder adicionar, ou null se pode. */
export function motivoBloqueioSelecao(container, selecionados) {
  const operacao = operacaoDo(container);
  if (!operacao) return container.bloqueado ? 'Container bloqueado' : 'Nada a agendar para este container';
  if (selecionados.some((c) => c.id === container.id)) return null;
  if (selecionados.length >= LIMITE_POR_CAMINHAO) return 'Um caminhão leva no máximo 2 containers';
  if (selecionados.length && operacaoDo(selecionados[0]) !== operacao) {
    return 'Agende entregas e retiradas separadamente';
  }
  if (selecionados.length && (container.tamanho === 40 || selecionados[0].tamanho === 40)) {
    return "Container de 40' vai sozinho no caminhão";
  }
  return null;
}

export function SelecaoProvider({ children }) {
  const [selecionados, setSelecionados] = useState([]);

  const alternar = useCallback((container) => {
    setSelecionados((atual) =>
      atual.some((c) => c.id === container.id)
        ? atual.filter((c) => c.id !== container.id)
        : [...atual, container],
    );
  }, []);

  const limpar = useCallback(() => setSelecionados([]), []);

  const valor = useMemo(
    () => ({
      selecionados,
      alternar,
      limpar,
      operacao: selecionados[0] ? operacaoDo(selecionados[0]) : null,
    }),
    [selecionados, alternar, limpar],
  );
  return <SelecaoContext.Provider value={valor}>{children}</SelecaoContext.Provider>;
}

export const useSelecao = () => useContext(SelecaoContext);
