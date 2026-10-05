import { History, MessageCircle, Plus, Ticket } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listarTickets } from "../../api";
import { obtenerUsuario } from "../../auth";
import Card from "../../components/ui/Card";
import Spinner from "../../components/ui/Spinner";
import EstadoBadge from "../../components/EstadoBadge";
import MinutitoPanel from "../../components/MinutitoPanel";

const ACCIONES = [
  {
    to: "/usuario",
    icon: Plus,
    titulo: "Nuevo ticket",
    texto: "Reporta un problema o solicita un servicio.",
  },
  {
    to: "/usuario/mis-tickets",
    icon: Ticket,
    titulo: "Mis tickets",
    texto: "Revisa el estado de tus solicitudes.",
  },
  {
    to: "/usuario/historico",
    icon: History,
    titulo: "Mi histórico",
    texto: "Revisa tus consultas ya resueltas.",
  },
  {
    to: "/usuario",
    icon: MessageCircle,
    titulo: "Habla con Minutito",
    texto: "Nuestro asistente virtual te ayuda al instante.",
  },
];

export default function DashboardPage() {
  const usuario = obtenerUsuario();
  const [tickets, setTickets] = useState([]);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    listarTickets()
      .then((lista) => setTickets(lista.slice(0, 5)))
      .catch(() => {})
      .finally(() => setCargando(false));
  }, []);

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <div className="lg:col-span-2">
        <Card className="mb-6 overflow-hidden">
          <Card.Body className="flex items-center justify-between gap-4">
            <div>
              <h1 className="text-xl font-bold text-gray-900">
                ¡Hola, {usuario?.nombre?.split(" ")[0]}!
              </h1>
              <p className="mb-2 text-gray-500">¿En qué podemos ayudarte hoy?</p>
              <p className="max-w-md text-sm text-gray-500">
                Aquí puedes crear un ticket, revisar el estado de tus solicitudes o hablar
                directamente con Minutito.
              </p>
            </div>
            <img
              src="/img/robot-minutito.jpg"
              alt="Minutito"
              className="hidden h-32 w-32 shrink-0 object-contain sm:block"
            />
          </Card.Body>
        </Card>

        <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {ACCIONES.map((a) => (
            <Link key={a.titulo} to={a.to}>
              <Card className="h-full transition-shadow hover:shadow-md">
                <Card.Body>
                  <a.icon className="mb-2 text-gray-900" size={22} />
                  <div className="font-semibold text-gray-900">{a.titulo}</div>
                  <div className="text-sm text-gray-500">{a.texto}</div>
                </Card.Body>
              </Card>
            </Link>
          ))}
        </div>

        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700">Mis últimos tickets</h2>
          <Link to="/usuario/mis-tickets" className="text-sm text-blue-600 hover:underline">
            Ver todos →
          </Link>
        </div>

        {cargando && <Spinner size="sm" />}
        {!cargando && tickets.length === 0 && (
          <p className="text-sm text-gray-500">Todavía no tienes tickets.</p>
        )}
        {!cargando && tickets.length > 0 && (
          <Card className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 text-gray-600">
                <tr>
                  <th className="px-3 py-2">#</th>
                  <th className="px-3 py-2">Texto</th>
                  <th className="px-3 py-2">Categoría</th>
                  <th className="px-3 py-2">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {tickets.map((t) => (
                  <tr key={t.id} className="hover:bg-gray-50">
                    <td className="px-3 py-2">
                      <Link to={`/usuario/tickets/${t.id}`} className="text-blue-600 hover:underline">
                        {t.id}
                      </Link>
                    </td>
                    <td className="max-w-xs truncate px-3 py-2">{t.texto}</td>
                    <td className="px-3 py-2">{t.categoria_predicha || "—"}</td>
                    <td className="px-3 py-2">
                      <EstadoBadge estado={t.estado} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}
      </div>

      <div className="lg:col-span-1">
        <div className="lg:sticky lg:top-6 lg:h-[calc(100vh-8rem)]">
          <MinutitoPanel />
        </div>
      </div>
    </div>
  );
}
