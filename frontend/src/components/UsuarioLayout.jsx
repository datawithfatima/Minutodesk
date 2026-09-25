import { BarChart3, BookOpen, HelpCircle, Home, Plus, Ticket, Trophy } from "lucide-react";
import { Outlet, useNavigate } from "react-router-dom";
import { cerrarSesion, obtenerUsuario } from "../auth";
import AppShell from "./AppShell";

const NAV_ITEMS = [
  { to: "/usuario", label: "Inicio", icon: Home },
  { to: "/usuario/mis-tickets", label: "Mis tickets", icon: Ticket },
  { to: "/usuario", label: "Crear ticket", icon: Plus },
  { to: "/usuario/gamificacion", label: "Mi gamificación", icon: Trophy },
  { label: "Base de conocimiento", icon: BookOpen, disabled: true },
  { label: "FAQs", icon: HelpCircle, disabled: true },
  { label: "Reportes", icon: BarChart3, disabled: true },
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
      rolLabel="Colaborador"
      onLogout={salir}
      footer="Pequeños clics, grandes soluciones"
    >
      <Outlet context={{ clienteId: usuario?.id }} />
    </AppShell>
  );
}
