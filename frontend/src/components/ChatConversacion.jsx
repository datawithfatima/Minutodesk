import Alert from "./ui/Alert";
import Badge from "./ui/Badge";
import Card from "./ui/Card";

export default function ChatConversacion({ interacciones }) {
  if (interacciones.length === 0) {
    return <Alert variant="secondary">Todavía no hay mensajes en este ticket.</Alert>;
  }

  return (
    <div className="flex flex-col gap-3">
      {interacciones.map((i) => (
        <div key={i.id}>
          <div className="mb-1 flex justify-end">
            <Card className="max-w-[75%] border-blue-600 bg-blue-600 text-white">
              <Card.Body className="py-2">{i.mensaje_cliente}</Card.Body>
            </Card>
          </div>
          <div className="flex justify-start">
            <Card className="max-w-[75%] bg-gray-50">
              <Card.Body className="py-2">
                {i.respuesta_minutito}
                {i.marco_resuelto && (
                  <div className="mt-1">
                    <Badge color="green">Marcó como resuelto</Badge>
                  </div>
                )}
              </Card.Body>
            </Card>
          </div>
        </div>
      ))}
    </div>
  );
}
