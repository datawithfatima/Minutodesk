// Paleta validada con scripts/validate_palette.js (modo claro, superficie blanca).
// Las series se asignan en este orden fijo y el color sigue a la entidad, no a su posición.
export const SERIES = [
  "#2a78d6", // 1 azul
  "#eb6834", // 2 naranja
  "#1baf7a", // 3 verde agua
  "#eda100", // 4 amarillo
  "#e87ba4", // 5 magenta
  "#008300", // 6 verde
  "#4a3aa7", // 7 violeta
  "#e34948", // 8 rojo
];

// Escala ordenada de un solo tono (Baja → Crítica), validada con --ordinal.
export const ORDINAL_AZUL = ["#86b6ef", "#5598e7", "#256abf", "#104281"];

// Colores fijos por entidad del histórico importado (gráficos y lista de tickets).
export const COLOR_ESTADO_HISTORICO = {
  Completado: SERIES[0],
  "En Curso": SERIES[1],
  Cancelado: SERIES[2],
  Nuevo: SERIES[3],
};
export const COLOR_PRIORIDAD = {
  Baja: ORDINAL_AZUL[0],
  Normal: ORDINAL_AZUL[1],
  Alta: ORDINAL_AZUL[2],
  Crítica: ORDINAL_AZUL[3],
  "Sin prioridad": "#c3c2b7",
};

export const AZUL_PISTA = "#cde2fb"; // paso claro del mismo azul: pista de los medidores
export const GRIS_SIN_DATO = "#c3c2b7";

// Tintas y cromo del gráfico (los textos nunca usan el color de la serie).
export const INK = {
  primary: "#0b0b0b",
  secondary: "#52514e",
  muted: "#898781",
  grid: "#e1e0d9",
  axis: "#c3c2b7",
  surface: "#ffffff",
};

export const ESTADO_OK = "#0ca30c"; // estados reservados: siempre con icono y texto
export const ESTADO_AVISO = "#fab219";

const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

export function etiquetaMes(clave) {
  const [anio, mes] = clave.split("-");
  return `${MESES[Number(mes) - 1]} ${anio.slice(2)}`;
}

export function formatoNumero(n) {
  return Number(n).toLocaleString("es-EC", { maximumFractionDigits: 1 });
}

export function formatoCompacto(n) {
  return n >= 10000
    ? Number(n).toLocaleString("es-EC", { notation: "compact", maximumFractionDigits: 1 })
    : formatoNumero(n);
}

export function hexA(hex, alfa) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alfa})`;
}

// Escala "bonita" (0, 50, 100…) para el eje Y.
export function escala(max, marcas = 4) {
  if (!(max > 0)) return { max: 1, pasos: [0, 1] };
  const bruto = max / marcas;
  const magnitud = 10 ** Math.floor(Math.log10(bruto));
  const f = bruto / magnitud;
  const paso = (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * magnitud;
  const tope = Math.ceil(max / paso) * paso;
  const pasos = [];
  for (let v = 0; v <= tope + paso / 1e6; v += paso) pasos.push(Number(v.toFixed(6)));
  return { max: tope, pasos };
}
