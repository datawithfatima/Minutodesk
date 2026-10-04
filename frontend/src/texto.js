// Normaliza texto para comparar sin importar tildes/mayúsculas (ej. "contraseña"
// y "contrasena" deben coincidir en una búsqueda). Mismo criterio que el backend
// (backend/app/ml/train_classifier.py::quitar_tildes).
export function normalizarTexto(texto) {
  return texto
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

export const ETIQUETA_ROL = {
  usuario: "Usuario final",
  tecnico: "Técnico",
  administrador: "Administrador",
};

export function formatearDuracion(inicio, fin) {
  const minutos = Math.max(0, Math.round((new Date(fin) - new Date(inicio)) / 60000));
  if (minutos < 60) return `${minutos} min`;
  const horas = Math.floor(minutos / 60);
  if (horas < 24) return `${horas} h ${minutos % 60} min`;
  return `${Math.floor(horas / 24)} d ${horas % 24} h`;
}
