import { CheckCircle2, Clock3, RotateCcw, ThumbsDown, ThumbsUp } from "lucide-react";
import { useEffect, useState } from "react";
import { obtenerConfirmacionCierre, responderConfirmacionCierre } from "../../api";
import Button from "../ui/Button";
import Spinner from "../ui/Spinner";
import { inputClass } from "../ui/formStyles";

/*
 * «¿Quedó resuelto?»: cuando un técnico marca resuelto el ticket, quien lo abrió confirma
 * o dice que no (el ticket vuelve al mismo técnico). Si no contesta, se confirma solo al
 * vencer la ventana. El personal ve el resultado en modo lectura (`editable` falso).
 */

const RESULTADO = {
  confirmado: { Icono: CheckCircle2, cls: "text-green-700", texto: "El usuario confirmó que quedó resuelto." },
  automatico: { Icono: Clock3, cls: "text-gray-600", texto: "Se dio por resuelto solo: el usuario no respondió a tiempo." },
  rechazado: { Icono: RotateCcw, cls: "text-acento", texto: "El usuario dijo que no quedó resuelto y el ticket se reabrió." },
};

function fecha(valor) {
  return new Date(valor).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}

export default function ConfirmacionCierre({ ticketId, editable = true, onCambio, className = "" }) {
  const [confirmacion, setConfirmacion] = useState(undefined); // undefined = cargando
  const [diciendoQueNo, setDiciendoQueNo] = useState(false);
  const [comentario, setComentario] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let vigente = true;
    obtenerConfirmacionCierre(ticketId)
      .then((c) => vigente && setConfirmacion(c))
      .catch(() => vigente && setConfirmacion(null));
    return () => {
      vigente = false;
    };
  }, [ticketId]);

  async function responder(quedoResuelto) {
    setEnviando(true);
    setError(null);
    try {
      const c = await responderConfirmacionCierre(ticketId, { quedoResuelto, comentario });
      setConfirmacion(c);
      setDiciendoQueNo(false);
      await onCambio?.(c);
    } catch (e) {
      setError(e.message);
    } finally {
      setEnviando(false);
    }
  }

  if (confirmacion === undefined) return <Spinner size="sm" />;
  if (confirmacion === null || confirmacion.respuesta === "anulado") return null;

  if (confirmacion.respuesta !== "pendiente") {
    const r = RESULTADO[confirmacion.respuesta];
    if (!r) return null;
    return (
      <div className={`flex items-start gap-2 text-sm ${className}`}>
        <r.Icono size={16} aria-hidden="true" className={`mt-0.5 shrink-0 ${r.cls}`} />
        <div>
          <p className="text-gray-700">{r.texto}</p>
          {confirmacion.comentario && <p className="mt-1 text-[13px] italic text-gray-500">«{confirmacion.comentario}»</p>}
          {confirmacion.respondido_en && (
            <p className="mt-0.5 font-mono text-[10.5px] text-gray-400">{fecha(confirmacion.respondido_en)}</p>
          )}
        </div>
      </div>
    );
  }

  if (!editable || !confirmacion.puede_responder) {
    return (
      <p className={`flex items-start gap-2 text-sm text-gray-600 ${className}`}>
        <Clock3 size={16} aria-hidden="true" className="mt-0.5 shrink-0 text-amber-700" />
        <span>
          Esperando que el usuario confirme. Si no responde, se dará por resuelto el{" "}
          <strong className="font-semibold text-noche">{fecha(confirmacion.vence_en)}</strong>
        </span>
      </p>
    );
  }

  return (
    <div className={`space-y-3 text-sm ${className}`}>
      <div>
        <p className="text-[15px] font-semibold text-noche">¿Quedó resuelto tu problema?</p>
        <p className="mt-0.5 text-gray-600">
          El técnico marcó el ticket como resuelto. Si no nos respondes, lo daremos por resuelto el{" "}
          <strong className="font-semibold text-noche">{fecha(confirmacion.vence_en)}</strong>
        </p>
      </div>

      {!diciendoQueNo ? (
        <div className="flex flex-wrap gap-2">
          <Button variant="dark" size="sm" disabled={enviando} onClick={() => responder(true)}>
            {enviando ? <Spinner size="sm" /> : <ThumbsUp size={15} aria-hidden="true" />} Sí, quedó resuelto
          </Button>
          <Button variant="outlineSecondary" size="sm" disabled={enviando} onClick={() => setDiciendoQueNo(true)}>
            <ThumbsDown size={15} aria-hidden="true" /> No, sigue fallando
          </Button>
        </div>
      ) : (
        <form
          className="space-y-2"
          onSubmit={(e) => {
            e.preventDefault();
            responder(false);
          }}
        >
          <label htmlFor={`no-resuelto-${ticketId}`} className="block text-xs font-medium text-gray-700">
            Cuéntale al técnico qué sigue fallando. El ticket vuelve a él, sin que tengas que crear otro.
          </label>
          <textarea
            id={`no-resuelto-${ticketId}`}
            rows={3}
            required
            minLength={5}
            maxLength={1000}
            value={comentario}
            onChange={(e) => setComentario(e.target.value)}
            className={`${inputClass} resize-y`}
            placeholder="Por ejemplo: el reporte abre, pero sigue sin mostrar las ventas de octubre."
          />
          <div className="flex flex-wrap gap-2">
            <Button type="submit" variant="primary" size="sm" disabled={enviando || comentario.trim().length < 5}>
              {enviando ? <Spinner size="sm" /> : <RotateCcw size={15} aria-hidden="true" />} Reabrir con el mismo técnico
            </Button>
            <Button type="button" variant="outlineSecondary" size="sm" disabled={enviando} onClick={() => setDiciendoQueNo(false)}>
              Volver
            </Button>
          </div>
        </form>
      )}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}
