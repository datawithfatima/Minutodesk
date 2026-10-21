import { Check, Copy } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useOutletContext, useParams } from "react-router-dom";
import {
  actualizarTicket,
  cancelarTicket,
  listarHistorial,
  listarInteracciones,
  obtenerCatalogos,
  obtenerCliente,
  obtenerTicket,
  obtenerUmbralConfianza,
} from "../../api";
import ArchivosTicket from "../../components/tickets/ArchivosTicket";
import DatosAlta from "../../components/tickets/DatosAlta";
import { tituloTipo } from "../../components/tickets/formato";
import { PrioridadPastilla } from "../../components/tickets/Pastillas";
import { inputClass, labelClass } from "../../components/ui/formStyles";
import Alert from "../../components/ui/Alert";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Card from "../../components/ui/Card";
import Spinner from "../../components/ui/Spinner";
import EstadoBadge from "../../components/EstadoBadge";
import { ETIQUETA_ESTADO } from "../../texto";
import ConversacionTicket from "../../components/tickets/ConversacionTicket";

const TABS = [
  { nombre: "Chat con el usuario", activa: true },
  { nombre: "Historial", activa: true },
  { nombre: "Archivos", activa: true },
  { nombre: "Notas", activa: false },
];

function Dato({ etiqueta, children }) {
  return (
    <div className="flex items-start justify-between gap-3 py-2.5">
      <dt className="shrink-0 text-sm text-gray-500">{etiqueta}</dt>
      <dd className="min-w-0 text-right text-sm font-medium text-noche">{children}</dd>
    </div>
  );
}

