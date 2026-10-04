import { ArrowLeft, Copy, Sparkles } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useOutletContext, useParams } from "react-router-dom";
import {
  actualizarTicket,
  listarHistorial,
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

const TABS = [
  { nombre: "Descripción", activa: true },
  { nombre: "Historial", activa: true },
  { nombre: "Archivos", activa: false },
  { nombre: "Notas", activa: false },
];

function construirHistorial(cliente, interacciones, cambiosDeEstado) {
  const quien = cliente?.nombre ?? "El usuario";
  const eventos = cambiosDeEstado.map((c) =>
    c.estado_anterior === null
      ? { fecha: c.fecha, titulo: `Ticket creado${cliente ? ` por ${cliente.nombre}` : ""}` }
      : {
          fecha: c.fecha,
          titulo: `Estado: ${c.estado_anterior} → ${c.estado_nuevo}`,
          detalle: `Cambio hecho por ${c.cambiado_por}`,
        }
  );
  interacciones.forEach((i) => {
    eventos.push({
      fecha: i.creado_en,
      titulo: `${quien} escribió a Minutito`,
      detalle: i.mensaje_cliente,
    });
    eventos.push({
      fecha: i.creado_en,
      titulo: "Minutito respondió",
      detalle: i.respuesta_minutito,
      marcoResuelto: i.marco_resuelto,
    });
  });
  return eventos.sort((a, b) => new Date(a.fecha) - new Date(b.fecha));
}

export default function TicketDetailPage() {
  const { id } = useParams();
  const { recargar, base } = useOutletContext();
  const [ticket, setTicket] = useState(null);
  const [cliente, setCliente] = useState(null);
  const [tecnico, setTecnico] = useState(null);
  const [interacciones, setInteracciones] = useState([]);
  const [cambiosDeEstado, setCambiosDeEstado] = useState([]);
  const [actualizando, setActualizando] = useState(false);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("Descripción");
  const [copiado, setCopiado] = useState(false);

  const cargar = useCallback(async () => {
    const t = await obtenerTicket(id);
    setTicket(t);
    const [c, ints, cambios, tec] = await Promise.all([
      obtenerCliente(t.cliente_id),
      listarInteracciones(id),
      listarHistorial(id),
      t.tecnico_id ? obtenerCliente(t.tecnico_id) : Promise.resolve(null),
    ]);
    setCliente(c);
    setInteracciones(ints);
    setCambiosDeEstado(cambios);
    setTecnico(tec);
  }, [id]);

  useEffect(() => {
    setTicket(null);
    setCliente(null);
    setTecnico(null);
    setInteracciones([]);
    setCambiosDeEstado([]);
    setError(null);
    setTab("Descripción");
    cargar().catch((e) => setError(e.message));
  }, [cargar]);

  async function aplicarCambio(cambios) {
    setActualizando(true);
    setError(null);
    try {
      await actualizarTicket(id, cambios);
      await cargar();
      await recargar();
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
    <div>
      <div className="mb-3 flex items-center gap-3">
        <Link to={base} className="text-gray-400 hover:text-gray-700" title="Cerrar detalle">
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
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gray-900 text-xs font-semibold text-white">
              {iniciales}
            </div>
            <div className="min-w-0">
              <div className="truncate text-sm font-medium text-gray-900">{cliente?.nombre}</div>
              <div className="truncate text-xs text-gray-500">
                {cliente?.email} · {new Date(ticket.creado_en).toLocaleString()}
              </div>
            </div>
          </div>
          <div className="mb-3 flex flex-wrap gap-2">
            <Badge>Tipo: {ticket.tipo_predicho || "sin determinar"}</Badge>
            <Badge>Categoría: {ticket.categoria_predicha || "sin determinar"}</Badge>
            {ticket.confianza_clasificacion != null && (
              <Badge>Confianza: {Math.round(ticket.confianza_clasificacion * 100)}%</Badge>
            )}
            {tecnico && <Badge>Atiende: {tecnico.nombre}</Badge>}
            {ticket.resuelto_por && (
              <Badge>
                Resuelto por: {ticket.resuelto_por === "minutito" ? "Minutito" : "equipo de soporte"}
              </Badge>
            )}
          </div>

          {!resuelto && (
            <div className="flex flex-wrap gap-2">
              {ticket.estado !== "en_proceso" && (
                <Button
                  variant="outlineSecondary"
                  size="sm"
                  onClick={() => aplicarCambio({ estado: "en_proceso" })}
                  disabled={actualizando}
                >
                  Tomar ticket (en proceso)
                </Button>
              )}
              <Button
                variant="outlineSuccess"
                size="sm"
                onClick={() => aplicarCambio({ estado: "resuelto", resuelto_por: "tecnico" })}
                disabled={actualizando}
              >
                Marcar resuelto
              </Button>
            </div>
          )}
          {resuelto && <Alert variant="success">Este ticket ya está resuelto.</Alert>}
        </Card.Body>
      </Card>

      <div className="mb-4 flex gap-1 border-b border-gray-200">
        {TABS.map((t) => (
          <button
            key={t.nombre}
            onClick={() => t.activa && setTab(t.nombre)}
            disabled={!t.activa}
            title={!t.activa ? "Próximamente" : undefined}
            className={`px-3 py-2 text-sm font-medium ${
              !t.activa
                ? "cursor-not-allowed text-gray-300"
                : tab === t.nombre
                  ? "border-b-2 border-gray-900 text-gray-900"
                  : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.nombre}
          </button>
        ))}
      </div>

      {tab === "Descripción" && (
        <>
          <Card className="mb-4">
            <Card.Body>
              <p className="mb-4 whitespace-pre-line">{ticket.texto}</p>
              <div className="rounded-lg border border-gray-100 bg-gray-50 p-4 opacity-70">
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
            </Card.Body>
          </Card>

          <h2 className="mb-2 text-sm font-semibold text-gray-700">
            Conversación del usuario con Minutito
          </h2>
          <ChatConversacion interacciones={interacciones} />
        </>
      )}

      {tab === "Historial" && (
        <Card>
          <Card.Body>
            <ol className="relative ml-2 border-l border-gray-200">
              {construirHistorial(cliente, interacciones, cambiosDeEstado).map((e, idx) => (
                <li key={idx} className="mb-4 ml-4 last:mb-0">
                  <span className="absolute -left-[6px] mt-1.5 h-3 w-3 rounded-full border border-white bg-gray-400" />
                  <div className="text-xs text-gray-400">{new Date(e.fecha).toLocaleString()}</div>
                  <div className="text-sm font-medium text-gray-900">{e.titulo}</div>
                  {e.detalle && (
                    <p className="whitespace-pre-line text-sm text-gray-600">{e.detalle}</p>
                  )}
                  {e.marcoResuelto && <Badge color="green">Marcó como resuelto</Badge>}
                </li>
              ))}
            </ol>
          </Card.Body>
        </Card>
      )}
    </div>
  );
}
