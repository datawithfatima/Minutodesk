import { cerrarSesion, obtenerToken } from "./auth";

// En el mismo equipo usa localhost; si se abre desde otro equipo de la red, usa ese mismo host.
const API_BASE =
  import.meta.env.VITE_API_URL || `${window.location.protocol}//${window.location.hostname}:8000`;

function headers(conJson = true) {
  const h = {};
  if (conJson) h["Content-Type"] = "application/json";
  const token = obtenerToken();
  if (token) h["Authorization"] = `Bearer ${token}`;
  return h;
}

async function manejarRespuesta(res) {
  if (!res.ok) {
    if (res.status === 401 && !res.url.endsWith("/auth/login")) {
      cerrarSesion();
      window.location.assign("/login");
      throw new Error("Tu sesión expiró. Inicia sesión de nuevo.");
    }
    const detalle = await res.json().catch(() => null);
    const mensaje =
      typeof detalle?.detail === "string"
        ? detalle.detail
        : Array.isArray(detalle?.detail)
          ? "Revisa los datos ingresados: hay un campo con un formato no válido."
          : res.status >= 500
            ? "El servidor tuvo un problema. Inténtalo de nuevo en unos minutos."
            : `No se pudo completar la acción (error ${res.status}).`;
    // Con contraseña temporal el servidor bloquea todo menos el cambio de contraseña.
    if (res.status === 403 && mensaje.includes("cambiar tu contraseña")) {
      window.location.assign("/cambiar-password");
    }
    throw new Error(mensaje);
  }
  return res.json();
}

// Sin respuesta del servidor (apagado o sin red), fetch falla con un mensaje en inglés.
function sinConexion() {
  throw new Error("No se pudo conectar con el servidor de MinutoDesk. Revisa tu conexión e inténtalo de nuevo.");
}

function consulta(params = {}) {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") p.set(k, v);
  });
  const texto = p.toString();
  return texto ? `?${texto}` : "";
}

function get(ruta, params) {
  return fetch(`${API_BASE}${ruta}${consulta(params)}`, { headers: headers(false) }).then(
    manejarRespuesta,
    sinConexion
  );
}

function enviar(metodo, ruta, cuerpo) {
  return fetch(`${API_BASE}${ruta}`, {
    method: metodo,
    headers: headers(),
    body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
  }).then(manejarRespuesta, sinConexion);
}

// --- Acceso ---
export const iniciarSesion = ({ email, password }) => enviar("POST", "/auth/login", { email, password });
export const cambiarPassword = ({ passwordActual, passwordNueva }) =>
  enviar("POST", "/auth/cambiar-password", {
    password_actual: passwordActual,
    password_nueva: passwordNueva,
  });
export const olvidePassword = (email) => enviar("POST", "/auth/olvide-password", { email });
export const establecerPassword = ({ token, password }) =>
  enviar("POST", "/auth/establecer-password", { token, password });

// --- Tickets ---
export const listarTickets = (filtros = {}) => get("/tickets", filtros);
export const obtenerTicket = (id) => get(`/tickets/${id}`);
// `tipo`, `categoria` y `prioridad` son opcionales (el chat con Minutito solo manda el texto).
export const crearTicket = ({ texto, tipo, categoria, prioridad }) =>
  enviar("POST", "/tickets", { texto, tipo, categoria, prioridad });
export const crearAltaColaborador = (datos) => enviar("POST", "/tickets/alta-colaborador", datos);
export const obtenerCatalogos = () => get("/tickets/catalogos");
export const sugerirClasificacion = (texto) => enviar("POST", "/tickets/sugerir", { texto });

// --- Archivos adjuntos: el archivo viaja como cuerpo crudo; su nombre, en una cabecera ---
export const listarAdjuntos = (ticketId) => get(`/tickets/${ticketId}/adjuntos`);
export const subirAdjunto = (ticketId, archivo) => {
  const h = headers(false);
  h["Content-Type"] = "application/octet-stream";
  h["X-Nombre-Archivo"] = encodeURIComponent(archivo.name);
  return fetch(`${API_BASE}/tickets/${ticketId}/adjuntos`, {
    method: "POST",
    headers: h,
    body: archivo,
  }).then(manejarRespuesta);
};
export const eliminarAdjunto = (id) => enviar("DELETE", `/adjuntos/${id}`);
// La descarga necesita la sesión, así que se pide con fetch y se entrega como archivo local.
export async function descargarAdjunto(adjunto) {
  const res = await fetch(`${API_BASE}/adjuntos/${adjunto.id}`, { headers: headers(false) });
  if (!res.ok) {
    const detalle = await res.json().catch(() => null);
    throw new Error(typeof detalle?.detail === "string" ? detalle.detail : `Error ${res.status}`);
  }
  const url = URL.createObjectURL(await res.blob());
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = adjunto.nombre_original;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export const actualizarTicket = (id, data) => enviar("PATCH", `/tickets/${id}`, data);
export const cancelarTicket = (id, motivo) => enviar("POST", `/tickets/${id}/cancelar`, { motivo });
export const listarInteracciones = (ticketId) => get(`/tickets/${ticketId}/interacciones`);
export const listarHistorial = (ticketId) => get(`/tickets/${ticketId}/historial`);
export const confirmarResolucion = (ticketId, resuelto) =>
  enviar("POST", `/tickets/${ticketId}/confirmar-resolucion`, { resuelto });
export const enviarMensajeChat = (ticketId, mensaje) =>
  enviar("POST", `/tickets/${ticketId}/chat`, { mensaje });

// --- Clientes y gamificación ---
export const listarClientes = () => get("/clientes");
export const obtenerCliente = (id) => get(`/clientes/${id}`);
export const obtenerGamificacion = (clienteId) => get(`/clientes/${clienteId}/gamificacion`);

// --- Reportes ---
export const obtenerResumen = () => get("/reportes/resumen");
export const obtenerHistorico = () => get("/reportes/historico");
export const listarTicketsHistoricos = (filtros) => get("/historico/tickets", filtros);
export const obtenerTicketHistorico = (id) => get(`/historico/tickets/${id}`);
export const obtenerClasificador = () => get("/reportes/clasificador"); // solo administrador
export const obtenerUmbralConfianza = () => get("/reportes/clasificador/umbral");

// --- Administración ---
export const listarUsuarios = (filtros = {}) => get("/admin/usuarios", filtros);
export const crearUsuario = (data) => enviar("POST", "/admin/usuarios", data);
export const actualizarUsuario = (id, data) => enviar("PATCH", `/admin/usuarios/${id}`, data);
// El CSV viaja como cuerpo crudo; sin `aplicar` el servidor solo devuelve la vista previa.
export const importarHistorico = (archivo, aplicar) => {
  const h = headers(false);
  h["Content-Type"] = "text/csv";
  return fetch(`${API_BASE}/admin/historico?aplicar=${aplicar ? "true" : "false"}`, {
    method: "POST",
    headers: h,
    body: archivo,
  }).then(manejarRespuesta);
};
export const eliminarUsuario = (id) => enviar("DELETE", `/admin/usuarios/${id}`);
export const restablecerPassword = (id) =>
  enviar("POST", `/admin/usuarios/${id}/restablecer-password`);
export const listarAreas = () => get("/admin/areas");
export const crearArea = ({ nombre }) => enviar("POST", "/admin/areas", { nombre });
export const actualizarArea = (id, data) => enviar("PATCH", `/admin/areas/${id}`, data);
