// Mesmas regras da API, para avisar o usuário antes de enviar.

const VALORES = (() => {
  const tabela = {};
  let valor = 10;
  for (const letra of 'ABCDEFGHIJKLMNOPQRSTUVWXYZ') {
    if (valor % 11 === 0) valor += 1;
    tabela[letra] = valor;
    valor += 1;
  }
  return tabela;
})();

export const normalizar = (texto) => (texto ?? '').replace(/[\s-]/g, '').toUpperCase();

/** Código de container ISO 6346, com dígito verificador. */
export function codigoContainerValido(codigo) {
  const c = normalizar(codigo);
  if (!/^[A-Z]{3}[UJZ]\d{7}$/.test(c)) return false;
  const soma = [...c.slice(0, 10)].reduce(
    (total, ch, i) => total + (/[A-Z]/.test(ch) ? VALORES[ch] : Number(ch)) * 2 ** i,
    0,
  );
  return (soma % 11) % 10 === Number(c[10]);
}

/** Placa antiga (ABC1234) ou Mercosul (ABC1D23). */
export const placaValida = (placa) => /^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$/.test(normalizar(placa));

export const cnpjValido = (cnpj) => (cnpj ?? '').replace(/\D/g, '').length === 14;
