import {
  BarChart3,
  Building2,
  ClipboardCheck,
  Database,
  History,
  Inbox,
  Medal,
  UserCog,
  Users,
} from "lucide-react";
import { Outlet, useNavigate } from "react-router-dom";
import { cerrarSesion, obtenerUsuario } from "../auth";
import AppShell from "./AppShell";

const NAV_ITEMS = [
  { to: "/admin", label: "Reportes", icon: BarChart3 },
  {
    to: "/admin/tickets",
    label: "Tickets",
    icon: Inbox,
    isActive: (p) => p.startsWith("/admin/tickets"),
  },
  {
    to: "/admin/asignados",
    label: "Mis asignados",
    icon: UserCog,
    isActive: (p) => p.startsWith("/admin/asignados"),
  },
  { to: "/admin/aprobaciones", label: "Aprobaciones", icon: ClipboardCheck },
  { to: "/admin/historico", label: "Histórico", icon: History },
  { to: "/admin/usuarios", label: "Usuarios", icon: Users },
  { to: "/admin/areas", label: "Áreas", icon: Building2 },
  { to: "/admin/ranking", label: "Ranking", icon: Medal },
  { to: "/admin/datos", label: "Datos históricos", icon: Database },
];

export default function AdminLayout() {
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
      rutaBusqueda="/admin/tickets"
      onLogout={salir}
      dark
      footer="Pequeños clics, grandes soluciones"
    >
      <Outlet />
    </AppShell>
  );
}
