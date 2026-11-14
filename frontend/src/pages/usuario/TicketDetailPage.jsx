import { Bot, CalendarDays, CheckCircle2, ClipboardCheck, ClipboardList, Flag, Layers, MessageSquare, Paperclip, Tag, TimerReset } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import { obtenerTicket } from "../../api";
import Alert from "../../components/ui/Alert";
import Spinner from "../../components/ui/Spinner";
import EstadoBadge from "../../components/EstadoBadge";
import ArchivosTicket from "../../components/tickets/ArchivosTicket";
import ConversacionMinutito from "../../components/tickets/ConversacionMinutito";
import ConversacionTicket from "../../components/tickets/ConversacionTicket";
import DatosAlta from "../../components/tickets/DatosAlta";
import EncuestaSatisfaccion from "../../components/tickets/EncuestaSatisfaccion";
import { tituloTipo } from "../../components/tickets/formato";
import { PrioridadPastilla } from "../../components/tickets/Pastillas";
import { CabeceraTicket, CicloEstado, FilaFicha, PanelFicha } from "../../components/tickets/FichaTicket";
import { TemporizadorSla } from "../../components/tickets/TemporizadorSla";

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

      <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="min-w-0 space-y-5">
          {/* Ficha del ticket: cabecera en grafito con su avance y la descripción debajo */}
          <div className="overflow-hidden rounded-lg border border-linea bg-superficie shadow-[0_1px_0_rgb(27_30_34/0.04),0_1px_3px_rgb(27_30_34/0.05)]">
            <CabeceraTicket
              ticket={ticket}
              etiqueta="Tu solicitud"
              insignias={
                <>
                  <EstadoBadge estado={ticket.estado} />
                  <span className="chip-claro">
                    <PrioridadPastilla prioridad={ticket.prioridad} />
                  </span>
                </>
              }
            >
              <CicloEstado estado={ticket.estado} />
              <TemporizadorSla sla={ticket.sla} className="mt-3" />
            </CabeceraTicket>
            <div className="p-5 sm:p-6">
              <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.14em] text-gray-500">Descripción</div>
              <p className="whitespace-pre-line break-words text-[15px] leading-relaxed text-noche">{ticket.texto}</p>
            </div>
          </div>

          {ticket.datos_alta && <DatosAlta datosJson={ticket.datos_alta} />}

          {cancelado && (
            <Alert variant="secondary">
              <strong className="font-semibold text-noche">El equipo de soporte canceló este ticket.</strong>
              {ticket.motivo_cancelacion && <> Motivo: {ticket.motivo_cancelacion}</>}
              <span className="mt-1 block">Si el problema sigue, crea un ticket nuevo.</span>
            </Alert>
          )}

          {resuelto && (
            <PanelFicha icono={ClipboardCheck} titulo="Acta de recepción · califica la atención" acento>
              <EncuestaSatisfaccion ticketId={id} />
            </PanelFicha>
          )}

          <PanelFicha icono={MessageSquare} titulo="Chat con soporte" acento>
            <ConversacionTicket ticket={ticket} />
          </PanelFicha>

          <PanelFicha icono={Bot} titulo="Conversación con Minutito">
            <ConversacionMinutito ticketId={id} nombre="Tú" />
          </PanelFicha>
        </div>

        <div className="min-w-0 space-y-5 lg:sticky lg:top-22">
          <PanelFicha icono={ClipboardList} titulo="Ficha técnica">
            <dl className="-my-2.5 divide-y divide-dashed divide-linea">
              <FilaFicha icono={Tag} etiqueta="Tipo">
                {tituloTipo(ticket.tipo || ticket.tipo_predicho) || "sin determinar"}
              </FilaFicha>
              <FilaFicha icono={Layers} etiqueta="Categoría">
                {ticket.categoria || ticket.categoria_predicha || "sin determinar"}
              </FilaFicha>
              <FilaFicha icono={Flag} etiqueta="Prioridad">
                <PrioridadPastilla prioridad={ticket.prioridad} />
              </FilaFicha>
              {ticket.sla && (
                <FilaFicha icono={TimerReset} etiqueta="Plazo de atención">
                  {ticket.sla.dias} {ticket.sla.dias === 1 ? "día" : "días"}
                </FilaFicha>
              )}
              {ticket.resuelto_por && (
                <FilaFicha icono={CheckCircle2} etiqueta="Resuelto por">
                  {ticket.resuelto_por}
                </FilaFicha>
              )}
              <FilaFicha icono={CalendarDays} etiqueta="Creado">
                {new Date(ticket.creado_en).toLocaleDateString()}
              </FilaFicha>
            </dl>
          </PanelFicha>

          <PanelFicha icono={Paperclip} titulo="Archivos adjuntos">
            <ArchivosTicket ticketId={id} resuelto={resuelto || cancelado} avisoInicial={avisosDeSubida} />
          </PanelFicha>
        </div>
      </div>
    </>
  );
}
