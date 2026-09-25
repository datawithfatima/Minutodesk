// Normaliza texto para comparar sin importar tildes/mayúsculas (ej. "contraseña"
// y "contrasena" deben coincidir en una búsqueda). Mismo criterio que el backend
// (backend/app/ml/train_classifier.py::quitar_tildes).
export function normalizarTexto(texto) {
  return texto
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}
