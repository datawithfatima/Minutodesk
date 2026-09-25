import { Bot, Send, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { crearTicket, enviarMensajeChat } from "../api";
import { obtenerUsuario } from "../auth";
import Spinner from "./ui/Spinner";

const SEGUNDOS_ANTES_DE_REDIRIGIR = 3;

export default function MinutitoPanel({ onCerrar }) {
  const usuario = obtenerUsuario();
  const [mensaje, setMensaje] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);
  const [resultado, setResultado] = useState(null); // { mensaje, respuesta, ticketId }
  const [cuenta, setCuenta] = useState(SEGUNDOS_ANTES_DE_REDIRIGIR);
  const navegar = useNavigate();

  useEffect(() => {
    if (!resultado) return;
    if (cuenta <= 0) {
      navegar(`/usuario/tickets/${resultado.ticketId}`);
      return;
    }
    const temporizador = setTimeout(() => setCuenta((c) => c - 1), 1000);
    return () => clearTimeout(temporizador);
  }, [resultado, cuenta, navegar]);

  async function manejarEnvio(e) {
    e.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      const ticket = await crearTicket({ texto: mensaje });
      const respuesta = await enviarMensajeChat(ticket.id, mensaje);
      setResultado({ mensaje, respuesta: respuesta.respuesta, ticketId: ticket.id });
    } catch (e) {
      setError(e.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="flex h-full flex-col rounded-lg border border-gray-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-gray-100 p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gray-900 text-white">
            <Bot size={18} />
          </div>
          <div>
            <div className="text-sm font-semibold text-gray-900">Minutito</div>
            <div className="text-xs text-gray-400">Asistente virtual de MinutoDesk</div>
          </div>
        </div>
        {onCerrar && (
          <button onClick={onCerrar} className="text-gray-400 hover:text-gray-600">
            <X size={18} />
          </button>
        )}
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        <div className="rounded-lg bg-gray-50 p-3 text-sm text-gray-700">
          ¡Hola {usuario?.nombre?.split(" ")[0]}! 👋 Soy Minutito, tu asistente virtual.
          Cuéntame qué necesitas — si puedo resolverlo te ayudo al instante, y si no, dejo
          tu ticket listo para que lo tome un técnico.
        </div>

        {resultado && (
          <>
            <div className="flex justify-end">
              <div className="max-w-[85%] rounded-lg bg-gray-900 px-3 py-2 text-sm text-white">
                {resultado.mensaje}
              </div>
            </div>
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 text-sm text-gray-700">
              {resultado.respuesta}
            </div>
            <div className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-2 text-xs text-gray-500">
              <span>Abriendo tu ticket en {cuenta}s...</span>
              <button
                onClick={() => navegar(`/usuario/tickets/${resultado.ticketId}`)}
                className="font-medium text-gray-900 hover:underline"
              >
                Ver ahora
              </button>
            </div>
          </>
        )}

        {error && <div className="text-sm text-red-600">{error}</div>}
      </div>

      {!resultado && (
        <form onSubmit={manejarEnvio} className="flex items-center gap-2 border-t border-gray-100 p-3">
          <input
            className="flex-1 rounded-full border border-gray-300 px-4 py-2 text-sm focus:border-gray-500 focus:outline-none"
            value={mensaje}
            onChange={(e) => setMensaje(e.target.value)}
            placeholder="Escribe tu mensaje..."
            required
            disabled={enviando}
          />
          <button
            type="submit"
            disabled={enviando}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gray-900 text-white hover:bg-gray-800 disabled:bg-gray-400"
          >
            {enviando ? <Spinner size="sm" /> : <Send size={16} />}
          </button>
        </form>
      )}
    </div>
  );
}
