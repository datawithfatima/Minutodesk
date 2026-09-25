import Alert from "./ui/Alert";
import Badge from "./ui/Badge";
import Card from "./ui/Card";

const NIVEL_COLOR = {
  Nuevo: "gray",
  Autosuficiente: "sky",
  "Experto en autoservicio": "green",
};

export default function GamificacionCard({ detalle }) {
  return (
    <Card>
      <Card.Body>
        <div className="mb-3 flex items-center gap-2 text-lg font-semibold">
          {detalle.puntos} puntos
          <Badge color={NIVEL_COLOR[detalle.nivel] || "gray"}>{detalle.nivel}</Badge>
        </div>
        <hr className="mb-3 border-gray-200" />
        <h2 className="mb-2 text-sm font-semibold text-gray-700">Historial</h2>
        {detalle.historial.length === 0 && (
          <Alert variant="secondary">Todavía no tiene eventos de gamificación.</Alert>
        )}
        {detalle.historial.map((e) => (
          <div
            key={e.id}
            className="flex items-center justify-between border-b border-gray-100 py-2 last:border-b-0"
          >
            <div>
              <div>{e.motivo}</div>
              <small className="text-gray-500">
                Ticket #{e.ticket_id} · {new Date(e.creado_en).toLocaleString()}
              </small>
            </div>
            <Badge color="green">+{e.puntos_otorgados}</Badge>
          </div>
        ))}
      </Card.Body>
    </Card>
  );
}
