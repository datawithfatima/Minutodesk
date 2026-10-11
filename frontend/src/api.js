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
    throw new Error(typeof detalle?.detail === "string" ? detalle.detail : `Error ${res.status}`);
  }
  return res.json();
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
    manejarRespuesta
  );
}

function enviar(metodo, ruta, cuerpo) {
  return fetch(`${API_BASE}${ruta}`, {
    method: metodo,
    headers: headers(),
    body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
  }).then(manejarRespuesta);
}

// --- Acceso ---
export const iniciarSesion = ({ email, password }) => enviar("POST", "/auth/login", { email, password });
export const olvidePassword = (email) => enviar("POST", "/auth/olvide-password", { email });
export const establecerPassword = ({ token, password }) =>
  enviar("POST", "/auth/establecer-password", { token, password });

// --- Tickets ---
export const listarTickets = (filtros = {}) => get("/tickets", filtros);
export const obtenerTicket = (id) => get(`/tickets/${id}`);
export const crearTicket = ({ texto }) => enviar("POST", "/tickets", { texto });
export const actualizarTicket = (id, data) => enviar("PATCH", `/tickets/${id}`, data);
export const listarInteracciones = (ticketId) => get(`/tickets/${ticketId}/interacciones`);
export const listarHistorial = (ticketId) => get(`/tickets/${ticketId}/historial`);
export const enviarMensajeChat = (ticketId, mensaje) =>
  enviar("POST", `/tickets/${ticketId}/chat`, { mensaje });

// --- Clientes y gamificación ---
export const listarClientes = () => get("/clientes");
export const obtenerCliente = (id) => get(`/clientes/${id}`);
export const obtenerGamificacion = (clienteId) => get(`/clientes/${clienteId}/gamificacion`);

// --- Reportes ---
export const obtenerResumen = () => get("/reportes/resumen");
export const obtenerHistorico = () => get("/reportes/historico");

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
export const enviarEnlaceDeAcceso = (id) => enviar("POST", `/admin/usuarios/${id}/invitacion`);
export const listarAreas = () => get("/admin/areas");
export const crearArea = ({ nombre }) => enviar("POST", "/admin/areas", { nombre });
export const actualizarArea = (id, data) => enviar("PATCH", `/admin/areas/${id}`, data);
