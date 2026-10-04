import { BarChart3, HelpCircle, History, Home, Plus, Ticket, Trophy } from "lucide-react";
import { Outlet, useNavigate } from "react-router-dom";
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
  { to: "/usuario", label: "Crear ticket", icon: Plus },
  { to: "/usuario/logros", label: "Mis logros", icon: Trophy },
  { to: "/usuario/historico", label: "Mi histórico", icon: History },
  { to: "/usuario/faqs", label: "FAQs", icon: HelpCircle },
  { to: "/usuario/reportes", label: "Reportes", icon: BarChart3 },
];

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
      footer="Pequeños clics, grandes soluciones"
    >
      <Outlet context={{ clienteId: usuario?.id }} />
    </AppShell>
  );
}
