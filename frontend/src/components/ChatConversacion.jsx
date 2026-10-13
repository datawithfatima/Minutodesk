import { Bot } from "lucide-react";
import Alert from "./ui/Alert";
import Badge from "./ui/Badge";

export default function ChatConversacion({ interacciones }) {
  if (interacciones.length === 0) {
    return <Alert variant="secondary">Todavía no hay mensajes en este ticket.</Alert>;
  }

  return (
    <div className="flex flex-col gap-4">
      {interacciones.map((i) => (
        <div key={i.id} className="space-y-2">
          <div className="flex justify-end">
            <div className="max-w-[90%] whitespace-pre-line break-words rounded-2xl rounded-br-md bg-noche px-3.5 py-2.5 text-sm text-white sm:max-w-[75%]">
              {i.mensaje_cliente}
            </div>
          </div>
          <div className="flex items-start gap-2">
            <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-acento-50 text-acento ring-1 ring-acento-100">
              <Bot size={14} aria-hidden="true" />
            </span>
            <div className="max-w-[85%] whitespace-pre-line break-words rounded-2xl rounded-tl-md border border-linea bg-white px-3.5 py-2.5 text-sm text-gray-700 sm:max-w-[75%]">
              {i.respuesta_minutito}
              {i.marco_resuelto && (
                <div className="mt-2">
                  <Badge color="green">El usuario confirmó que se resolvió</Badge>
                </div>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
