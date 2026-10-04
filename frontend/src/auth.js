const TOKEN_KEY = "minutodesk_token";
const USUARIO_KEY = "minutodesk_usuario";

export function guardarSesion(token, usuario) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USUARIO_KEY, JSON.stringify(usuario));
}

export function obtenerToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function obtenerUsuario() {
  const valor = localStorage.getItem(USUARIO_KEY);
  return valor ? JSON.parse(valor) : null;
}

export function cerrarSesion() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USUARIO_KEY);
}

export function rutaInicio(rol) {
  if (rol === "administrador") return "/admin";
  if (rol === "tecnico") return "/tecnico";
  return "/usuario";
}
