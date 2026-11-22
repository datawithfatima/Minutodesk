import {
  Bot,
  CalendarDays,
  Check,
  CheckCircle2,
  ClipboardCheck,
  ClipboardList,
  Copy,
  Cpu,
  HardHat,
  History,
  Layers,
  Link2,
  MessageSquare,
  Paperclip,
  ShieldCheck,
  Tag,
  TimerReset,
  Wrench,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useOutletContext, useParams } from "react-router-dom";
import {
  actualizarTicket,
  cancelarTicket,
  liberarTicket,
  listarAsignaciones,
  listarHistorial,
  listarClientes,
  listarInteracciones,
  listarMotivosLiberacion,
  listarMotivosPausa,
  obtenerCatalogos,
  obtenerCliente,
  obtenerTicket,
  obtenerUmbralConfianza,
  pausarSla,
  reanudarSla,
  tomarTicket,
} from "../../api";
import { obtenerUsuario } from "../../auth";
import { PanelAtencion, situacionAtencion } from "../../components/tickets/Atencion";
import ArchivosTicket from "../../components/tickets/ArchivosTicket";
import DatosAlta from "../../components/tickets/DatosAlta";
import ConfirmacionCierre from "../../components/tickets/ConfirmacionCierre";
import EncuestaSatisfaccion from "../../components/tickets/EncuestaSatisfaccion";
import PanelDuplicados from "../../components/tickets/PanelDuplicados";
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
import ConversacionMinutito from "../../components/tickets/ConversacionMinutito";
import ConversacionTicket from "../../components/tickets/ConversacionTicket";
import { PanelPausaSla, TemporizadorSla } from "../../components/tickets/TemporizadorSla";
import {
  BarraConfianza,
  BotonCabecera,
  CabeceraTicket,
  CicloEstado,
  FilaFicha,
  PanelFicha,
  PestanasTicket,
} from "../../components/tickets/FichaTicket";
import Selector from "../../components/ui/Selector";

const ICONO_PESTANA = { Chat: MessageSquare, Minutito: Bot, Historial: History, Archivos: Paperclip };

const TABS = [
  { nombre: "Chat", activa: true },
  { nombre: "Minutito", activa: true },
  { nombre: "Historial", activa: true },
  { nombre: "Archivos", activa: true },
];

const COMO_SE_TOMO = {
  boton: "con «Tomar ticket»",
  respuesta: "al responder al solicitante",
  estado: "al cambiar su estado",
  asignacion: "al asignárselo",
};