function construirHistorial(cliente, interacciones, cambiosDeEstado) {
  const quien = cliente?.nombre ?? "El usuario";
  const eventos = cambiosDeEstado.map((c) =>
    c.estado_anterior === null
      ? { fecha: c.fecha, titulo: `Ticket creado${cliente ? ` por ${cliente.nombre}` : ""}` }
      : c.estado_nuevo === "cancelado"
        ? {
            fecha: c.fecha,
            titulo: `Ticket cancelado por ${c.cambiado_por}`,
            detalle: c.motivo ? `Motivo: ${c.motivo}` : undefined,
          }
        : {
            fecha: c.fecha,
            titulo: `Estado: ${ETIQUETA_ESTADO[c.estado_anterior] ?? c.estado_anterior} → ${
              ETIQUETA_ESTADO[c.estado_nuevo] ?? c.estado_nuevo
            }`,
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

const MIN_MOTIVO = 5;

/** Cancelar exige motivo: el usuario lo verá en su ticket y queda en el historial. */
function CancelarTicket({ deshabilitado, onConfirmar }) {
  const [abierto, setAbierto] = useState(false);
  const [motivo, setMotivo] = useState("");
  const [enviando, setEnviando] = useState(false);

  if (!abierto) {
    return (
      <button
        type="button"
        onClick={() => setAbierto(true)}
        disabled={deshabilitado}
        className="mt-1 rounded-lg py-1.5 text-sm font-medium text-red-600 transition-colors duration-150 hover:bg-red-50 disabled:opacity-50"
      >
        Cancelar ticket
      </button>
    );
  }

  async function confirmar(e) {
    e.preventDefault();
    setEnviando(true);
    const ok = await onConfirmar(motivo.trim());
    setEnviando(false);
    if (ok) setAbierto(false);
  }

  const valido = motivo.trim().length >= MIN_MOTIVO;
  return (
    <form onSubmit={confirmar} className="mt-1 space-y-2 rounded-xl border border-red-200 bg-red-50/40 p-3">
      <label htmlFor="motivo-cancelacion" className="block text-sm font-medium text-noche">
        Motivo de la cancelación
      </label>
      <textarea
        id="motivo-cancelacion"
        rows={3}
        maxLength={500}
        autoFocus
        value={motivo}
        onChange={(e) => setMotivo(e.target.value)}
        placeholder="Ej.: duplicado del ticket #12, o el usuario ya no lo necesita."
        aria-describedby="motivo-ayuda"
        className={`${inputClass} resize-y`}
      />
      <p id="motivo-ayuda" className="text-xs text-gray-500">
        El usuario verá este motivo en su ticket. No cuenta como resuelto.
      </p>
      <div className="flex flex-wrap gap-2">
        <Button type="submit" variant="outlineDanger" size="sm" disabled={!valido || enviando}>
          {enviando ? <Spinner size="sm" /> : "Confirmar cancelación"}
        </Button>
        <Button type="button" variant="outlineSecondary" size="sm" onClick={() => setAbierto(false)}>
          Volver
        </Button>
      </div>
    </form>
  );
}

export default function TicketDetailPage() {
  const { id } = useParams();
  const { recargar } = useOutletContext();
  const [ticket, setTicket] = useState(null);
  const [cliente, setCliente] = useState(null);
  const [tecnico, setTecnico] = useState(null);
  const [interacciones, setInteracciones] = useState([]);
  const [cambiosDeEstado, setCambiosDeEstado] = useState([]);
  const [actualizando, setActualizando] = useState(false);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("Chat con el usuario");
  const [copiado, setCopiado] = useState(false);
  const [umbralConfianza, setUmbralConfianza] = useState(null);
  const [catalogos, setCatalogos] = useState(null);

  useEffect(() => {
    obtenerCatalogos()
      .then(setCatalogos)
      .catch(() => {});
  }, []);

  useEffect(() => {
    // Por debajo de este umbral, la precisión medida de la categoría no llega a la meta.
    obtenerUmbralConfianza()
      .then((r) => setUmbralConfianza(r.umbral ?? null))
      .catch(() => {});
  }, []);

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
    setTab("Chat con el usuario");
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

  async function cancelar(motivo) {
    setError(null);
    try {
      await cancelarTicket(id, motivo);
      await cargar();
      await recargar();
      return true;
    } catch (e) {
      setError(e.message);
      return false;
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
  const cancelado = ticket.estado === "cancelado";
  const iniciales = (cliente?.nombre || "")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0])
    .join("")
    .toUpperCase();

  const confianzaBaja =
    umbralConfianza != null &&
    ticket.confianza_clasificacion != null &&
    ticket.confianza_clasificacion < umbralConfianza;

  return (
    <div>
      {error && (
        <Alert variant="danger" className="mb-4">
          {error}
        </Alert>
      )}

      <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-[minmax(0,1fr)_320px] lg:grid-rows-[auto_1fr]">
        {/* ───── Contenido del ticket ───── */}
        {/* En móvil el orden es: ticket, gestión y conversación; en escritorio, la gestión va a la derecha. */}
          <Card className="min-w-0 max-lg:order-1 lg:col-start-1">
            <Card.Body>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
                <h1 className="text-xl font-semibold tracking-[-0.015em] text-noche">Ticket #{ticket.id}</h1>
                <EstadoBadge estado={ticket.estado} />
                <PrioridadPastilla prioridad={ticket.prioridad} />
                <button
                  onClick={copiarLink}
                  className="ml-auto inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs text-gray-500 transition-colors duration-150 hover:bg-marfil hover:text-noche"
                >
                  {copiado ? <Check size={14} aria-hidden="true" /> : <Copy size={14} aria-hidden="true" />}
                  {copiado ? "Enlace copiado" : "Copiar enlace"}
                </button>
              </div>

              <div className="mt-4 flex items-center gap-3 border-b border-linea pb-4">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-noche text-xs font-semibold text-white">
                  {iniciales}
                </div>
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-noche">{cliente?.nombre}</div>
                  <div className="truncate text-xs text-gray-500">
                    {cliente?.email} · {new Date(ticket.creado_en).toLocaleString()}
                  </div>
                </div>
              </div>

              <p className="mt-4 whitespace-pre-line break-words text-[15px] leading-relaxed text-noche">
                {ticket.texto}
              </p>
              {ticket.datos_alta && (
                <div className="mt-4">
                  <DatosAlta datosJson={ticket.datos_alta} />
                </div>
              )}

            </Card.Body>
          </Card>

        {/* ───── Gestión y datos (columna lateral) ───── */}
        {/* En móvil la columna se «disuelve» (contents) para ordenar sus tarjetas entre las demás. */}
        <div className="contents lg:sticky lg:top-22 lg:col-start-2 lg:row-span-2 lg:row-start-1 lg:block lg:space-y-4 lg:self-start">
          <Card className="max-lg:order-2">
            <Card.Body className="space-y-4">
              <h2 className="text-sm font-semibold text-noche">Gestión</h2>

              {resuelto ? (
                <Alert variant="success">Este ticket ya está resuelto.</Alert>
              ) : cancelado ? (
                <div className="space-y-3">
                  <Alert variant="secondary">
                    <strong className="font-semibold text-noche">Ticket cancelado.</strong>
                    {ticket.motivo_cancelacion && <> Motivo: {ticket.motivo_cancelacion}</>}
                  </Alert>
                  <Button
                    variant="outlineSecondary"
                    onClick={() => aplicarCambio({ estado: "abierto" })}
                    disabled={actualizando}
                    className="w-full"
                  >
                    Reabrir ticket
                  </Button>
                </div>
              ) : (
                <div className="grid gap-2">
                  {ticket.estado !== "en_proceso" && (
                    <Button
                      variant="outlineSecondary"
                      onClick={() => aplicarCambio({ estado: "en_proceso" })}
                      disabled={actualizando}
                      className="w-full"
                    >
                      Tomar ticket
                    </Button>
                  )}
                  <Button
                    variant="primary"
                    onClick={() => aplicarCambio({ estado: "resuelto", resuelto_por: "tecnico" })}
                    disabled={actualizando}
                    className="w-full"
                  >
                    Marcar como resuelto
                  </Button>
                  <CancelarTicket deshabilitado={actualizando} onConfirmar={cancelar} />
                </div>
              )}

              {catalogos && (
                <div className="space-y-3 border-t border-linea pt-4">
                  <div>
                    <label htmlFor="gestion-categoria" className={labelClass}>
                      Categoría
                    </label>
                    <select
                      id="gestion-categoria"
                      className={inputClass}
                      value={ticket.categoria || ""}
                      disabled={actualizando || !!ticket.datos_alta}
                      onChange={(e) => e.target.value && aplicarCambio({ categoria: e.target.value })}
                    >
                      <option value="">
                        {ticket.categoria_predicha ? `Sin confirmar (SVM: ${ticket.categoria_predicha})` : "Sin categoría"}
                      </option>
                      {catalogos.categorias.map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                      {ticket.datos_alta && <option value={ticket.categoria}>{ticket.categoria}</option>}
                    </select>
                  </div>
                  <div>
                    <label htmlFor="gestion-prioridad" className={labelClass}>
                      Prioridad
                    </label>
                    <select
                      id="gestion-prioridad"
                      className={inputClass}
                      value={ticket.prioridad}
                      disabled={actualizando}
                      onChange={(e) => aplicarCambio({ prioridad: e.target.value })}
                    >
                      {catalogos.prioridades.map((p) => (
                        <option key={p} value={p}>
                          {p}
                        </option>
                      ))}
                    </select>
                  </div>
                  {!ticket.clasificacion_confirmada && ticket.categoria_predicha && (
                    <div>
                      <Button
                        variant="outlinePrimary"
                        size="sm"
                        disabled={actualizando}
                        className="w-full"
                        onClick={() =>
                          aplicarCambio({
                            categoria: ticket.categoria_predicha,
                            ...(ticket.tipo_predicho && ticket.tipo_predicho !== catalogos.tipos[2]?.nombre
                              ? { tipo: ticket.tipo_predicho }
                              : {}),
                          })
                        }
                      >
                        Confirmar la clasificación del SVM
                      </Button>
                      <p className="mt-1.5 text-xs text-gray-500">
                        Si es correcta, confírmala; si no, elige otra categoría. Así se mide el acierto real.
                      </p>
                    </div>
                  )}
                </div>
              )}
            </Card.Body>
          </Card>

          <Card className="max-lg:order-4">
            <Card.Body>
              <h2 className="text-sm font-semibold text-noche">Detalles</h2>
              <dl className="mt-1 divide-y divide-linea">
                <Dato etiqueta="Tipo">{tituloTipo(ticket.tipo || ticket.tipo_predicho) || "Sin determinar"}</Dato>
                <Dato etiqueta="Categoría">{ticket.categoria || ticket.categoria_predicha || "Sin determinar"}</Dato>
                {ticket.categoria_predicha && (
                  <Dato etiqueta="Sugerencia del SVM">
                    {ticket.categoria_predicha}
                    {ticket.confianza_clasificacion != null && (
                      <span className="block text-xs font-normal text-gray-500">
                        Confianza {Math.round(ticket.confianza_clasificacion * 100)}%
                      </span>
                    )}
                  </Dato>
                )}
                <Dato etiqueta="Clasificación">
                  {ticket.clasificacion_confirmada ? (
                    <Badge color="green">Confirmada</Badge>
                  ) : confianzaBaja ? (
                    <Badge color="amber">Confianza baja: revisar</Badge>
                  ) : (
                    <span className="font-normal text-gray-500">Sin confirmar</span>
                  )}
                </Dato>
                <Dato etiqueta="Atiende">{tecnico?.nombre ?? <span className="font-normal text-gray-500">Nadie aún</span>}</Dato>
                {ticket.resuelto_por && (
                  <Dato etiqueta="Resuelto por">
                    {ticket.resuelto_por === "minutito" ? "Minutito" : "Equipo de soporte"}
                  </Dato>
                )}
                <Dato etiqueta="Creado">{new Date(ticket.creado_en).toLocaleDateString()}</Dato>
              </dl>
            </Card.Body>
          </Card>
        </div>

          <div className="min-w-0 max-lg:order-3 lg:col-start-1">
            <div role="tablist" className="mb-4 flex gap-1 overflow-x-auto border-b border-linea">
              {TABS.map((t) => (
                <button
                  key={t.nombre}
                  role="tab"
                  aria-selected={tab === t.nombre}
                  onClick={() => t.activa && setTab(t.nombre)}
                  disabled={!t.activa}
                  title={!t.activa ? "Próximamente" : undefined}
                  className={`-mb-px shrink-0 whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium transition-colors duration-150 ${
                    !t.activa
                      ? "cursor-not-allowed border-transparent text-gray-300"
                      : tab === t.nombre
                        ? "border-acento text-noche"
                        : "border-transparent text-gray-500 hover:text-noche"
                  }`}
                >
                  {t.nombre}
                  {!t.activa && <span className="ml-1.5 text-[10px] font-normal">Próx.</span>}
                </button>
              ))}
            </div>

            {tab === "Chat con el usuario" && (
              <Card>
                <Card.Body>
                  <ConversacionTicket key={ticket.id} ticket={ticket} esPersonal />
                </Card.Body>
              </Card>
            )}

            {tab === "Archivos" && (
              <Card>
                <Card.Body>
                  <ArchivosTicket ticketId={id} resuelto={resuelto || cancelado} />
                </Card.Body>
              </Card>
            )}

            {tab === "Historial" && (
              <Card>
                <Card.Body>
                  <ol className="relative ml-2 border-l border-linea">
                    {construirHistorial(cliente, interacciones, cambiosDeEstado).map((e, idx) => (
                      <li key={idx} className="mb-4 ml-4 last:mb-0">
                        <span className="absolute -left-[6px] mt-1.5 h-3 w-3 rounded-full border-2 border-white bg-acento" />
                        <div className="text-xs text-gray-400">{new Date(e.fecha).toLocaleString()}</div>
                        <div className="text-sm font-medium text-noche">{e.titulo}</div>
                        {e.detalle && <p className="whitespace-pre-line text-sm text-gray-600">{e.detalle}</p>}
                        {e.marcoResuelto && <Badge color="green">El usuario confirmó que se resolvió</Badge>}
                      </li>
                    ))}
                  </ol>
                </Card.Body>
              </Card>
            )}
          </div>
      </div>
    </div>
  );
}
