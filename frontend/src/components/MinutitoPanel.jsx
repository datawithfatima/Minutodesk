import { Bot, Send, X } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { crearTicket, enviarMensajeChat } from "../api";
import { obtenerUsuario } from "../auth";
import ConfirmarResolucion from "./ConfirmarResolucion";
import Spinner from "./ui/Spinner";

export default function MinutitoPanel({ onCerrar }) {
  const usuario = obtenerUsuario();
  const [mensaje, setMensaje] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);
  // { mensaje, respuesta, ticketId, pideConfirmacion }
  const [resultado, setResultado] = useState(null);
  // Respuesta del usuario a "¿se resolvió?": { mensaje }
  const [decision, setDecision] = useState(null);
  const navegar = useNavigate();

  async function manejarEnvio(e) {
    e.preventDefault();
    setEnviando(true);
    setError(null);
    let ticket = null;
    try {
      ticket = await crearTicket({ texto: mensaje });
      const respuesta = await enviarMensajeChat(ticket.id, mensaje);
      setResultado({
        mensaje,
        respuesta: respuesta.respuesta,
        ticketId: ticket.id,
        pideConfirmacion: respuesta.requiere_confirmacion,
      });
    } catch (e) {
      // Si el ticket ya se creó, no se pide reintentar (duplicaría el ticket): se muestra
      // el aviso como respuesta y el ticket queda para un técnico.
      if (ticket) {
        setResultado({ mensaje, respuesta: e.message, ticketId: ticket.id, pideConfirmacion: false });
      } else {
        setError(e.message);
      }
    } finally {
      setEnviando(false);
    }
  }

  const verTicket = () => navegar(`/usuario/tickets/${resultado.ticketId}`);

  return (
    <div className="flex h-full flex-col rounded-xl border border-linea bg-white shadow-[0_1px_2px_rgba(16,27,48,0.04)]">
      <div className="flex items-center justify-between border-b border-gray-100 p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-acento text-white">
            <Bot size={18} aria-hidden="true" />
          </div>
          <div>
            <div className="text-sm font-semibold text-noche">Minutito</div>
            <div className="text-xs text-gray-500">Asistente virtual de MinutoDesk</div>
          </div>
        </div>
        {onCerrar && (
          <button onClick={onCerrar} aria-label="Cerrar" className="rounded-lg p-1 text-gray-400 hover:bg-marfil hover:text-gray-600">
            <X size={18} />
          </button>
        )}
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        <div className="max-w-[92%] rounded-2xl rounded-tl-md bg-marfil px-3.5 py-2.5 text-sm text-gray-700">
          ¡Hola, {usuario?.nombre?.split(" ")[0]}! Soy Minutito. Cuéntame qué te pasa y lo
          vemos juntos; si no logro resolverlo, dejo tu ticket listo para el equipo.
        </div>

        {resultado && (
          <>
            <div className="flex justify-end">
              <div className="max-w-[85%] break-words rounded-2xl rounded-br-md bg-noche px-3.5 py-2.5 text-sm text-white">
                {resultado.mensaje}
              </div>
            </div>
            <div className="max-w-[92%] whitespace-pre-wrap rounded-2xl rounded-tl-md border border-linea bg-white px-3.5 py-2.5 text-sm text-gray-700">
              {resultado.respuesta}
            </div>

            {resultado.pideConfirmacion && !decision && (
              <ConfirmarResolucion
                ticketId={resultado.ticketId}
                onDecision={(_resuelto, texto) => setDecision({ mensaje: texto })}
                onError={setError}
              />
            )}

            {(decision || !resultado.pideConfirmacion) && (
              <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-linea bg-white p-3 text-sm text-gray-700">
                <span>{decision?.mensaje ?? "Tu ticket quedó registrado."}</span>
                <button
                  onClick={verTicket}
                  className="shrink-0 font-medium text-acento hover:underline"
                >
                  Ver mi ticket
                </button>
              </div>
            )}
          </>
        )}

        {error && <div className="text-sm text-red-600">{error}</div>}
      </div>

      {!resultado && (
        <form onSubmit={manejarEnvio} className="flex items-center gap-2 border-t border-gray-100 p-3">
          <input
            aria-label="Mensaje para Minutito"
            className="min-w-0 flex-1 rounded-full border border-linea bg-marfil px-4 py-2 text-base transition-colors duration-150 focus:border-acento focus:bg-white focus:outline-none focus-visible:outline-none focus:ring-3 focus:ring-acento/25 sm:text-sm"
            value={mensaje}
            onChange={(e) => setMensaje(e.target.value)}
            placeholder="Escribe tu mensaje..."
            required
            disabled={enviando}
          />
          <button
            type="submit"
            disabled={enviando}
            aria-label="Enviar mensaje"
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-acento text-white transition-colors duration-150 hover:bg-acento-600 disabled:bg-acento/40"
          >
            {enviando ? <Spinner size="sm" /> : <Send size={16} />}
          </button>
        </form>
      )}
    </div>
  );
}