function construirHistorial(cliente, interacciones, cambiosDeEstado, pausas = [], asignaciones = []) {
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
  pausas.forEach((p) => {
    eventos.push({
      fecha: p.inicio,
      titulo: `Plazo en pausa: ${p.motivo_titulo}`,
      detalle: `${p.detalle ? `${p.detalle} · ` : ""}${p.automatica ? "pausa automática por una aprobación" : `por ${p.iniciada_por}`}`,
    });
    if (p.fin) {
      eventos.push({
        fecha: p.fin,
        titulo: "Plazo reanudado",
        detalle: p.reanudada_por ? `por ${p.reanudada_por}` : "al responder la aprobación",
      });
    }
  });
  asignaciones.forEach((a) => {
    if (a.accion === "tomado") {
      eventos.push({ fecha: a.fecha, titulo: `${a.tecnico} tomó el ticket`, detalle: COMO_SE_TOMO[a.via] });
    } else if (a.accion === "reasignado") {
      eventos.push({ fecha: a.fecha, titulo: `Reasignado a ${a.tecnico}`, detalle: `por ${a.por}` });
    } else {
      eventos.push({
        fecha: a.fecha,
        titulo: `${a.tecnico ?? "El técnico"} dejó el ticket${a.por_id !== a.tecnico_id ? ` (lo liberó ${a.por})` : ""}`,
        detalle: [a.motivo_titulo, a.detalle].filter(Boolean).join(": "),
      });
    }
  });
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
        className="mt-1 rounded-md py-1.5 text-sm font-medium text-red-600 transition-colors duration-150 hover:bg-red-50 disabled:opacity-50"
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
    <form onSubmit={confirmar} className="mt-1 space-y-2 rounded-lg border border-red-200 bg-red-50/40 p-3">
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
  const [tab, setTab] = useState("Chat");
  const [copiado, setCopiado] = useState(false);
  const [umbralConfianza, setUmbralConfianza] = useState(null);
  const [catalogos, setCatalogos] = useState(null);
  const [tecnicos, setTecnicos] = useState([]);
  const [motivosPausa, setMotivosPausa] = useState([]);
  const [motivosLiberacion, setMotivosLiberacion] = useState([]);
  const [asignaciones, setAsignaciones] = useState([]);
  const yo = obtenerUsuario();
  const esAdmin = yo?.rol === "administrador";

  useEffect(() => {
    obtenerCatalogos()
      .then(setCatalogos)
      .catch(() => {});
    listarMotivosPausa()
      .then(setMotivosPausa)
      .catch(() => {});
    listarMotivosLiberacion()
      .then(setMotivosLiberacion)
      .catch(() => {});
    listarClientes()
      .then((lista) => setTecnicos(lista.filter((c) => c.rol === "tecnico" && c.activo)))
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
    const [c, ints, cambios, tec, asig] = await Promise.all([
      obtenerCliente(t.cliente_id),
      listarInteracciones(id),
      listarHistorial(id),
      t.tecnico_id ? obtenerCliente(t.tecnico_id) : Promise.resolve(null),
      listarAsignaciones(id).catch(() => []),
    ]);
    setAsignaciones(asig);
    // Ticket de la carga masiva: quien lo pidió no tiene cuenta, se muestra su nombre.
    setCliente(t.solicitante_externo ? { ...c, nombre: t.solicitante_externo, email: "Sin cuenta en MinutoDesk" } : c);
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
    setTab("Chat");
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

  async function pausarPlazo(motivo, detalle) {
    setError(null);
    try {
      await pausarSla(id, { motivo, detalle });
      await cargar();
      return true;
    } catch (e) {
      setError(e.message);
      return false;
    }
  }

  async function reanudarPlazo() {
    setActualizando(true);
    setError(null);
    try {
      await reanudarSla(id);
      await cargar();
    } catch (e) {
      setError(e.message);
    } finally {
      setActualizando(false);
    }
  }

  async function tomar() {
    setActualizando(true);
    setError(null);
    try {
      await tomarTicket(id);
    } catch (e) {
      setError(e.message); // p. ej. otro técnico lo tomó un instante antes
    } finally {
      await cargar().catch(() => {});
      await recargar();
      setActualizando(false);
    }
  }

  async function liberar(motivo, detalle) {
    setError(null);
    try {
      await liberarTicket(id, { motivo, detalle });
      await cargar();
      await recargar();
      return true;
    } catch (e) {
      setError(e.message);
      return false;
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

  const categoriaVigente = ticket.categoria || ticket.categoria_predicha;
  // Si atiende alguien que no está en la lista (p. ej. un administrador que lo tomó), se agrega.
  const opcionesTecnico =
    tecnico && !tecnicos.some((t) => t.id === tecnico.id) ? [...tecnicos, tecnico] : tecnicos;

  // Tomado por otro técnico: se ve, pero solo esa persona o un administrador lo cambian.
  const situacion = situacionAtencion(ticket, yo?.id);
  const bloqueado = situacion === "ajeno" && !esAdmin;
  const tomadoSinAdmin = (situacion === "mio" || situacion === "ajeno") && !esAdmin;

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
          <div className="min-w-0 overflow-hidden rounded-lg border border-linea bg-superficie shadow-[0_1px_0_rgb(27_30_34/0.04),0_1px_3px_rgb(27_30_34/0.05)] max-lg:order-1 lg:col-start-1">
            <CabeceraTicket
              ticket={ticket}
              insignias={
                <>
                  <EstadoBadge estado={ticket.estado} />
                  <span className="chip-claro">
                    <PrioridadPastilla prioridad={ticket.prioridad} />
                  </span>
                </>
              }
              acciones={
                <BotonCabecera onClick={copiarLink}>
                  {copiado ? <Check size={14} aria-hidden="true" /> : <Copy size={14} aria-hidden="true" />}
                  {copiado ? "Enlace copiado" : "Copiar enlace"}
                </BotonCabecera>
              }
            >
              <CicloEstado estado={ticket.estado} />
              <TemporizadorSla sla={ticket.sla} className="mt-3" />
            </CabeceraTicket>
            <div className="p-5 sm:p-6">
              <div className="flex items-center gap-3 border-b border-dashed border-linea pb-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-grafito text-xs font-semibold text-casco">
                  {iniciales}
                </div>
                <div className="min-w-0">
                  <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-gray-500">Solicitante</div>
                  <div className="truncate text-sm font-semibold text-noche">{cliente?.nombre}</div>
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

            </div>
          </div>
        {/* ───── Gestión y datos (columna lateral) ───── */}
        {/* En móvil la columna se «disuelve» (contents) para ordenar sus tarjetas entre las demás. */}
        <div className="contents lg:sticky lg:top-22 lg:col-start-2 lg:row-span-2 lg:row-start-1 lg:block lg:space-y-4 lg:self-start">
          <PanelFicha icono={Wrench} titulo="Gestión" acento className="max-lg:order-2">
            <div className="space-y-4">

              {resuelto ? (
                <div className="flex items-center gap-3 rounded-md border border-green-200 bg-green-50 p-3">
                  <span className="anim-sello flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-green-600 text-white">
                    <CheckCircle2 size={18} aria-hidden="true" />
                  </span>
                  <div className="text-sm">
                    <div className="font-semibold text-green-800">Obra entregada</div>
                    <div className="text-green-700">Este ticket ya está resuelto.</div>
                  </div>
                </div>
              ) : cancelado ? (
                <div className="space-y-3">
                  <Alert variant="secondary">
                    <strong className="font-semibold text-noche">Ticket cancelado.</strong>
                    {ticket.motivo_cancelacion && <> Motivo: {ticket.motivo_cancelacion}</>}
                  </Alert>
                  {!bloqueado && (
                    <Button
                      variant="outlineSecondary"
                      onClick={() => aplicarCambio({ estado: "abierto" })}
                      disabled={actualizando}
                      className="w-full"
                    >
                      Reabrir ticket
                    </Button>
                  )}
                </div>
              ) : (
                <div className="grid gap-2">
                  <PanelAtencion
                    ticket={ticket}
                    tecnico={tecnico}
                    yoId={yo?.id}
                    esAdmin={esAdmin}
                    motivos={motivosLiberacion}
                    deshabilitado={actualizando}
                    onTomar={tomar}
                    onLiberar={liberar}
                  />
                  {!bloqueado && (
                    <div className="mt-2 grid gap-2 border-t border-dashed border-linea pt-4">
                      <Button
                        variant={situacion === "mio" ? "primary" : "outlineSecondary"}
                        onClick={() => aplicarCambio({ estado: "resuelto", resuelto_por: "tecnico" })}
                        disabled={actualizando}
                        className="w-full"
                      >
                        Marcar como resuelto
                      </Button>
                      <CancelarTicket deshabilitado={actualizando} onConfirmar={cancelar} />
                    </div>
                  )}
                </div>
              )}

              {ticket.sla && !resuelto && !cancelado && !bloqueado && (
                <div className="space-y-2 border-t border-dashed border-linea pt-4">
                  <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-gray-500">Plazo de atención</p>
                  <PanelPausaSla
                    sla={ticket.sla}
                    motivos={motivosPausa}
                    deshabilitado={actualizando}
                    onPausar={pausarPlazo}
                    onReanudar={reanudarPlazo}
                  />
                </div>
              )}

              {catalogos && (
                <div className="space-y-3 border-t border-dashed border-linea pt-4">
                  <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-gray-500">Clasificación y asignación</p>
                  <div>
                    <label htmlFor="gestion-categoria" className={labelClass}>
                      Categoría
                    </label>
                    <Selector
                      id="gestion-categoria"
                      className={inputClass}
                      value={ticket.categoria || ""}
                      disabled={actualizando || bloqueado || !!ticket.datos_alta}
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
                    </Selector>
                  </div>
                  <div>
                    <label htmlFor="gestion-prioridad" className={labelClass}>
                      Prioridad
                    </label>
                    <Selector
                      id="gestion-prioridad"
                      className={inputClass}
                      value={ticket.prioridad}
                      disabled={actualizando || bloqueado}
                      onChange={(e) => aplicarCambio({ prioridad: e.target.value })}
                    >
                      {catalogos.prioridades.map((p) => (
                        <option key={p} value={p}>
                          {p}
                        </option>
                      ))}
                    </Selector>
                  </div>
                  <div>
                    <label htmlFor="gestion-tecnico" className={labelClass}>
                      Técnico asignado
                    </label>
                    <Selector
                      id="gestion-tecnico"
                      className={inputClass}
                      value={ticket.tecnico_id ?? ""}
                      disabled={actualizando || resuelto || cancelado || tomadoSinAdmin}
                      onChange={(e) => e.target.value && aplicarCambio({ tecnico_id: Number(e.target.value) })}
                    >
                      <option value="">Sin asignar</option>
                      {opcionesTecnico.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.nombre}
                        </option>
                      ))}
                    </Selector>
                    {!resuelto && !cancelado && (
                      <p className="mt-1.5 text-xs text-gray-500">
                        {tomadoSinAdmin ? (
                          situacion === "mio" ? (
                            <>Para pasarlo a otro técnico, libéralo indicando el motivo.</>
                          ) : (
                            <>Solo un administrador puede reasignarlo.</>
                          )
                        ) : esAdmin && ticket.tomado_en ? (
                          <>
                            Tomado. Al elegir a otro técnico, queda a su nombre.{" "}
                            <button
                              type="button"
                              disabled={actualizando}
                              onClick={() => aplicarCambio({ tecnico_auto: true })}
                              className="font-medium text-acento underline-offset-2 hover:underline disabled:opacity-50"
                            >
                              Devolver al sugerido por sistema
                            </button>
                          </>
                        ) : ticket.tecnico_manual ? (
                          <>
                            Elegido a mano.{" "}
                            <button
                              type="button"
                              disabled={actualizando}
                              onClick={() => aplicarCambio({ tecnico_auto: true })}
                              className="font-medium text-acento underline-offset-2 hover:underline disabled:opacity-50"
                            >
                              Volver al sugerido por sistema
                            </button>
                          </>
                        ) : ticket.tecnico_id ? (
                          <>Sugerido según el sistema «{categoriaVigente}». Si no es correcto, elige otro.</>
                        ) : ticket.tecnico_sugerido_id ? (
                          <>
                            Aún sin técnico.{" "}
                            <button
                              type="button"
                              disabled={actualizando}
                              onClick={() => aplicarCambio({ tecnico_auto: true })}
                              className="font-medium text-acento underline-offset-2 hover:underline disabled:opacity-50"
                            >
                              Asignar a{" "}
                              {opcionesTecnico.find((t) => t.id === ticket.tecnico_sugerido_id)?.nombre ??
                                "el sugerido"}
                            </button>{" "}
                            según el sistema «{categoriaVigente}».
                          </>
                        ) : categoriaVigente ? (
                          <>Ningún técnico de «{categoriaVigente}» tiene cuenta todavía. Elige uno a mano.</>
                        ) : (
                          <>Elige quién atiende este ticket.</>
                        )}
                      </p>
                    )}
                  </div>
                  {!ticket.clasificacion_confirmada && ticket.categoria_predicha && !bloqueado && (
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
                    </div>
                  )}
                </div>
              )}
            </div>
          </PanelFicha>

          <PanelFicha icono={ClipboardList} titulo="Ficha técnica" className="max-lg:order-4">
            <dl className="-my-2.5 divide-y divide-dashed divide-linea">
              <FilaFicha icono={Tag} etiqueta="Tipo">
                {tituloTipo(ticket.tipo || ticket.tipo_predicho) || "Sin determinar"}
              </FilaFicha>
              <FilaFicha icono={Layers} etiqueta="Categoría">
                {ticket.categoria || ticket.categoria_predicha || "Sin determinar"}
              </FilaFicha>
              {ticket.categoria_predicha && (
                <FilaFicha icono={Cpu} etiqueta="Sugerencia del SVM">
                  {ticket.categoria_predicha}
                  {ticket.confianza_clasificacion != null && (
                    <BarraConfianza valor={ticket.confianza_clasificacion} umbral={umbralConfianza} />
                  )}
                </FilaFicha>
              )}
              <FilaFicha icono={TimerReset} etiqueta="Plazo">
                {ticket.sla ? (
                  `${ticket.sla.dias} ${ticket.sla.dias === 1 ? "día" : "días"}`
                ) : (
                  <span className="font-normal text-gray-500">Sin tipo</span>
                )}
              </FilaFicha>
              <FilaFicha icono={ShieldCheck} etiqueta="Clasificación">
                {ticket.clasificacion_confirmada ? (
                  <Badge color="green">Confirmada</Badge>
                ) : confianzaBaja ? (
                  <Badge color="amber">Confianza baja: revisar</Badge>
                ) : ticket.categoria_predicha && !ticket.categoria ? (
                  <Badge color="sky">Automática</Badge>
                ) : (
                  <span className="font-normal text-gray-500">Sin confirmar</span>
                )}
              </FilaFicha>
              <FilaFicha icono={HardHat} etiqueta="Atiende">
                {tecnico ? (
                  <span className="inline-flex flex-wrap items-center gap-1.5">
                    {tecnico.nombre}
                    {ticket.tomado_en ? (
                      !resuelto && !cancelado && <Badge color="green">Tomado</Badge>
                    ) : (
                      !resuelto && !cancelado && <Badge color="sky">Sugerido</Badge>
                    )}
                  </span>
                ) : (
                  <span className="font-normal text-gray-500">Nadie aún</span>
                )}
              </FilaFicha>
              {ticket.resuelto_por && (
                <FilaFicha icono={CheckCircle2} etiqueta="Resuelto por">
                  {ticket.resuelto_por === "minutito" ? "Minutito" : "Equipo de soporte"}
                </FilaFicha>
              )}
              <FilaFicha icono={CalendarDays} etiqueta="Creado">
                {new Date(ticket.creado_en).toLocaleDateString()}
              </FilaFicha>
            </dl>
          </PanelFicha>

          <PanelFicha icono={Link2} titulo="Duplicados y afectados" className="max-lg:order-5">
            <PanelDuplicados
              ticket={ticket}
              onCambio={async () => {
                await cargar();
                await recargar();
              }}
            />
          </PanelFicha>

          {ticket.estado === "resuelto" && !ticket.solicitante_externo && (
            <PanelFicha icono={ClipboardCheck} titulo="Satisfacción del usuario" className="max-lg:order-5">
              <ConfirmacionCierre
                key={`${ticket.id}-${ticket.cerrado_en}`}
                ticketId={ticket.id}
                editable={false}
                className="mb-3 border-b border-dashed border-linea pb-3"
              />
              <EncuestaSatisfaccion key={ticket.id} ticketId={ticket.id} editable={false} />
            </PanelFicha>
          )}
        </div>

          <div className="min-w-0 max-lg:order-3 lg:col-start-1">
            <PestanasTicket
              pestanas={TABS.filter((t) => t.activa).map((t) => ({ nombre: t.nombre, Icono: ICONO_PESTANA[t.nombre] }))}
              activa={tab}
              onCambiar={setTab}
            />
            {tab === "Chat" && (
              <Card className="anim-pestana">
                <Card.Body>
                  <ConversacionTicket
                    key={ticket.id}
                    ticket={ticket}
                    esPersonal
                    bloqueadoPor={bloqueado ? tecnico?.nombre ?? "otro técnico" : null}
                    onEnviado={() => {
                      if (!ticket.tomado_en) cargar().then(recargar).catch(() => {});
                    }}
                  />
                </Card.Body>
              </Card>
            )}

            {tab === "Minutito" && (
              <Card className="anim-pestana">
                <Card.Body>
                  <ConversacionMinutito ticketId={id} nombre={cliente?.nombre} />
                </Card.Body>
              </Card>
            )}

            {tab === "Archivos" && (
              <Card className="anim-pestana">
                <Card.Body>
                  <ArchivosTicket ticketId={id} resuelto={resuelto || cancelado} />
                </Card.Body>
              </Card>
            )}

            {tab === "Historial" && (
              <Card className="anim-pestana">
                <Card.Body>
                  <ol className="relative ml-2 border-l border-linea">
                    {construirHistorial(cliente, interacciones, cambiosDeEstado, ticket.sla?.pausas, asignaciones).map((e, idx) => (
                      <li key={idx} className="mb-4 ml-4 last:mb-0">
                        <span className="absolute -left-[6px] mt-1.5 h-3 w-3 rounded-[3px] border-2 border-superficie bg-acento" />
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
