import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { enviarMensajeChat, listarInteracciones, obtenerTicket } from "../../api";
import Alert from "../../components/ui/Alert";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Card from "../../components/ui/Card";
import Spinner from "../../components/ui/Spinner";
import { inputClass } from "../../components/ui/formStyles";
import EstadoBadge from "../../components/EstadoBadge";
import ChatConversacion from "../../components/ChatConversacion";

export default function TicketDetailPage() {
  const { id } = useParams();
  const [ticket, setTicket] = useState(null);
  const [interacciones, setInteracciones] = useState([]);
  const [mensaje, setMensaje] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  const cargar = useCallback(async () => {
    const [t, ints] = await Promise.all([obtenerTicket(id), listarInteracciones(id)]);
    setTicket(t);
    setInteracciones(ints);
  }, [id]);

  useEffect(() => {
    cargar().catch((e) => setError(e.message));
  }, [cargar]);

  async function manejarEnvio(e) {
    e.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      await enviarMensajeChat(id, mensaje);
      setMensaje("");
      await cargar();
    } catch (e) {
      setError(e.message);
    } finally {
      setEnviando(false);
    }
  }

  if (error && !ticket) return <Alert variant="danger">{error}</Alert>;
  if (!ticket) return <Spinner size="sm" />;

  const resuelto = ticket.estado === "resuelto";

  return (
    <>
      <div className="mb-3 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Ticket #{ticket.id}</h1>
        <EstadoBadge estado={ticket.estado} />
      </div>

      {error && (
        <Alert variant="danger" className="mb-3">
          {error}
        </Alert>
      )}

      <Card className="mb-4">
        <Card.Body>
          <p className="mb-3">{ticket.texto}</p>
          <div className="flex flex-wrap gap-2">
            <Badge>Tipo: {ticket.tipo_predicho || "sin determinar"}</Badge>
            <Badge>Categoría: {ticket.categoria_predicha || "sin determinar"}</Badge>
            {ticket.resuelto_por && <Badge>Resuelto por: {ticket.resuelto_por}</Badge>}
          </div>
        </Card.Body>
      </Card>

      <h2 className="mb-2 text-lg font-semibold">Conversación con Minutito</h2>
      <div className="mb-3">
        <ChatConversacion interacciones={interacciones} />
      </div>

      {!resuelto && (
        <form onSubmit={manejarEnvio}>
          <textarea
            rows={2}
            className={`${inputClass} mb-2`}
            value={mensaje}
            onChange={(e) => setMensaje(e.target.value)}
            placeholder="Escribe tu mensaje para Minutito..."
            required
          />
          <Button type="submit" disabled={enviando}>
            {enviando ? <Spinner size="sm" /> : "Enviar"}
          </Button>
        </form>
      )}
      {resuelto && <Alert variant="success">Este ticket ya está resuelto.</Alert>}
    </>
  );
}
