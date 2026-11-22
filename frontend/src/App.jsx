import { Navigate, Route, Routes } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import OlvidePasswordPage from "./pages/OlvidePasswordPage";
import EstablecerPasswordPage from "./pages/EstablecerPasswordPage";
import CambiarPasswordPage from "./pages/CambiarPasswordPage";
import RequireAuth from "./components/RequireAuth";
import { obtenerToken, obtenerUsuario, rutaInicio } from "./auth";

import UsuarioLayout from "./components/UsuarioLayout";
import DashboardPage from "./pages/usuario/DashboardPage";
import MisTicketsPage from "./pages/usuario/MisTicketsPage";
import NuevoTicketPage from "./pages/usuario/NuevoTicketPage";
import UsuarioTicketDetailPage from "./pages/usuario/TicketDetailPage";
import MisLogrosPage from "./pages/usuario/GamificacionPage";
import FaqsPage from "./pages/usuario/FaqsPage";
import ConocimientoPage from "./pages/usuario/ConocimientoPage";

import TecnicoLayout from "./components/TecnicoLayout";
import TicketsWorkspace from "./pages/tecnico/TicketsWorkspace";
import TicketDetailPage from "./pages/tecnico/TicketDetailPage";
import RankingPage from "./pages/tecnico/GamificacionPage";
import UsuariosSoloLecturaPage from "./pages/tecnico/ClientesPage";

import AdminLayout from "./components/AdminLayout";
import UsuariosPage from "./pages/admin/UsuariosPage";
import AreasPage from "./pages/admin/AreasPage";
import DatosHistoricosPage from "./pages/admin/DatosHistoricosPage";
import BitacoraPage from "./pages/admin/BitacoraPage";

import HistoricoPage from "./pages/compartido/HistoricoPage";
import ReportesPage from "./pages/compartido/ReportesPage";
import AprobacionesPage from "./pages/compartido/AprobacionesPage";

// No hay portada: la raíz lleva al panel de quien ya inició sesión, o al login.
function Raiz() {
  const usuario = obtenerToken() ? obtenerUsuario() : null;
  if (!usuario) return <Navigate to="/login" replace />;
  return <Navigate to={usuario.debe_cambiar_password ? "/cambiar-password" : rutaInicio(usuario.rol)} replace />;
}

// Mapa de rutas del portal. Cada rol (usuario, técnico, administrador) tiene su propio
// panel, protegido por RequireAuth, que redirige al login a quien no tiene sesión o rol.
// En las bandejas de tickets, la ruta índice declara element={null} a propósito: la lista
// se dibuja en TicketsWorkspace y, sin ticket elegido, el detalle queda vacío. Si se omite
// element, React Router muestra una advertencia en la consola del navegador.
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Raiz />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/olvide-password" element={<OlvidePasswordPage />} />
      <Route path="/establecer-password" element={<EstablecerPasswordPage />} />
      <Route path="/cambiar-password" element={<CambiarPasswordPage />} />

      <Route element={<RequireAuth rol="usuario" />}>
        <Route path="/usuario" element={<UsuarioLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="mis-tickets" element={<MisTicketsPage />} />
          <Route path="nuevo-ticket" element={<NuevoTicketPage />} />
          <Route path="tickets/:id" element={<UsuarioTicketDetailPage />} />
          <Route path="aprobaciones" element={<AprobacionesPage />} />
          <Route path="logros" element={<MisLogrosPage />} />
          <Route path="historico" element={<HistoricoPage />} />
          <Route path="conocimiento" element={<ConocimientoPage />} />
          <Route path="faqs" element={<FaqsPage />} />
        </Route>
      </Route>

      <Route element={<RequireAuth rol="tecnico" />}>
        <Route path="/tecnico" element={<TecnicoLayout />}>
          <Route index element={<Navigate to="reportes" replace />} />
          <Route path="tickets" element={<TicketsWorkspace base="/tecnico/tickets" />}>
            <Route index element={null} />
            <Route path=":id" element={<TicketDetailPage />} />
          </Route>
          <Route
            path="asignados"
            element={
              <TicketsWorkspace
                base="/tecnico/asignados"
                soloAsignados
                titulo="Mis asignados"
              />
            }
          >
            <Route index element={null} />
            <Route path=":id" element={<TicketDetailPage />} />
          </Route>
          <Route path="historico" element={<HistoricoPage />} />
          <Route path="aprobaciones" element={<AprobacionesPage />} />
          <Route path="usuarios" element={<UsuariosSoloLecturaPage />} />
          <Route path="ranking" element={<RankingPage />} />
          <Route path="reportes" element={<ReportesPage />} />
        </Route>
      </Route>

      <Route element={<RequireAuth rol="administrador" />}>
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<ReportesPage />} />
          <Route path="tickets" element={<TicketsWorkspace base="/admin/tickets" />}>
            <Route index element={null} />
            <Route path=":id" element={<TicketDetailPage />} />
          </Route>
          <Route
            path="asignados"
            element={
              <TicketsWorkspace
                base="/admin/asignados"
                soloAsignados
                titulo="Mis asignados"
              />
            }
          >
            <Route index element={null} />
            <Route path=":id" element={<TicketDetailPage />} />
          </Route>
          <Route path="historico" element={<HistoricoPage />} />
          <Route path="aprobaciones" element={<AprobacionesPage />} />
          <Route path="usuarios" element={<UsuariosPage />} />
          <Route path="areas" element={<AreasPage />} />
          <Route path="datos" element={<DatosHistoricosPage />} />
          <Route path="bitacora" element={<BitacoraPage />} />
          <Route path="ranking" element={<RankingPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
