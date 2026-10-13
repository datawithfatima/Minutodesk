import { BarChart3, Bot, HelpCircle, History, Home, Plus, Ticket, Trophy } from "lucide-react";
import { Link, Outlet, useNavigate } from "react-router-dom";
import { cerrarSesion, obtenerUsuario } from "../auth";
import AppShell from "./AppShell";

const NAV_ITEMS = [
  { to: "/usuario", label: "Inicio", icon: Home },
  {
    to: "/usuario/mis-tickets",
    label: "Mis tickets",
    icon: Ticket,
    isActive: (p) => p.startsWith("/usuario/mis-tickets") || p.startsWith("/usuario/tickets/"),
  },
  { to: "/usuario/nuevo-ticket", label: "Crear ticket", icon: Plus },
  { to: "/usuario/logros", label: "Mis logros", icon: Trophy },
  { to: "/usuario/historico", label: "Mi histórico", icon: History },
  { to: "/usuario/faqs", label: "FAQs", icon: HelpCircle },
  { to: "/usuario/reportes", label: "Reportes", icon: BarChart3 },
];

// Acceso rápido al asistente (el chat vive en Inicio).
function MinutitoAcceso() {
  return (
    <Link
      to="/usuario#minutito"
      className="group mx-3 mb-3 block rounded-xl border border-white/10 bg-white/[0.04] p-3 transition-colors duration-150 hover:border-acento/60 hover:bg-white/[0.07]"
    >
      <div className="flex items-center gap-2.5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-acento text-white">
          <Bot size={16} aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <div className="text-xs font-semibold text-white">Minutito</div>
          <div className="text-[11px] text-noche-300">Tu asistente de soporte</div>
        </div>
      </div>
      <span className="mt-2 block text-xs text-white/80 group-hover:text-white">Pídele ayuda ahora →</span>
    </Link>
  );
}

export default function UsuarioLayout() {
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
      rutaBusqueda="/usuario/mis-tickets"
      onLogout={salir}
      dark
      sidebarExtra={<MinutitoAcceso />}
      footer="Pequeños clics, grandes soluciones"
    >
      <Outlet context={{ clienteId: usuario?.id }} />
    </AppShell>
  );
}
