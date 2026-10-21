import { BarChart3, ClipboardCheck, History, Inbox, Medal, UserCog, Users } from "lucide-react";
import { Outlet, useNavigate } from "react-router-dom";
import { cerrarSesion, obtenerUsuario } from "../auth";
import AppShell from "./AppShell";

const NAV_ITEMS = [
  { to: "/tecnico/reportes", label: "Reportes", icon: BarChart3 },
  {
    to: "/tecnico/tickets",
    label: "Tickets",
    icon: Inbox,
    isActive: (p) => p.startsWith("/tecnico/tickets"),
  },
  {
    to: "/tecnico/asignados",
    label: "Mis asignados",
    icon: UserCog,
    isActive: (p) => p.startsWith("/tecnico/asignados"),
  },
  { to: "/tecnico/aprobaciones", label: "Aprobaciones", icon: ClipboardCheck },
  { to: "/tecnico/historico", label: "Mi histórico", icon: History },
  { to: "/tecnico/usuarios", label: "Usuarios", icon: Users },
  { to: "/tecnico/ranking", label: "Ranking", icon: Medal },
];

export default function TecnicoLayout() {
  const usuario = obtenerUsuario();
  const navegar = useNavigate();

  function salir() {
    cerrarSesion();
    navegar("/");
  }

  return (
    <AppShell
      navItems={NAV_ITEMS}
      usuario={usuario}
      rutaBusqueda="/tecnico/tickets"
      onLogout={salir}
      dark
      footer="La tecnología funciona mejor cuando las personas trabajan juntas."
    >
      <Outlet />
    </AppShell>
  );
}
