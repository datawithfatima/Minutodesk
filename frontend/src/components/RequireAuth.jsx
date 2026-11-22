import { Navigate, Outlet } from "react-router-dom";
import { obtenerToken, obtenerUsuario, rutaInicio } from "../auth";

// Guardián de rutas: este componente deja pasar solo a quien tiene sesión y el rol pedido.
// Sin sesión lleva al login; con contraseña temporal, a cambiarla; con otro rol, a su panel.
// Es una ayuda de navegación: la protección real la hace el backend, que valida el token
// y el rol en cada petición.
export default function RequireAuth({ rol }) {
  const token = obtenerToken();
  const usuario = obtenerUsuario();

  if (!token || !usuario) {
    return <Navigate to="/login" replace />;
  }
  if (usuario.debe_cambiar_password) {
    return <Navigate to="/cambiar-password" replace />;
  }
  if (rol && usuario.rol !== rol) {
    return <Navigate to={rutaInicio(usuario.rol)} replace />;
  }
  return <Outlet />;
}
