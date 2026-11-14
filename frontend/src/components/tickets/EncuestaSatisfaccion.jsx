import { ClipboardCheck, Star } from "lucide-react";
import { useEffect, useState } from "react";
import { obtenerEncuesta, responderEncuesta } from "../../api";
import Alert from "../ui/Alert";
import Button from "../ui/Button";

/*
 * Encuesta de satisfacción como «acta de recepción de obra»: cuando el ticket queda
 * resuelto, quien lo abrió califica la atención de 1 a 5 estrellas con un comentario
 * opcional. El personal la ve en modo lectura (`editable` falso).
 */

const RESPUESTAS = {
  1: "Muy insatisfecho",
  2: "Insatisfecho",
  3: "Aceptable",
  4: "Satisfecho",
  5: "Muy satisfecho",
};

export function Estrellas({ valor, tamano = 16, className = "" }) {
  return (
    <span className={`inline-flex items-center gap-0.5 ${className}`} aria-label={`${valor} de 5 estrellas`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <Star
          key={n}
          size={tamano}
          aria-hidden="true"
          className={n <= valor ? "fill-casco text-casco" : "text-gray-300"}
          strokeWidth={1.75}
        />
      ))}
    </span>
  );
}

function SelectorEstrellas({ valor, onCambiar }) {
  const [sobre, setSobre] = useState(0);
  const mostrado = sobre || valor;
  return (
    <div>
      <div role="radiogroup" aria-label="Calificación de la atención" className="flex items-center gap-1" onMouseLeave={() => setSobre(0)}>
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            role="radio"
            aria-checked={valor === n}
            aria-label={`${n} ${n === 1 ? "estrella" : "estrellas"}: ${RESPUESTAS[n]}`}
            onMouseEnter={() => setSobre(n)}
            onFocus={() => setSobre(n)}
            onBlur={() => setSobre(0)}
            onClick={() => onCambiar(n)}
            className="btn-obra rounded-md p-1 transition-transform duration-150 hover:-translate-y-0.5 focus-visible:outline-2 focus-visible:outline-acento"
          >
            <Star
              size={30}
              strokeWidth={1.6}
              aria-hidden="true"
              className={`transition-colors duration-150 ${
                n <= mostrado ? "fill-casco text-casco drop-shadow-[0_1px_0_rgb(0_0_0/0.25)]" : "text-gray-300"
              }`}
            />
          </button>
        ))}
      </div>
      <p className="mt-1 h-5 font-mono text-[11px] uppercase tracking-[0.12em] text-gray-500" aria-live="polite">
        {mostrado ? RESPUESTAS[mostrado] : "Toca una estrella"}
      </p>
    </div>
  );
}

export default function EncuestaSatisfaccion({ ticketId, editable = true }) {
  const [encuesta, setEncuesta] = useState(undefined); // undefined = cargando, null = sin responder
  const [estrellas, setEstrellas] = useState(0);
  const [comentario, setComentario] = useState("");
  const [editando, setEditando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);
  const [recienEnviada, setRecienEnviada] = useState(false);

  useEffect(() => {
    obtenerEncuesta(ticketId)
      .then((e) => {
        setEncuesta(e);
        if (e) {
          setEstrellas(e.estrellas);
          setComentario(e.comentario || "");
        }
      })
      .catch(() => setEncuesta(null));
  }, [ticketId]);

  if (encuesta === undefined) return null;
  if (!editable && !encuesta) {
    return <p className="text-sm text-gray-500">El usuario todavía no calificó la atención.</p>;
  }

  async function enviar(e) {
    e.preventDefault();
    if (!estrellas) {
      setError("Elige de 1 a 5 estrellas.");
      return;
    }
    setEnviando(true);
    setError(null);
    try {
      const guardada = await responderEncuesta(ticketId, { estrellas, comentario });
      setEncuesta(guardada);
      setEditando(false);
      setRecienEnviada(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setEnviando(false);
    }
  }

  // Ya calificada: se muestra el acta firmada (y, para quien la llenó, la opción de cambiarla).
  if (encuesta && !editando) {
    return (
      <div className="relative">
        {recienEnviada && (
          <span
            aria-hidden="true"
            className="anim-sello absolute -top-1 right-0 rotate-[-8deg] rounded-[3px] border-2 border-acento px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-acento"
          >
            Recibido
          </span>
        )}
        <div className="flex items-center gap-3">
          <Estrellas valor={encuesta.estrellas} tamano={22} />
          <span className="font-mono text-xs text-gray-500">{RESPUESTAS[encuesta.estrellas]}</span>
        </div>
        {encuesta.comentario && (
          <blockquote className="mt-3 border-l-2 border-casco pl-3 text-sm italic leading-relaxed text-gray-700">
            «{encuesta.comentario}»
          </blockquote>
        )}
        <p className="mt-3 text-xs text-gray-500">
          {editable ? "Gracias por calificar la atención" : "Calificado"} el{" "}
          {new Date(encuesta.actualizado_en || encuesta.creado_en).toLocaleDateString("es-EC")}.
        </p>
        {editable && (
          <button
            type="button"
            onClick={() => {
              setEditando(true);
              setRecienEnviada(false);
            }}
            className="mt-2 text-xs font-semibold text-acento hover:underline"
          >
            Cambiar mi calificación
          </button>
        )}
      </div>
    );
  }

  return (
    <form onSubmit={enviar}>
      <div className="mb-3 flex items-start gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-grafito text-casco">
          <ClipboardCheck size={18} aria-hidden="true" />
        </span>
        <div>
          <p className="font-semibold text-noche">¿Cómo te atendimos?</p>
          <p className="text-sm text-gray-600">Firma el acta de recepción: tu opinión ayuda al equipo a mejorar.</p>
        </div>
      </div>
      <SelectorEstrellas valor={estrellas} onCambiar={setEstrellas} />
      <label className="mt-3 block">
        <span className="mb-1 block text-xs text-gray-500">Comentario (opcional)</span>
        <textarea
          value={comentario}
          onChange={(e) => setComentario(e.target.value)}
          maxLength={1000}
          rows={3}
          placeholder="¿Qué hicimos bien o qué podemos mejorar?"
          className="campo-obra w-full rounded-md border border-linea bg-superficie px-3 py-2 text-sm text-noche placeholder:text-gray-400"
        />
      </label>
      {error && (
        <Alert variant="danger" className="mt-2">
          {error}
        </Alert>
      )}
      <div className="mt-3 flex flex-wrap gap-2">
        <Button type="submit" size="sm" disabled={enviando || !estrellas}>
          {enviando ? "Enviando…" : "Enviar calificación"}
        </Button>
        {editando && (
          <Button type="button" size="sm" variant="outlineSecondary" onClick={() => setEditando(false)}>
            Cancelar
          </Button>
        )}
      </div>
    </form>
  );
}
