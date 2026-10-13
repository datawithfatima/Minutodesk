import { BarChart3, Bot, History, Inbox, Medal, UserCog, Users } from "lucide-react";
import { Outlet, useNavigate } from "react-router-dom";
import { cerrarSesion, obtenerUsuario } from "../auth";
import AppShell from "./AppShell";

const NAV_ITEMS = [
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
  { to: "/tecnico/historico", label: "Mi histórico", icon: History },
  { to: "/tecnico/usuarios", label: "Usuarios", icon: Users },
  { to: "/tecnico/ranking", label: "Ranking", icon: Medal },
  { to: "/tecnico/reportes", label: "Reportes", icon: BarChart3 },
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
          <div className="text-[11px] text-noche-300">Próximamente para técnicos</div>
        </div>
      </div>
    </div>
  );
}

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
      sidebarExtra={<MinutitoMiniWidget />}
      footer="La tecnología funciona mejor cuando las personas trabajan juntas."
    >
      <Outlet />
    </AppShell>
  );
}
