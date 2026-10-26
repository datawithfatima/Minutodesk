import { normalizarTexto } from "../../texto";

export function formatearBytes(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${Math.round(n / 1024)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function extensionDe(nombre) {
  const i = nombre.lastIndexOf(".");
  return i > 0 ? nombre.slice(i).toLowerCase() : "";
}

/** Devuelve el motivo si el archivo no cumple los límites del servidor (o null si está bien). */
export function problemaConArchivo(archivo, limites) {
  if (!limites) return null;
  if (archivo.size === 0) return "está vacío";
  if (!limites.extensiones.includes(extensionDe(archivo.name))) return "su tipo de archivo no está permitido";
  if (archivo.size > limites.megabytes * 1024 * 1024) return `supera los ${limites.megabytes} MB`;
  return null;
}

// Misma regla que el servidor (cédula ecuatoriana de persona natural), para avisar mientras se escribe.
export function cedulaValida(cedula) {
  if (!/^\d{10}$/.test(cedula)) return false;
  const provincia = Number(cedula.slice(0, 2));
  if (!((provincia >= 1 && provincia <= 24) || provincia === 30) || Number(cedula[2]) > 5) return false;
  let suma = 0;
  for (let i = 0; i < 9; i++) {
    const d = Number(cedula[i]) * (i % 2 === 0 ? 2 : 1);
    suma += d > 9 ? d - 9 : d;
  }
  return (10 - (suma % 10)) % 10 === Number(cedula[9]);
}

// Los tipos vienen con una aclaración entre paréntesis: en pantalla basta el título.
export function tituloTipo(nombre) {
  return nombre ? nombre.split(" (")[0] : null;
}

export function textoSiNo(valor) {
  if (valor === true) return "Sí";
  if (valor === false) return "No";
  return "—";
}

/**
 * Si el ticket coincide con lo buscado: por número («83» o «#83»), descripción, categoría
 * (la confirmada o la del clasificador) o quien lo pidió. Sin tildes ni mayúsculas.
 */
export function coincideBusqueda(ticket, busqueda, solicitante = "") {
  const buscado = normalizarTexto(busqueda.trim());
  if (!buscado) return true;
  const numero = buscado.replace(/^#/, "");
  if (/^\d+$/.test(numero)) return String(ticket.id) === numero;
  return [ticket.texto, ticket.categoria, ticket.categoria_predicha, ticket.solicitante_externo, solicitante]
    .filter(Boolean)
    .some((campo) => normalizarTexto(campo).includes(buscado));
}
