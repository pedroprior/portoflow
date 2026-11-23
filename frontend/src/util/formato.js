const FUSO = 'America/Sao_Paulo';

const dataHora = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short', timeZone: FUSO });
const hora = new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit', timeZone: FUSO });
const dia = new Intl.DateTimeFormat('en-CA', { timeZone: FUSO }); // AAAA-MM-DD

export const fmtDataHora = (iso) => (iso ? dataHora.format(new Date(iso)) : '—');
export const fmtHora = (iso) => (iso ? hora.format(new Date(iso)) : '—');
export const diaLocal = (iso) => dia.format(iso ? new Date(iso) : new Date());
export const fmtJanela = (j) => `${fmtDataHora(j.inicio)}–${fmtHora(j.fim)}`;

export const fmtPeso = (valor) =>
  `${Number(valor).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} kg`;

/** ISO para o valor de <input type="datetime-local"> no fuso do navegador. */
export const isoParaLocal = (iso) => {
  if (!iso) return '';
  const d = new Date(iso);
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
};

/** Valor de <input type="datetime-local"> para ISO com fuso. */
export const localParaIso = (valor) => (valor ? new Date(valor).toISOString() : null);

export const STATUS_CONTAINER = {
  aguardando_chegada: { rotulo: 'Aguardando chegada', cor: 'gray' },
  no_patio: { rotulo: 'No pátio', cor: 'blue' },
  saiu: { rotulo: 'Saiu', cor: 'teal' },
};

export const STATUS_AGENDAMENTO = {
  confirmado: { rotulo: 'Confirmado', cor: 'indigo' },
  cumprido: { rotulo: 'Cumprido', cor: 'green' },
  cancelado: { rotulo: 'Cancelado', cor: 'gray' },
};

export const STATUS_ESCALA = {
  prevista: { rotulo: 'Prevista', cor: 'gray' },
  atracada: { rotulo: 'Atracada', cor: 'blue' },
  encerrada: { rotulo: 'Encerrada', cor: 'teal' },
};

export const STATUS_USUARIO = {
  pendente: { rotulo: 'Pendente', cor: 'orange' },
  ativo: { rotulo: 'Ativo', cor: 'green' },
  inativo: { rotulo: 'Inativo', cor: 'gray' },
};

export const OPERACAO = { entrega: 'Entrega', retirada: 'Retirada' };
export const PAPEL = { admin: 'Administrador', operador: 'Operador', externo: 'Cliente' };
