import { Building2, ClipboardCheck, HelpCircle, History, Home, Plus, Ticket } from "lucide-react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
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
  { to: "/usuario/aprobaciones", label: "Aprobaciones", icon: ClipboardCheck },
  { to: "/usuario/logros", label: "Mi obra", icon: Building2 },
  { to: "/usuario/historico", label: "Mi histórico", icon: History },
  { to: "/usuario/faqs", label: "FAQs", icon: HelpCircle },
];

// Acceso rápido al asistente (el chat vive en Inicio).
function MinutitoAcceso() {
  return (
    <Link
      to="/usuario#minutito"
      className="group relative mx-3 mb-3 block overflow-hidden rounded-md border border-white/10 bg-white/[0.04] p-3 transition-colors duration-150 hover:border-casco/60 hover:bg-white/[0.07]"
    >
      <div className="flex items-center gap-2.5">
        <img
          src="/img/robot-minutito.jpg"
          alt=""
          className="h-9 w-9 rounded-md bg-white object-contain p-0.5 transition-transform duration-300 ease-[cubic-bezier(.34,1.4,.64,1)] group-hover:-rotate-6 group-hover:scale-110"
        />
        <div className="min-w-0">
          <div className="text-xs font-semibold text-white">Minutito</div>
          <div className="text-[11px] text-noche-300">Tu asistente de soporte</div>
        </div>
      </div>
      <span className="mt-2 flex items-center justify-between text-xs text-white/80 group-hover:text-white">
        Pídele ayuda ahora
        <span aria-hidden="true" className="transition-transform duration-200 group-hover:translate-x-1">→</span>
      </span>
      <span aria-hidden="true" className="franja-obra absolute inset-x-0 bottom-0 h-[3px] origin-left scale-x-0 transition-transform duration-300 group-hover:scale-x-100" />
    </Link>
  );
}

export default function UsuarioLayout() {
  const usuario = obtenerUsuario();
  const navegar = useNavigate();
  const { pathname } = useLocation();

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
      // En Inicio el chat ya está en la pantalla: el acceso rápido sobra.
      sidebarExtra={pathname === "/usuario" ? null : <MinutitoAcceso />}
      footer="Pequeños clics, grandes soluciones"
    >
      <Outlet context={{ clienteId: usuario?.id }} />
    </AppShell>
  );
}
