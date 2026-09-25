import { Route, Routes } from "react-router-dom";
import InicioPage from "./pages/InicioPage";
import LoginPage from "./pages/LoginPage";
import RegistroPage from "./pages/RegistroPage";
import RequireAuth from "./components/RequireAuth";

import UsuarioLayout from "./components/UsuarioLayout";
import DashboardPage from "./pages/usuario/DashboardPage";
import MisTicketsPage from "./pages/usuario/MisTicketsPage";
import UsuarioTicketDetailPage from "./pages/usuario/TicketDetailPage";
import UsuarioGamificacionPage from "./pages/usuario/GamificacionPage";

import TecnicoLayout from "./components/TecnicoLayout";
import ColaPage from "./pages/tecnico/ColaPage";
import TecnicoTicketDetailPage from "./pages/tecnico/TicketDetailPage";
import TecnicoGamificacionPage from "./pages/tecnico/GamificacionPage";
import ClientesPage from "./pages/tecnico/ClientesPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<InicioPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/registro" element={<RegistroPage />} />

      <Route element={<RequireAuth rol="colaborador" />}>
        <Route path="/usuario" element={<UsuarioLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="mis-tickets" element={<MisTicketsPage />} />
          <Route path="tickets/:id" element={<UsuarioTicketDetailPage />} />
          <Route path="gamificacion" element={<UsuarioGamificacionPage />} />
        </Route>
      </Route>

      <Route element={<RequireAuth rol="tecnico" />}>
        <Route path="/tecnico" element={<TecnicoLayout />}>
          <Route index element={<ColaPage />} />
          <Route path="tickets/:id" element={<TecnicoTicketDetailPage />} />
          <Route path="clientes" element={<ClientesPage />} />
          <Route path="gamificacion" element={<TecnicoGamificacionPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
