import {
  BarChart3,
  Bot,
  Building2,
  FileUp,
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
  { to: "/admin/datos", label: "Importar histórico", icon: FileUp },
];

function MinutitoMiniWidget() {
  return (
    <div className="mx-3 mb-3 rounded-lg bg-slate-800 p-3 opacity-60" title="Próximamente">
      <div className="mb-1 flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-700 text-white">
          <Bot size={16} />
        </div>
        <div>
          <div className="text-xs font-semibold text-white">Minutito</div>
          <div className="text-[10px] text-slate-400">Tu asistente de soporte</div>
        </div>
      </div>
      <span className="text-[10px] text-slate-500">Próximamente</span>
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
