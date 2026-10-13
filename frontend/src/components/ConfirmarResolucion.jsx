import { useState } from "react";
import { confirmarResolucion } from "../api";
import Button from "./ui/Button";
import Spinner from "./ui/Spinner";

/**
 * Pregunta al usuario si la ayuda de Minutito resolvió su problema. Solo con su
 * confirmación el ticket cuenta como resuelto por Minutito.
 * `onDecision(resuelto, mensaje)` se llama cuando el servidor acepta la respuesta.
 */
export default function ConfirmarResolucion({ ticketId, onDecision, onError }) {
  const [enviando, setEnviando] = useState(null); // true | false mientras se envía

  async function decidir(resuelto) {
    setEnviando(resuelto);
    try {
      const r = await confirmarResolucion(ticketId, resuelto);
      onDecision(resuelto, r.mensaje, r.estado_ticket);
    } catch (e) {
      onError?.(e.message);
    } finally {
      setEnviando(null);
    }
  }

  return (
    <div className="rounded-lg border border-linea bg-white p-3">
      <div className="mb-2 text-sm font-medium text-noche">¿Se resolvió tu problema?</div>
      <div className="flex flex-wrap gap-2">
        <Button variant="dark" size="sm" disabled={enviando !== null} onClick={() => decidir(true)}>
          {enviando === true ? <Spinner size="sm" /> : "Sí, se resolvió"}
        </Button>
        <Button
          variant="outlineSecondary"
          size="sm"
          disabled={enviando !== null}
          onClick={() => decidir(false)}
        >
          {enviando === false ? <Spinner size="sm" /> : "No, necesito un técnico"}
        </Button>
      </div>
    </div>
  );
}
