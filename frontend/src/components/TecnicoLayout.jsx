import { BarChart3, BookOpen, Bot, Inbox, Settings, Trophy, UserCog, Users } from "lucide-react";
import { Outlet, useNavigate } from "react-router-dom";
import { cerrarSesion, obtenerUsuario } from "../auth";
import AppShell from "./AppShell";

const NAV_ITEMS = [
  { to: "/tecnico", label: "Tickets", icon: Inbox },
  { label: "Mis asignados", icon: UserCog, disabled: true },
  { to: "/tecnico/clientes", label: "Clientes / Usuarios", icon: Users },
  { to: "/tecnico/gamificacion", label: "Gamificación", icon: Trophy },
  { label: "Base de conocimiento", icon: BookOpen, disabled: true },
  { label: "Reportes", icon: BarChart3, disabled: true },
  { label: "Configuración", icon: Settings, disabled: true },
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
      <span className="text-[10px] text-slate-500">Próximamente para técnicos</span>
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
      rolLabel="Técnico de Soporte TI"
      onLogout={salir}
      dark
      sidebarExtra={<MinutitoMiniWidget />}
      footer="La tecnología funciona mejor cuando las personas trabajan juntas."
    >
      <Outlet />
    </AppShell>
  );
}
