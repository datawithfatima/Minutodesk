import { ClipboardCheck, Send } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  enviarMensajeSoporte,
  listarClientes,
  obtenerConversacion,
  solicitarAprobacion,
} from "../../api";
import { obtenerUsuario } from "../../auth";
import Alert from "../ui/Alert";
import Badge from "../ui/Badge";
import Button from "../ui/Button";
import Spinner from "../ui/Spinner";
import { inputClass, labelClass } from "../ui/formStyles";

// Cada cuánto se buscan mensajes nuevos mientras la pantalla está abierta.
const INTERVALO_MS = 15000;

const ESTADO_APROBACION = {
  pendiente: { texto: "Pendiente", color: "amber" },
  aprobada: { texto: "Aprobada", color: "green" },
  rechazada: { texto: "Rechazada", color: "gray" },
};

function fecha(valor) {
  return new Date(valor).toLocaleString([], { dateStyle: "short", timeStyle: "short" });
}

function Mensaje({ m, propio }) {
  return (
    <div className={`flex ${propio ? "justify-end" : "justify-start"}`}>
      <div className="max-w-[90%] sm:max-w-[75%]">
        <div className={`mb-0.5 text-[11px] text-gray-400 ${propio ? "text-right" : ""}`}>
          {propio ? "Tú" : m.autor}
          {!propio && m.autor_es_personal && " · Soporte"} · {fecha(m.creado_en)}
        </div>
        <div
          className={`whitespace-pre-line break-words rounded-2xl px-3.5 py-2.5 text-sm ${
            propio
              ? "rounded-br-md bg-noche text-white"
              : "rounded-tl-md border border-linea bg-white text-gray-700"
          }`}
        >
          {m.texto}
        </div>
      </div>
    </div>
  );
}

function PasoAprobacion({ a }) {
  const estado = ESTADO_APROBACION[a.estado] ?? ESTADO_APROBACION.pendiente;
  return (
    <div className="rounded-xl border border-dashed border-linea bg-marfil/60 px-4 py-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="flex items-center gap-2 font-medium text-noche">
          <ClipboardCheck size={15} aria-hidden="true" className="text-acento" />
          Aprobación de {a.aprobador}
        </span>
        <Badge color={estado.color}>{estado.texto}</Badge>
      </div>
      <p className="mt-1.5 whitespace-pre-line break-words text-gray-700">{a.descripcion}</p>
      <p className="mt-1 text-[11px] text-gray-400">
        Pedida por {a.solicitada_por} · {fecha(a.creado_en)}
        {a.respondida_en && ` · Respondida ${fecha(a.respondida_en)}`}
      </p>
      {a.comentario && (
        <p className="mt-1.5 text-gray-600">
          <span className="font-medium">Comentario:</span> {a.comentario}
        </p>
      )}
    </div>
  );
}

function FormAprobacion({ ticket, onCreada, onCancelar }) {
  const yo = obtenerUsuario();
  const [personas, setPersonas] = useState(null);
  const [aprobadorId, setAprobadorId] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    listarClientes()
      .then((lista) =>
        setPersonas(lista.filter((c) => c.activo && !c.pendiente_activacion && c.id !== yo.id && c.id !== ticket.cliente_id))
      )
      .catch((e) => setError(e.message));
  }, [ticket.cliente_id, yo.id]);

  async function enviar(e) {
    e.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      await solicitarAprobacion(ticket.id, { aprobadorId: Number(aprobadorId), descripcion });
      onCreada();
    } catch (e) {
      setError(e.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={enviar} className="space-y-3 rounded-xl border border-linea bg-white p-4">
      <h3 className="text-sm font-semibold text-noche">Solicitar aprobación</h3>
      {error && <Alert variant="danger">{error}</Alert>}
      <div>
        <label htmlFor="aprobador" className={labelClass}>
          ¿Quién debe aprobar?
        </label>
        {personas === null ? (
          <Spinner size="sm" />
        ) : (
          <select
            id="aprobador"
            required
            value={aprobadorId}
            onChange={(e) => setAprobadorId(e.target.value)}
            className={inputClass}
          >
            <option value="">Elige a una persona (p. ej. su jefe)</option>
            {personas.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nombre} · {p.area}
              </option>
            ))}
          </select>
        )}
      </div>
      <div>
        <label htmlFor="descripcion-aprobacion" className={labelClass}>
          ¿Qué hay que aprobar?
        </label>
        <textarea
          id="descripcion-aprobacion"
          rows={3}
          required
          minLength={5}
          maxLength={1000}
          value={descripcion}
          onChange={(e) => setDescripcion(e.target.value)}
          placeholder="Ej.: Aprobar la licencia de Power BI para este colaborador."
          className={`${inputClass} resize-y`}
        />
        <p className="mt-1 text-xs text-gray-500">
          Le llegará un aviso por correo. El ticket no se podrá resolver hasta que responda.
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button type="submit" size="sm" variant="dark" disabled={enviando || !aprobadorId}>
          {enviando ? <Spinner size="sm" /> : "Enviar solicitud"}
        </Button>
        <Button type="button" size="sm" variant="outlineSecondary" onClick={onCancelar}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}

