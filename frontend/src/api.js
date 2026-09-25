import { obtenerToken } from "./auth";

const API_BASE = "http://localhost:8000";

function headers(conJson = true) {
  const h = {};
  if (conJson) h["Content-Type"] = "application/json";
  const token = obtenerToken();
  if (token) h["Authorization"] = `Bearer ${token}`;
  return h;
}

async function manejarRespuesta(res) {
  if (!res.ok) {
    const detalle = await res.json().catch(() => null);
    throw new Error(detalle?.detail || `Error ${res.status}`);
  }
  return res.json();
}

export function registrarse({ nombre, area, email, password }) {
  return fetch(`${API_BASE}/auth/registro`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ nombre, area, email, password }),
  }).then(manejarRespuesta);
}

export function iniciarSesion({ email, password }) {
  return fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ email, password }),
  }).then(manejarRespuesta);
}

export function listarTickets({ estado, categoria_predicha, cliente_id } = {}) {
  const params = new URLSearchParams();
  if (estado) params.set("estado", estado);
  if (categoria_predicha) params.set("categoria_predicha", categoria_predicha);
  if (cliente_id != null) params.set("cliente_id", cliente_id);
  const query = params.toString() ? `?${params}` : "";
  return fetch(`${API_BASE}/tickets${query}`, { headers: headers(false) }).then(
    manejarRespuesta
  );
}

export function obtenerTicket(id) {
  return fetch(`${API_BASE}/tickets/${id}`, { headers: headers(false) }).then(
    manejarRespuesta
  );
}

export function crearTicket({ texto }) {
  return fetch(`${API_BASE}/tickets`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ texto }),
  }).then(manejarRespuesta);
}

export function actualizarTicket(id, data) {
  return fetch(`${API_BASE}/tickets/${id}`, {
    method: "PATCH",
    headers: headers(),
    body: JSON.stringify(data),
  }).then(manejarRespuesta);
}

export function listarInteracciones(ticketId) {
  return fetch(`${API_BASE}/tickets/${ticketId}/interacciones`, {
    headers: headers(false),
  }).then(manejarRespuesta);
}

export function enviarMensajeChat(ticketId, mensaje) {
  return fetch(`${API_BASE}/tickets/${ticketId}/chat`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ mensaje }),
  }).then(manejarRespuesta);
}

export function listarClientes() {
  return fetch(`${API_BASE}/clientes`, { headers: headers(false) }).then(
    manejarRespuesta
  );
}

export function obtenerCliente(id) {
  return fetch(`${API_BASE}/clientes/${id}`, { headers: headers(false) }).then(
    manejarRespuesta
  );
}

export function obtenerGamificacion(clienteId) {
  return fetch(`${API_BASE}/clientes/${clienteId}/gamificacion`, {
    headers: headers(false),
  }).then(manejarRespuesta);
}
