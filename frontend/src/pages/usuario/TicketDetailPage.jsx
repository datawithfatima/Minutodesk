import { useCallback, useEffect, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import { obtenerTicket } from "../../api";
import Alert from "../../components/ui/Alert";
import Badge from "../../components/ui/Badge";
import Card from "../../components/ui/Card";
import Spinner from "../../components/ui/Spinner";
import EstadoBadge from "../../components/EstadoBadge";
import ArchivosTicket from "../../components/tickets/ArchivosTicket";
import ConversacionMinutito from "../../components/tickets/ConversacionMinutito";
import ConversacionTicket from "../../components/tickets/ConversacionTicket";
import DatosAlta from "../../components/tickets/DatosAlta";
import { tituloTipo } from "../../components/tickets/formato";
import { PrioridadPastilla } from "../../components/tickets/Pastillas";

export default function TicketDetailPage() {
  const { id } = useParams();
  const estadoNavegacion = useLocation().state;
  const creado = estadoNavegacion?.creado === true; // viene de «Crear ticket»
  // Archivos que no se pudieron subir al crear el ticket (se pueden volver a adjuntar aquí).
  const avisosDeSubida = estadoNavegacion?.avisos?.length
    ? `No se pudo adjuntar: ${estadoNavegacion.avisos.join(" ")} Puedes volver a intentarlo aquí.`
    : null;
  const [ticket, setTicket] = useState(null);
  const [error, setError] = useState(null);

  const cargar = useCallback(async () => setTicket(await obtenerTicket(id)), [id]);

  useEffect(() => {
    cargar().catch((e) => setError(e.message));
  }, [cargar]);

  if (error && !ticket) return <Alert variant="danger">{error}</Alert>;
  if (!ticket) return <Spinner size="sm" />;

  const resuelto = ticket.estado === "resuelto";
  const cancelado = ticket.estado === "cancelado";

  return (
    <>
      <div className="mb-3 flex items-center justify-between gap-3">
        <h1 className="text-xl font-semibold sm:text-2xl">Ticket #{ticket.id}</h1>
        <EstadoBadge estado={ticket.estado} />
      </div>

      {creado && (
        <Alert variant="success" className="mb-3">
          Tu ticket quedó registrado y un técnico lo atenderá. Puedes escribirle por el chat con soporte.
        </Alert>
      )}

      {error && (
        <Alert variant="danger" className="mb-3">
          {error}
        </Alert>
      )}

      <Card className="mb-4">
        <Card.Body>
          <p className="mb-3 whitespace-pre-line break-words">{ticket.texto}</p>
          <div className="flex flex-wrap items-center gap-2">
            <Badge>Tipo: {tituloTipo(ticket.tipo || ticket.tipo_predicho) || "sin determinar"}</Badge>
            <Badge>Categoría: {ticket.categoria || ticket.categoria_predicha || "sin determinar"}</Badge>
            <PrioridadPastilla prioridad={ticket.prioridad} />
            {ticket.resuelto_por && <Badge>Resuelto por: {ticket.resuelto_por}</Badge>}
          </div>
        </Card.Body>
      </Card>

      {ticket.datos_alta && (
        <div className="mb-4">
          <DatosAlta datosJson={ticket.datos_alta} />
        </div>
      )}

      <h2 className="mb-2 text-lg font-semibold">Archivos adjuntos</h2>
      <div className="mb-5">
        <ArchivosTicket ticketId={id} resuelto={resuelto || cancelado} avisoInicial={avisosDeSubida} />
      </div>

      <h2 className="mb-2 text-lg font-semibold">Chat con soporte</h2>
      <Card className="mb-5">
        <Card.Body>
          <ConversacionTicket ticket={ticket} />
        </Card.Body>
      </Card>

      <h2 className="mb-2 text-lg font-semibold">Conversación con Minutito</h2>
      <div className="mb-5">
        <ConversacionMinutito ticketId={id} nombre="Tú" />
      </div>

      {cancelado && (
        <Alert variant="secondary">
          <strong className="font-semibold text-noche">El equipo de soporte canceló este ticket.</strong>
          {ticket.motivo_cancelacion && <> Motivo: {ticket.motivo_cancelacion}</>}
          <span className="mt-1 block">Si el problema sigue, crea un ticket nuevo.</span>
        </Alert>
      )}

      {resuelto && <Alert variant="success">Este ticket ya está resuelto.</Alert>}
    </>
  );
}