/**
 * Chat del ticket entre la persona que lo abrió y el equipo de soporte, con los pasos de
 * aprobación intercalados por fecha. El personal además puede pedir aprobaciones.
 */
export default function ConversacionTicket({ ticket, esPersonal = false }) {
  const yo = obtenerUsuario();
  const [datos, setDatos] = useState(null);
  const [texto, setTexto] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);
  const [pidiendo, setPidiendo] = useState(false);
  const final = useRef(null);
  const cerrado = ticket.estado === "resuelto" || ticket.estado === "cancelado";

  const cargar = useCallback(
    () => obtenerConversacion(ticket.id).then(setDatos),
    [ticket.id]
  );

  useEffect(() => {
    cargar().catch((e) => setError(e.message));
    const intervalo = setInterval(() => cargar().catch(() => {}), INTERVALO_MS);
    return () => clearInterval(intervalo);
  }, [cargar]);

  const cantidad = datos ? datos.mensajes.length + datos.aprobaciones.length : 0;
  useEffect(() => {
    if (cantidad) final.current?.scrollIntoView({ block: "nearest" });
  }, [cantidad]);

  async function enviar(e) {
    e.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      await enviarMensajeSoporte(ticket.id, texto);
      setTexto("");
      await cargar();
    } catch (e) {
      setError(e.message);
    } finally {
      setEnviando(false);
    }
  }

  if (!datos) return error ? <Alert variant="danger">{error}</Alert> : <Spinner size="sm" />;

  const linea = [
    ...datos.mensajes.map((m) => ({ tipo: "mensaje", fecha: m.creado_en, clave: `m${m.id}`, m })),
    ...datos.aprobaciones.map((a) => ({ tipo: "aprobacion", fecha: a.creado_en, clave: `a${a.id}`, a })),
  ].sort((x, y) => new Date(x.fecha) - new Date(y.fecha));

  return (
    <div className="space-y-3">
      {linea.length === 0 ? (
        <Alert variant="secondary">
          {esPersonal
            ? "Todavía no hay mensajes. Escríbele al usuario para pedirle datos o contarle cómo avanza."
            : "Aquí puedes conversar con el técnico que atiende tu ticket."}
        </Alert>
      ) : (
        <div className="flex max-h-[28rem] flex-col gap-3 overflow-y-auto pr-1">
          {linea.map((item) =>
            item.tipo === "mensaje" ? (
              <Mensaje key={item.clave} m={item.m} propio={item.m.autor_id === yo?.id} />
            ) : (
              <PasoAprobacion key={item.clave} a={item.a} />
            )
          )}
          <div ref={final} />
        </div>
      )}

      {error && <Alert variant="danger">{error}</Alert>}

      {cerrado ? (
        <p className="text-sm text-gray-500">El ticket está cerrado: el chat queda solo para consulta.</p>
      ) : (
        <>
          <form onSubmit={enviar} className="flex items-end gap-2">
            <label htmlFor={`mensaje-${ticket.id}`} className="sr-only">
              Mensaje
            </label>
            <textarea
              id={`mensaje-${ticket.id}`}
              rows={2}
              maxLength={2000}
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey && texto.trim()) {
                  e.preventDefault();
                  e.currentTarget.form.requestSubmit();
                }
              }}
              placeholder={esPersonal ? "Escribe al usuario..." : "Escribe al equipo de soporte..."}
              className={`${inputClass} resize-y`}
            />
            <Button type="submit" disabled={enviando || !texto.trim()} aria-label="Enviar mensaje">
              {enviando ? <Spinner size="sm" /> : <Send size={16} />}
            </Button>
          </form>
          {esPersonal &&
            (pidiendo ? (
              <FormAprobacion
                ticket={ticket}
                onCancelar={() => setPidiendo(false)}
                onCreada={() => {
                  setPidiendo(false);
                  cargar().catch((e) => setError(e.message));
                }}
              />
            ) : (
              <Button variant="outlinePrimary" size="sm" onClick={() => setPidiendo(true)}>
                <ClipboardCheck size={15} /> Solicitar aprobación
              </Button>
            ))}
        </>
      )}
    </div>
  );
}
