import { ArrowLeft, Copy, Sparkles } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  actualizarTicket,
  listarInteracciones,
  obtenerCliente,
  obtenerTicket,
} from "../../api";
import Alert from "../../components/ui/Alert";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Card from "../../components/ui/Card";
import Spinner from "../../components/ui/Spinner";
import EstadoBadge from "../../components/EstadoBadge";
import ChatConversacion from "../../components/ChatConversacion";
import MinutitoPanelProximamente from "../../components/MinutitoPanelProximamente";

const TABS = ["Descripción", "Historial", "Archivos", "Notas"];

export default function TicketDetailPage() {
  const { id } = useParams();
  const [ticket, setTicket] = useState(null);
  const [cliente, setCliente] = useState(null);
  const [interacciones, setInteracciones] = useState([]);
  const [actualizando, setActualizando] = useState(false);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("Descripción");
  const [copiado, setCopiado] = useState(false);

  const cargar = useCallback(async () => {
    const t = await obtenerTicket(id);
    setTicket(t);
    const [c, ints] = await Promise.all([
      obtenerCliente(t.cliente_id),
      listarInteracciones(id),
    ]);
    setCliente(c);
    setInteracciones(ints);
  }, [id]);

  useEffect(() => {
    cargar().catch((e) => setError(e.message));
  }, [cargar]);

  async function marcarResuelto() {
    setActualizando(true);
    setError(null);
    try {
      await actualizarTicket(id, { estado: "resuelto", resuelto_por: "tecnico" });
      await cargar();
    } catch (e) {
      setError(e.message);
    } finally {
      setActualizando(false);
    }
  }

  async function tomarEnProceso() {
    setActualizando(true);
    setError(null);
    try {
      await actualizarTicket(id, { estado: "en_proceso" });
      await cargar();
    } catch (e) {
      setError(e.message);
    } finally {
      setActualizando(false);
    }
  }

  function copiarLink() {
    navigator.clipboard.writeText(window.location.href).then(() => {
      setCopiado(true);
      setTimeout(() => setCopiado(false), 1500);
    });
  }

  if (error && !ticket) return <Alert variant="danger">{error}</Alert>;
  if (!ticket) return <Spinner size="sm" />;

  const resuelto = ticket.estado === "resuelto";
  const iniciales = (cliente?.nombre || "")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0])
    .join("")
    .toUpperCase();

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <div className="lg:col-span-2">
        <div className="mb-3 flex items-center gap-3">
          <Link to="/tecnico" className="text-gray-400 hover:text-gray-700">
            <ArrowLeft size={18} />
          </Link>
          <h1 className="text-lg font-semibold text-gray-900">Ticket #{ticket.id}</h1>
          <EstadoBadge estado={ticket.estado} />
          <button
            onClick={copiarLink}
            className="ml-auto flex items-center gap-1 text-xs text-gray-400 hover:text-gray-700"
            title="Copiar enlace"
          >
            <Copy size={14} />
            {copiado ? "¡Copiado!" : ""}
          </button>
        </div>

        {error && (
          <Alert variant="danger" className="mb-3">
            {error}
          </Alert>
        )}

        <Card className="mb-4">
          <Card.Body>
            <div className="mb-3 flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gray-900 text-xs font-semibold text-white">
                {iniciales}
              </div>
              <div>
                <div className="text-sm font-medium text-gray-900">{cliente?.nombre}</div>
                <div className="text-xs text-gray-500">
                  {cliente?.email} · {new Date(ticket.creado_en).toLocaleString()}
                </div>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge>Tipo: {ticket.tipo_predicho || "sin determinar"}</Badge>
              <Badge>Categoría: {ticket.categoria_predicha || "sin determinar"}</Badge>
              {ticket.confianza_clasificacion != null && (
                <Badge>Confianza: {Math.round(ticket.confianza_clasificacion * 100)}%</Badge>
              )}
              {ticket.resuelto_por && <Badge>Resuelto por: {ticket.resuelto_por}</Badge>}
            </div>
          </Card.Body>
        </Card>

        <div className="mb-4 flex gap-1 border-b border-gray-200">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              disabled={t !== "Descripción"}
              title={t !== "Descripción" ? "Próximamente" : undefined}
              className={`px-3 py-2 text-sm font-medium ${
                t !== "Descripción"
                  ? "cursor-not-allowed text-gray-300"
                  : tab === t
                    ? "border-b-2 border-gray-900 text-gray-900"
                    : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        <Card className="mb-4">
          <Card.Body>
            <p className="mb-4">{ticket.texto}</p>

            <div className="mb-4 rounded-lg border border-gray-100 bg-gray-50 p-4 opacity-70">
              <div className="mb-1 flex items-center gap-2 text-sm font-semibold text-gray-500">
                <Sparkles size={14} />
                Sugerencias del asistente
                <span className="rounded-full bg-gray-200 px-1.5 py-0.5 text-[10px] text-gray-500">
                  Próximamente
                </span>
              </div>
              <p className="text-sm text-gray-400">
                Minutito podrá sugerir pasos de resolución basados en el historial de tickets
                similares.
              </p>
            </div>

            {!resuelto && (
              <div className="flex gap-2">
                {ticket.estado !== "en_proceso" && (
                  <Button variant="outlineSecondary" size="sm" onClick={tomarEnProceso} disabled={actualizando}>
                    Tomar ticket (en proceso)
                  </Button>
                )}
                <Button variant="outlineSuccess" size="sm" onClick={marcarResuelto} disabled={actualizando}>
                  Marcar resuelto
                </Button>
              </div>
            )}
            {resuelto && <Alert variant="success">Este ticket ya está resuelto.</Alert>}
          </Card.Body>
        </Card>

        <h2 className="mb-2 text-sm font-semibold text-gray-700">
          Conversación del colaborador con Minutito
        </h2>
        <ChatConversacion interacciones={interacciones} />
      </div>

      <div className="lg:col-span-1">
        <div className="lg:sticky lg:top-6 lg:h-[calc(100vh-8rem)]">
          <MinutitoPanelProximamente />
        </div>
      </div>
    </div>
  );
}
