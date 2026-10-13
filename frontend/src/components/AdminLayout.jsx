import {
  BarChart3,
  Bot,
  Building2,
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
  { to: "/admin/historico", label: "Histórico", icon: History },
  { to: "/admin/usuarios", label: "Usuarios", icon: Users },
  { to: "/admin/areas", label: "Áreas", icon: Building2 },
  { to: "/admin/ranking", label: "Ranking", icon: Medal },
  { to: "/admin/datos", label: "Datos históricos", icon: Database },
];

// Minutito para el personal todavía no existe: se muestra, pero indicando que llega pronto.
function MinutitoMiniWidget() {
  return (
    <div className="mx-3 mb-3 rounded-xl border border-white/10 p-3" title="Próximamente">
      <div className="flex items-center gap-2.5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/[0.06] text-noche-300">
          <Bot size={16} aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <div className="text-xs font-semibold text-white/80">Minutito</div>
          <div className="text-[11px] text-noche-300">Próximamente</div>
        </div>
      </div>
    </div>
  );
}

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
      sidebarExtra={<MinutitoMiniWidget />}
      footer="Pequeños clics, grandes soluciones"
    >
      <Outlet />
    </AppShell>
  );
}
