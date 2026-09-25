import { Navigate, Outlet } from "react-router-dom";
import { obtenerToken, obtenerUsuario } from "../auth";

export default function RequireAuth({ rol }) {
  const token = obtenerToken();
  const usuario = obtenerUsuario();

  if (!token || !usuario) {
    return <Navigate to="/login" replace />;
  }
  if (rol && usuario.rol !== rol) {
    return <Navigate to={usuario.rol === "tecnico" ? "/tecnico" : "/usuario"} replace />;
  }
  return <Outlet />;
}
