import { FileUp } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { cargarTicketsMasivos } from "../../api";
import Alert from "../../components/ui/Alert";
import Button from "../../components/ui/Button";
import Card from "../../components/ui/Card";
import Spinner from "../../components/ui/Spinner";

const MOTIVOS = [
  ["de_entrenamiento", "ya son parte del histórico de entrenamiento"],
  ["ya_cargados", "ya se habían cargado antes"],
  ["incompletos", "no traen tipo, categoría o descripción"],
  ["sin_id_o_repetidos", "no tienen ID o están repetidos en el archivo"],
];

/** Crea como tickets de MinutoDesk los tickets nuevos del export de la herramienta anterior. */
export default function CargaMasiva() {
  const [archivo, setArchivo] = useState(null);
  const [previa, setPrevia] = useState(null);
  const [creados, setCreados] = useState(null);
  const [trabajando, setTrabajando] = useState(false);
  const [error, setError] = useState(null);

  async function revisar(e) {
    const elegido = e.target.files?.[0] ?? null;
    setArchivo(elegido);
    setPrevia(null);
    setCreados(null);
    setError(null);
    if (!elegido) return;
    setTrabajando(true);
    try {
      setPrevia(await cargarTicketsMasivos(elegido, false));
    } catch (err) {
      setError(err.message);
    } finally {
      setTrabajando(false);
    }
  }

  async function confirmar() {
    setTrabajando(true);
    setError(null);
    try {
      const r = await cargarTicketsMasivos(archivo, true);
      setPrevia(null);
      setArchivo(null);
      setCreados(r.creados);
    } catch (err) {
      setError(err.message);
    } finally {
      setTrabajando(false);
    }
  }

  return (
    <Card>
      <Card.Body className="space-y-3">
        <div>
          <h2 className="text-sm font-semibold text-noche">Cargar tickets nuevos</h2>
          <p className="text-sm text-gray-500">
            Usa el export de siempre. Cada ticket nuevo se crea en MinutoDesk con su fecha y estado reales: el
            clasificador propone su tipo y categoría, y se guardan los reales para comparar. Los que ya están en
            el histórico se ignoran solos y repetir la carga no duplica nada.
          </p>
        </div>
        {error && <Alert variant="danger">{error}</Alert>}
        {creados != null && (
          <Alert variant="success">
            Se crearon {creados} tickets. Ya están en <Link className="font-medium underline" to="/admin/tickets">Tickets</Link>{" "}
            y la comparación con el clasificador en <Link className="font-medium underline" to="/admin">Reportes</Link>.
          </Alert>
        )}
        <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-linea bg-white px-3 py-2 text-sm font-medium text-noche hover:bg-marfil">
          <FileUp size={16} aria-hidden="true" />
          {archivo ? archivo.name : "Elegir archivo CSV"}
          <input type="file" accept=".csv,text/csv" className="sr-only" onChange={revisar} />
        </label>
        {trabajando && <Spinner size="sm" />}
        {previa && (
          <div className="space-y-2 rounded-lg bg-marfil p-3 text-sm">
            <p className="text-noche">
              De {previa.filas} filas, <strong>{previa.validos}</strong> se crearán como tickets nuevos.
            </p>
            <ul className="list-disc pl-5 text-gray-600">
              {MOTIVOS.filter(([clave]) => previa[clave] > 0).map(([clave, texto]) => (
                <li key={clave}>
                  {previa[clave]} {texto}
                </li>
              ))}
            </ul>
            <Button size="sm" variant="dark" disabled={trabajando || previa.validos === 0} onClick={confirmar}>
              Confirmar y crear {previa.validos} tickets
            </Button>
          </div>
        )}
      </Card.Body>
    </Card>
  );
}
