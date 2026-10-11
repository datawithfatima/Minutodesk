import { Navigate, Route, Routes } from "react-router-dom";
import InicioPage from "./pages/InicioPage";
import LoginPage from "./pages/LoginPage";
import OlvidePasswordPage from "./pages/OlvidePasswordPage";
import EstablecerPasswordPage from "./pages/EstablecerPasswordPage";
import RequireAuth from "./components/RequireAuth";

import UsuarioLayout from "./components/UsuarioLayout";
import DashboardPage from "./pages/usuario/DashboardPage";
import MisTicketsPage from "./pages/usuario/MisTicketsPage";
import UsuarioTicketDetailPage from "./pages/usuario/TicketDetailPage";
import MisLogrosPage from "./pages/usuario/GamificacionPage";
import FaqsPage from "./pages/usuario/FaqsPage";

import TecnicoLayout from "./components/TecnicoLayout";
import TicketsWorkspace from "./pages/tecnico/TicketsWorkspace";
import TicketDetailPage from "./pages/tecnico/TicketDetailPage";
import RankingPage from "./pages/tecnico/GamificacionPage";
import UsuariosSoloLecturaPage from "./pages/tecnico/ClientesPage";

import AdminLayout from "./components/AdminLayout";
import UsuariosPage from "./pages/admin/UsuariosPage";
import AreasPage from "./pages/admin/AreasPage";
import ImportarPage from "./pages/admin/ImportarPage";

import HistoricoPage from "./pages/compartido/HistoricoPage";
import ReportesPage from "./pages/compartido/ReportesPage";

const SUBTITULO_ASIGNADOS = "Los tickets que tomaste o resolviste.";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<InicioPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/olvide-password" element={<OlvidePasswordPage />} />
      <Route path="/establecer-password" element={<EstablecerPasswordPage />} />

      <Route element={<RequireAuth rol="usuario" />}>
        <Route path="/usuario" element={<UsuarioLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="mis-tickets" element={<MisTicketsPage />} />
          <Route path="tickets/:id" element={<UsuarioTicketDetailPage />} />
          <Route path="logros" element={<MisLogrosPage />} />
          <Route path="historico" element={<HistoricoPage />} />
          <Route path="faqs" element={<FaqsPage />} />
          <Route path="reportes" element={<ReportesPage />} />
        </Route>
      </Route>

      <Route element={<RequireAuth rol="tecnico" />}>
        <Route path="/tecnico" element={<TecnicoLayout />}>
          <Route index element={<Navigate to="tickets" replace />} />
          <Route path="tickets" element={<TicketsWorkspace base="/tecnico/tickets" />}>
            <Route index />
            <Route path=":id" element={<TicketDetailPage />} />
          </Route>
          <Route
            path="asignados"
            element={
              <TicketsWorkspace
                base="/tecnico/asignados"
                soloAsignados
                titulo="Mis asignados"
                subtitulo={SUBTITULO_ASIGNADOS}
              />
            }
          >
            <Route index />
            <Route path=":id" element={<TicketDetailPage />} />
          </Route>
          <Route path="historico" element={<HistoricoPage />} />
          <Route path="usuarios" element={<UsuariosSoloLecturaPage />} />
          <Route path="ranking" element={<RankingPage />} />
          <Route path="reportes" element={<ReportesPage />} />
        </Route>
      </Route>

      <Route element={<RequireAuth rol="administrador" />}>
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<ReportesPage />} />
          <Route path="tickets" element={<TicketsWorkspace base="/admin/tickets" />}>
            <Route index />
            <Route path=":id" element={<TicketDetailPage />} />
          </Route>
          <Route
            path="asignados"
            element={
              <TicketsWorkspace
                base="/admin/asignados"
                soloAsignados
                titulo="Mis asignados"
                subtitulo={SUBTITULO_ASIGNADOS}
              />
            }
          >
            <Route index />
            <Route path=":id" element={<TicketDetailPage />} />
          </Route>
          <Route path="historico" element={<HistoricoPage />} />
          <Route path="usuarios" element={<UsuariosPage />} />
          <Route path="areas" element={<AreasPage />} />
          <Route path="datos" element={<ImportarPage />} />
          <Route path="ranking" element={<RankingPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
