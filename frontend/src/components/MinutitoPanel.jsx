import { Bot, CheckCircle2, Plus, Send, Ticket } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  borradorTicketMinutito,
  conversacionMinutitoActual,
  crearTicket,
  hablarConMinutito,
  nuevaConversacionMinutito,
  obtenerCatalogos,
  resolverConversacionMinutito,
  subirAdjunto,
} from "../api";
import { obtenerUsuario } from "../auth";
import Markdown from "./Markdown";
import SelectorArchivos from "./tickets/SelectorArchivos";
import { tituloTipo } from "./tickets/formato";
import Button from "./ui/Button";
import Spinner from "./ui/Spinner";
import { inputClass, labelClass } from "./ui/formStyles";

/** Borrador del ticket armado con la conversación: la persona lo revisa y lo envía. */
function BorradorTicket({ conversacionId, onCancelar }) {
  const navegar = useNavigate();
  const [catalogos, setCatalogos] = useState(null);
  const [texto, setTexto] = useState("");
  const [tipo, setTipo] = useState("");
  const [categoria, setCategoria] = useState("");
  const [sugerencia, setSugerencia] = useState(null);
  const [prioridad, setPrioridad] = useState("Normal");
  const [archivos, setArchivos] = useState([]);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([obtenerCatalogos(), borradorTicketMinutito(conversacionId)])
      .then(([c, b]) => {
        setCatalogos(c);
        setTexto(b.texto);
        setSugerencia(b.sugerencia);
        setTipo(b.sugerencia.tipo);
        setCategoria(b.sugerencia.confiable ? b.sugerencia.categoria : "");
      })
      .catch((e) => setError(e.message));
  }, [conversacionId]);

  if (!catalogos) {
    return (
      <div className="rounded-xl border border-linea bg-white p-3 text-sm text-gray-500">
        {error ? <span className="text-red-600">{error}</span> : <><Spinner size="sm" /> Preparando tu ticket con lo que conversamos…</>}
      </div>
    );
  }

  const tipoAccesos = catalogos.tipos[2]?.nombre; // «Gestión de usuarios y accesos» tiene su propio formulario
  const esAlta = tipo === tipoAccesos;

  async function enviar(e) {
    e.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      // Si queda la categoría que el clasificador asignó solo, se envía vacía (como en el
      // formulario): así no cuenta como confirmada por la persona.
      const automatica = sugerencia?.confiable && categoria === sugerencia.categoria;
      const ticket = await crearTicket({
        texto,
        tipo,
        categoria: automatica ? null : categoria || null,
        prioridad,
        conversacionId,
      });
      // Los archivos se suben ya con el ticket creado; si alguno falla, se avisa en el ticket.
      const avisos = [];
      for (const f of archivos) {
        try {
          await subirAdjunto(ticket.id, f);
        } catch (err) {
          avisos.push(`«${f.name}»: ${err.message}`);
        }
      }
      navegar(`/usuario/tickets/${ticket.id}`, { state: { creado: true, avisos } });
    } catch (err) {
      setError(err.message);
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={enviar} className="space-y-3 rounded-xl border border-acento/30 bg-acento-50/40 p-3 text-sm">
      <div className="font-semibold text-noche">Tu ticket para el equipo de sistemas</div>
      <p className="text-xs text-gray-600">Lo armé con nuestra conversación. Revísalo y cámbialo si hace falta.</p>
      {error && <p className="text-red-600">{error}</p>}
      <div>
        <label htmlFor="borrador-texto" className={labelClass}>
          Descripción
        </label>
        <textarea
          id="borrador-texto"
          rows={4}
          required
          minLength={5}
          maxLength={5000}
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          className={`${inputClass} resize-y`}
        />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label htmlFor="borrador-tipo" className={labelClass}>
            Tipo
          </label>
          <select id="borrador-tipo" value={tipo} onChange={(e) => setTipo(e.target.value)} className={inputClass}>
            {catalogos.tipos.map((t) => (
              <option key={t.nombre} value={t.nombre}>
                {tituloTipo(t.nombre)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="borrador-prioridad" className={labelClass}>
            Prioridad
          </label>
          <select id="borrador-prioridad" value={prioridad} onChange={(e) => setPrioridad(e.target.value)} className={inputClass}>
            {catalogos.prioridades.map((p) => (
              <option key={p}>{p}</option>
            ))}
          </select>
        </div>
      </div>
      {esAlta ? (
        <p className="rounded-lg bg-white p-2 text-gray-700">
          Las altas de colaboradores, accesos y permisos van en su propio formulario.{" "}
          <Link to="/usuario/nuevo-ticket" className="font-medium text-acento underline">
            Ir al formulario
          </Link>
        </p>
      ) : (
        <div>
          <label htmlFor="borrador-categoria" className={labelClass}>
            Categoría
          </label>
          {sugerencia?.confiable && categoria === sugerencia.categoria && (
            <p className="mb-1 text-xs text-emerald-700">
              Clasificada automáticamente ({Math.round(sugerencia.confianza * 100)}% de confianza).
            </p>
          )}
          <select
            id="borrador-categoria"
            required
            value={categoria}
            onChange={(e) => setCategoria(e.target.value)}
            className={inputClass}
          >
            <option value="">Elige una categoría…</option>
            {catalogos.categorias.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </div>
      )}
      {!esAlta && (
        <div>
          <span className={labelClass}>Adjuntar captura (opcional)</span>
          <SelectorArchivos archivos={archivos} onCambio={setArchivos} limites={catalogos.adjuntos} />
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" size="sm" variant="dark" disabled={enviando || esAlta}>
          {enviando ? <Spinner size="sm" /> : "Enviar ticket"}
        </Button>
        <Button type="button" size="sm" variant="outlineSecondary" onClick={onCancelar}>
          Seguir conversando
        </Button>
      </div>
    </form>
  );
}

function Burbuja({ rol, texto, escribiendo }) {
  if (rol === "usuario") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl rounded-br-md bg-noche px-3.5 py-2.5 text-sm text-white">
          {texto}
        </div>
      </div>
    );
  }
  return (
    <div className="max-w-[94%] break-words rounded-2xl rounded-tl-md border border-linea bg-white px-3.5 py-2.5 text-sm leading-relaxed text-gray-700">
      {texto ? <Markdown texto={texto} /> : null}
      {escribiendo && (
        <span className="inline-flex items-center gap-1.5 text-xs text-gray-400">
          <Spinner size="sm" /> {texto ? "" : "Minutito está pensando…"}
        </span>
      )}
    </div>
  );
}

/**
 * Chat con Minutito. Se conversa sin ticket; si se resuelve, la persona lo confirma; si no,
 * Minutito arma el ticket con la conversación para que el equipo lo atienda.
 */
export default function MinutitoPanel() {
  const usuario = obtenerUsuario();
  const [conversacion, setConversacion] = useState(null); // { id, mensajes: [{rol, texto}] }
  const [mensajes, setMensajes] = useState([]);
  const [texto, setTexto] = useState("");
  const [escribiendo, setEscribiendo] = useState(false);
  const [ofreceTicket, setOfreceTicket] = useState(false);
  const [creandoTicket, setCreandoTicket] = useState(false);
  const [resuelta, setResuelta] = useState(false);
  const [error, setError] = useState(null);
  const final = useRef(null);

  // Retoma la conversación abierta, si la hay (p. ej. al volver a la página).
  useEffect(() => {
    conversacionMinutitoActual()
      .then((c) => {
        if (c) {
          setConversacion(c);
          setMensajes(c.mensajes.map(({ rol, texto }) => ({ rol, texto })));
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    final.current?.scrollIntoView({ block: "nearest" });
  }, [mensajes, creandoTicket]);

  async function enviar(e) {
    e.preventDefault();
    const mensaje = texto.trim();
    if (!mensaje || escribiendo) return;
    setError(null);
    setTexto("");
    setOfreceTicket(false);
    setEscribiendo(true);
    setMensajes((m) => [...m, { rol: "usuario", texto: mensaje }, { rol: "minutito", texto: "" }]);
    const actualizar = (t) =>
      setMensajes((m) => [...m.slice(0, -1), { rol: "minutito", texto: t }]);
    try {
      const c = conversacion ?? (await nuevaConversacionMinutito());
      setConversacion(c);
      const r = await hablarConMinutito(c.id, mensaje, actualizar);
      actualizar(r.texto);
      setOfreceTicket(r.ofreceTicket);
    } catch (err) {
      setMensajes((m) => m.slice(0, -1)); // quita la burbuja vacía
      setError(err.message);
      setOfreceTicket(true); // sin Minutito, la salida es el ticket
    } finally {
      setEscribiendo(false);
    }
  }

  async function marcarResuelta() {
    setError(null);
    try {
      await resolverConversacionMinutito(conversacion.id);
      setResuelta(true);
    } catch (err) {
      setError(err.message);
    }
  }

  function empezarDeNuevo() {
    setConversacion(null);
    setMensajes([]);
    setResuelta(false);
    setOfreceTicket(false);
    setCreandoTicket(false);
    setError(null);
  }

  const hayRespuesta = mensajes.some((m) => m.rol === "minutito" && m.texto);
  const puedeActuar = conversacion && hayRespuesta && !escribiendo && !resuelta;

  return (
    <div className="flex h-full max-h-[calc(100dvh-7rem)] min-h-[28rem] flex-col rounded-xl border border-linea bg-white shadow-[0_1px_2px_rgba(16,27,48,0.04)]">
      <div className="flex items-center justify-between gap-3 border-b border-gray-100 p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-acento text-white">
            <Bot size={18} aria-hidden="true" />
          </div>
          <div>
            <div className="text-sm font-semibold text-noche">Minutito</div>
            <div className="text-xs text-gray-500">Asistente virtual de soporte</div>
          </div>
        </div>
        {mensajes.length > 0 && (
          <button
            type="button"
            onClick={empezarDeNuevo}
            disabled={escribiendo}
            className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-gray-500 hover:bg-marfil hover:text-noche"
          >
            <Plus size={14} /> Nueva conversación
          </button>
        )}
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-4" aria-live="polite">
        <div className="max-w-[94%] rounded-2xl rounded-tl-md bg-marfil px-3.5 py-2.5 text-sm text-gray-700">
          ¡Hola, {usuario?.nombre?.split(" ")[0]}! Soy Minutito. Cuéntame qué te pasa y lo resolvemos juntos. Si
          no lo logramos, te ayudo a crear el ticket para el equipo de sistemas.
        </div>
        {mensajes.map((m, i) => (
          <Burbuja key={i} rol={m.rol} texto={m.texto} escribiendo={escribiendo && i === mensajes.length - 1} />
        ))}

        {resuelta && (
          <div className="flex items-center gap-2 rounded-xl border border-green-200 bg-green-50 p-3 text-sm text-green-800">
            <CheckCircle2 size={16} /> ¡Qué bueno que se resolvió! Ganaste 10 puntos de autoservicio.
          </div>
        )}

        {creandoTicket && conversacion && (
          <BorradorTicket conversacionId={conversacion.id} onCancelar={() => setCreandoTicket(false)} />
        )}

        {puedeActuar && !creandoTicket && (
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <span className="w-full text-xs text-gray-500">¿Cómo vamos?</span>
            <Button size="sm" variant="outlineSuccess" onClick={marcarResuelta}>
              <CheckCircle2 size={14} /> Sí, se resolvió
            </Button>
            <Button size="sm" variant={ofreceTicket ? "dark" : "outlineSecondary"} onClick={() => setCreandoTicket(true)}>
              <Ticket size={14} /> Crear ticket con esta conversación
            </Button>
          </div>
        )}
        {error && (
          <div className="space-y-2 text-sm">
            <p className="text-red-600">{error}</p>
            {conversacion && !creandoTicket && (
              <Button size="sm" variant="dark" onClick={() => setCreandoTicket(true)}>
                <Ticket size={14} /> Crear ticket
              </Button>
            )}
          </div>
        )}
        <div ref={final} />
      </div>

      {!resuelta && !creandoTicket && (
        <form onSubmit={enviar} className="flex items-end gap-2 border-t border-gray-100 p-3">
          <label htmlFor="mensaje-minutito" className="sr-only">
            Mensaje para Minutito
          </label>
          <textarea
            id="mensaje-minutito"
            rows={1}
            maxLength={2000}
            className="max-h-32 min-w-0 flex-1 resize-none rounded-2xl border border-linea bg-marfil px-4 py-2 text-base transition-colors duration-150 focus:border-acento focus:bg-white focus:outline-none focus-visible:outline-none focus:ring-3 focus:ring-acento/25 sm:text-sm"
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                e.currentTarget.form.requestSubmit();
              }
            }}
            placeholder={mensajes.length ? "Escribe tu respuesta…" : "Escribe tu problema o pregunta…"}
            disabled={escribiendo}
          />
          <button
            type="submit"
            disabled={escribiendo || !texto.trim()}
            aria-label="Enviar mensaje"
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-acento text-white transition-colors duration-150 hover:bg-acento-600 disabled:bg-acento/40"
          >
            {escribiendo ? <Spinner size="sm" /> : <Send size={16} />}
          </button>
        </form>
      )}
      {resuelta && (
        <div className="border-t border-gray-100 p-3">
          <Button size="sm" variant="outlineSecondary" onClick={empezarDeNuevo}>
            <Plus size={14} /> Nueva conversación
          </Button>
        </div>
      )}
    </div>
  );
}
