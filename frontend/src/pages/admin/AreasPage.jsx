import { Building2, Plus } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { actualizarArea, crearArea, listarAreas } from "../../api";
import Alert from "../../components/ui/Alert";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Card from "../../components/ui/Card";
import PageHeader from "../../components/ui/PageHeader";
import Spinner from "../../components/ui/Spinner";
import { inputClass, labelClass } from "../../components/ui/formStyles";

export default function AreasPage() {
  const [areas, setAreas] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [nuevoNombre, setNuevoNombre] = useState("");
  const [editando, setEditando] = useState(null); // { id, nombre }

  const cargar = useCallback(async () => setAreas(await listarAreas()), []);

  useEffect(() => {
    cargar()
      .catch((e) => setError(e.message))
      .finally(() => setCargando(false));
  }, [cargar]);

  async function ejecutar(accion) {
    setError(null);
    try {
      await accion();
      await cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  function agregar(e) {
    e.preventDefault();
    ejecutar(async () => {
      await crearArea({ nombre: nuevoNombre });
      setNuevoNombre("");
    });
  }

  function guardarNombre() {
    ejecutar(async () => {
      await actualizarArea(editando.id, { nombre: editando.nombre });
      setEditando(null);
    });
  }

  return (
    <>
      <PageHeader
        icon={Building2}
        title="Áreas"
        subtitle="Catálogo de áreas a las que pertenecen los usuarios. Desactivar un área no borra a quienes ya la tienen."
      />

      {error && (
        <Alert variant="danger" className="mb-3">
          {error}
        </Alert>
      )}
      {cargando && <Spinner size="sm" />}

      {!cargando && (
        <>
          <Card className="mb-4">
            <Card.Body>
              <form onSubmit={agregar} className="flex flex-wrap items-end gap-3">
                <div className="min-w-[220px] flex-1">
                  <label className={labelClass}>Nueva área</label>
                  <input
                    className={inputClass}
                    value={nuevoNombre}
                    onChange={(e) => setNuevoNombre(e.target.value)}
                    placeholder="Ej: Recursos Humanos"
                    required
                  />
                </div>
                <Button type="submit" variant="dark">
                  <Plus size={16} /> Agregar
                </Button>
              </form>
            </Card.Body>
          </Card>

          <Card className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 text-gray-600">
                <tr>
                  <th className="px-3 py-2">Área</th>
                  <th className="px-3 py-2">Estado</th>
                  <th className="px-3 py-2 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {areas.map((a) => (
                  <tr key={a.id} className="hover:bg-gray-50">
                    <td className="px-3 py-2">
                      {editando?.id === a.id ? (
                        <input
                          className={`${inputClass} max-w-xs`}
                          value={editando.nombre}
                          onChange={(e) => setEditando({ ...editando, nombre: e.target.value })}
                          autoFocus
                        />
                      ) : (
                        <span className="font-medium text-gray-900">{a.nombre}</span>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <Badge color={a.activo ? "green" : "gray"}>
                        {a.activo ? "Activa" : "Inactiva"}
                      </Badge>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex justify-end gap-2">
                        {editando?.id === a.id ? (
                          <>
                            <Button size="sm" variant="dark" onClick={guardarNombre}>
                              Guardar
                            </Button>
                            <Button
                              size="sm"
                              variant="outlineSecondary"
                              onClick={() => setEditando(null)}
                            >
                              Cancelar
                            </Button>
                          </>
                        ) : (
                          <>
                            <Button
                              size="sm"
                              variant="outlineSecondary"
                              onClick={() => setEditando({ id: a.id, nombre: a.nombre })}
                            >
                              Renombrar
                            </Button>
                            <Button
                              size="sm"
                              variant="outlineSecondary"
                              onClick={() =>
                                ejecutar(() => actualizarArea(a.id, { activo: !a.activo }))
                              }
                            >
                              {a.activo ? "Desactivar" : "Activar"}
                            </Button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </>
      )}
    </>
  );
}
