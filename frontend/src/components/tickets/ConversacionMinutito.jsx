import { Bot } from "lucide-react";
import { useEffect, useState } from "react";
import { conversacionMinutitoDeTicket, listarInteracciones } from "../../api";
import ChatConversacion from "../ChatConversacion";
import Markdown from "../Markdown";
import Alert from "../ui/Alert";
import Spinner from "../ui/Spinner";

/**
 * Lo que la persona conversó con Minutito antes de crear el ticket (solo lectura).
 * Los tickets anteriores a este flujo tienen la conversación guardada como interacciones.
 */
export default function ConversacionMinutito({ ticketId, nombre = "El usuario" }) {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([conversacionMinutitoDeTicket(ticketId), listarInteracciones(ticketId)])
      .then(([conversacion, interacciones]) => setDatos({ conversacion, interacciones }))
      .catch((e) => setError(e.message));
  }, [ticketId]);

  if (error) return <Alert variant="danger">{error}</Alert>;
  if (!datos) return <Spinner size="sm" />;
  if (!datos.conversacion) {
    return datos.interacciones.length ? (
      <ChatConversacion interacciones={datos.interacciones} />
    ) : (
      <Alert variant="secondary">Este ticket se creó sin conversar con Minutito.</Alert>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {datos.conversacion.mensajes.map((m) =>
        m.rol === "usuario" ? (
          <div key={m.id} className="flex justify-end">
            <div className="max-w-[90%] sm:max-w-[75%]">
              <div className="mb-0.5 text-right text-[11px] text-gray-400">{nombre}</div>
              <div className="whitespace-pre-line anim-colocar break-words rounded-2xl rounded-br-md bg-noche px-3.5 py-2.5 text-sm text-white">
                {m.texto}
              </div>
            </div>
          </div>
        ) : (
          <div key={m.id} className="flex items-start gap-2">
            <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-acento-50 text-acento ring-1 ring-acento-100">
              <Bot size={14} aria-hidden="true" />
            </span>
            <div className="max-w-[85%] anim-colocar break-words rounded-2xl rounded-tl-md border border-linea bg-white px-3.5 py-2.5 text-sm text-gray-700 sm:max-w-[75%]">
              <Markdown texto={m.texto} />
            </div>
          </div>
        )
      )}
    </div>
  );
}
