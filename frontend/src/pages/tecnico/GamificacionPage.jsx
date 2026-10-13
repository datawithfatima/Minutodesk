import { Medal } from "lucide-react";
import { useEffect, useState } from "react";
import { listarClientes, obtenerGamificacion } from "../../api";
import Alert from "../../components/ui/Alert";
import Card from "../../components/ui/Card";
import PageHeader from "../../components/ui/PageHeader";
import Spinner from "../../components/ui/Spinner";
import GamificacionCard from "../../components/GamificacionCard";

export default function GamificacionPage() {
  const [clientes, setClientes] = useState([]);
  const [clienteId, setClienteId] = useState(null);
  const [detalle, setDetalle] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    listarClientes()
      .then((lista) => {
        const ordenada = lista
          .filter((c) => c.rol === "usuario" && c.activo)
          .sort((a, b) => b.puntos - a.puntos);
        setClientes(ordenada);
        if (ordenada.length > 0) setClienteId(ordenada[0].id);
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (clienteId == null) return;
    obtenerGamificacion(clienteId)
      .then(setDetalle)
      .catch((e) => setError(e.message));
  }, [clienteId]);

  return (
    <>
      <PageHeader
        icon={Medal}
        title="Ranking de logros"
        subtitle="Posiciones por puntos de los usuarios y el detalle de cómo los ganaron."
      />
      {error && (
        <Alert variant="danger" className="mb-3">
          {error}
        </Alert>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card className="overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-marfil text-xs uppercase tracking-wide text-gray-500 [&_th]:font-medium">
              <tr>
                <th className="px-3 py-2">Usuario</th>
                <th className="px-3 py-2">Puntos</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {clientes.map((c) => (
                <tr
                  key={c.id}
                  onClick={() => setClienteId(c.id)}
                  className={`cursor-pointer hover:bg-marfil ${
                    c.id === clienteId ? "bg-acento-50" : ""
                  }`}
                >
                  <td className="px-3 py-2">
                    {c.nombre} <span className="text-gray-500">({c.area})</span>
                  </td>
                  <td className="px-3 py-2">{c.puntos}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <div>
          {!detalle && <Spinner size="sm" />}
          {detalle && <GamificacionCard detalle={detalle} />}
        </div>
      </div>
    </>
  );
}
