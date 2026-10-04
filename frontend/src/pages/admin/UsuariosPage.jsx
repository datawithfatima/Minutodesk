import { Mail, Plus, Search, Users } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  actualizarUsuario,
  crearUsuario,
  enviarEnlaceDeAcceso,
  listarAreas,
  listarUsuarios,
} from "../../api";
import { obtenerUsuario } from "../../auth";
import { ETIQUETA_ROL, normalizarTexto } from "../../texto";
import Alert from "../../components/ui/Alert";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Card from "../../components/ui/Card";
import PageHeader from "../../components/ui/PageHeader";
import Spinner from "../../components/ui/Spinner";
import { inputClass, labelClass } from "../../components/ui/formStyles";

const FORM_VACIO = { nombre: "", email: "", area_id: "", rol: "usuario", activo: true };

function textoDeCorreo(modo, destino, accion) {
  return modo === "smtp"
    ? `${accion} Enviamos el enlace a ${destino}.`
    : `${accion} El correo no está configurado: el enlace quedó guardado en backend/correos_enviados/ (modo desarrollo).`;
}

export default function UsuariosPage() {
  const yo = obtenerUsuario();
  const [usuarios, setUsuarios] = useState([]);
  const [areas, setAreas] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [aviso, setAviso] = useState(null);
  const [busqueda, setBusqueda] = useState("");
  const [filtroRol, setFiltroRol] = useState("");
  const [filtroEstado, setFiltroEstado] = useState("");
  const [panel, setPanel] = useState(null); // { modo: "crear" } | { modo: "editar", usuario }
  const [form, setForm] = useState(FORM_VACIO);
  const [guardando, setGuardando] = useState(false);

  const cargar = useCallback(async () => {
    const [listaUsuarios, listaAreas] = await Promise.all([listarUsuarios(), listarAreas()]);
    setUsuarios(listaUsuarios);
    setAreas(listaAreas);
  }, []);

  useEffect(() => {
    cargar()
      .catch((e) => setError(e.message))
      .finally(() => setCargando(false));
  }, [cargar]);

  const visibles = useMemo(
    () =>
      usuarios.filter((u) => {
        if (filtroRol && u.rol !== filtroRol) return false;
        if (filtroEstado === "activo" && !u.activo) return false;
        if (filtroEstado === "inactivo" && u.activo) return false;
        if (busqueda && !normalizarTexto(`${u.nombre} ${u.email}`).includes(normalizarTexto(busqueda)))
          return false;
        return true;
      }),
    [usuarios, busqueda, filtroRol, filtroEstado]
  );

  function abrirCrear() {
    const primeraActiva = areas.find((a) => a.activo);
    setForm({ ...FORM_VACIO, area_id: primeraActiva ? String(primeraActiva.id) : "" });
    setPanel({ modo: "crear" });
    setAviso(null);
    setError(null);
  }

  function abrirEditar(usuario) {
    setForm({
      nombre: usuario.nombre,
      email: usuario.email,
      area_id: String(usuario.area_id),
      rol: usuario.rol,
      activo: usuario.activo,
    });
    setPanel({ modo: "editar", usuario });
    setAviso(null);
    setError(null);
  }

  async function guardar(e) {
    e.preventDefault();
    setGuardando(true);
    setError(null);
    try {
      if (panel.modo === "crear") {
        const resultado = await crearUsuario({
          nombre: form.nombre,
          email: form.email,
          area_id: Number(form.area_id),
          rol: form.rol,
        });
        setAviso(textoDeCorreo(resultado.correo, form.email.trim().toLowerCase(), "Usuario creado."));
      } else {
        await actualizarUsuario(panel.usuario.id, {
          nombre: form.nombre,
          area_id: Number(form.area_id),
          rol: form.rol,
          activo: form.activo,
        });
        setAviso("Cambios guardados.");
      }
      setPanel(null);
      await cargar();
    } catch (e) {
      setError(e.message);
    } finally {
      setGuardando(false);
    }
  }

  async function enviarEnlace(usuario) {
    setError(null);
    setAviso(null);
    try {
      const r = await enviarEnlaceDeAcceso(usuario.id);
      setAviso(textoDeCorreo(r.correo, usuario.email, "Enlace de acceso generado."));
    } catch (e) {
      setError(e.message);
    }
  }

  const editandoPropio = panel?.modo === "editar" && panel.usuario.id === yo.id;
  const areasDisponibles = areas.filter(
    (a) => a.activo || (panel?.modo === "editar" && a.id === panel.usuario.area_id)
  );

  return (
    <>
      <PageHeader
        icon={Users}
        title="Usuarios"
        subtitle="Crea cuentas, asigna roles y áreas, y activa o desactiva personas."
      />

      {error && (
        <Alert variant="danger" className="mb-3">
          {error}
        </Alert>
      )}
      {aviso && (
        <Alert variant="success" className="mb-3">
          {aviso}
        </Alert>
      )}
      {cargando && <Spinner size="sm" />}

      {!cargando && (
        <>
          <Card className="mb-4">
            <Card.Body className="flex flex-wrap items-end gap-3">
              <div className="min-w-[200px] flex-1">
                <label className={labelClass}>Buscar</label>
                <div className="relative">
                  <Search
                    size={16}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
                  />
                  <input
                    className={`${inputClass} pl-9`}
                    value={busqueda}
                    onChange={(e) => setBusqueda(e.target.value)}
                    placeholder="Nombre o correo..."
                  />
                </div>
              </div>
              <div>
                <label className={labelClass}>Rol</label>
                <select
                  className={`${inputClass} w-44`}
                  value={filtroRol}
                  onChange={(e) => setFiltroRol(e.target.value)}
                >
                  <option value="">Todos</option>
                  {Object.entries(ETIQUETA_ROL).map(([valor, etiqueta]) => (
                    <option key={valor} value={valor}>
                      {etiqueta}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className={labelClass}>Estado</label>
                <select
                  className={`${inputClass} w-36`}
                  value={filtroEstado}
                  onChange={(e) => setFiltroEstado(e.target.value)}
                >
                  <option value="">Todos</option>
                  <option value="activo">Activos</option>
                  <option value="inactivo">Inactivos</option>
                </select>
              </div>
              <Button variant="dark" onClick={abrirCrear}>
                <Plus size={16} /> Nuevo usuario
              </Button>
            </Card.Body>
          </Card>

          {panel && (
            <Card className="mb-4">
              <Card.Body>
                <h2 className="mb-3 text-sm font-semibold text-gray-700">
                  {panel.modo === "crear" ? "Nuevo usuario" : `Editar: ${panel.usuario.nombre}`}
                </h2>
                <form onSubmit={guardar} className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  <div>
                    <label className={labelClass}>Nombre completo</label>
                    <input
                      className={inputClass}
                      value={form.nombre}
                      onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                      required
                      autoComplete="off"
                    />
                  </div>
                  <div>
                    <label className={labelClass}>Correo electrónico</label>
                    <input
                      type="email"
                      className={inputClass}
                      value={form.email}
                      onChange={(e) => setForm({ ...form, email: e.target.value })}
                      required
                      disabled={panel.modo === "editar"}
                      autoComplete="off"
                    />
                  </div>
                  <div>
                    <label className={labelClass}>Área</label>
                    <select
                      className={inputClass}
                      value={form.area_id}
                      onChange={(e) => setForm({ ...form, area_id: e.target.value })}
                      required
                    >
                      {areasDisponibles.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.nombre}
                          {a.activo ? "" : " (inactiva)"}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className={labelClass}>Rol</label>
                    <select
                      className={inputClass}
                      value={form.rol}
                      onChange={(e) => setForm({ ...form, rol: e.target.value })}
                      disabled={editandoPropio}
                    >
                      {Object.entries(ETIQUETA_ROL).map(([valor, etiqueta]) => (
                        <option key={valor} value={valor}>
                          {etiqueta}
                        </option>
                      ))}
                    </select>
                  </div>
                  {panel.modo === "editar" && (
                    <label className="flex items-center gap-2 text-sm text-gray-700">
                      <input
                        type="checkbox"
                        checked={form.activo}
                        disabled={editandoPropio}
                        onChange={(e) => setForm({ ...form, activo: e.target.checked })}
                      />
                      Cuenta activa
                    </label>
                  )}
                  {editandoPropio && (
                    <p className="text-xs text-gray-400 md:col-span-2">
                      No puedes cambiar tu propio rol ni desactivar tu cuenta.
                    </p>
                  )}
                  {panel.modo === "crear" && (
                    <p className="text-xs text-gray-400 md:col-span-2">
                      La persona recibirá un correo con un enlace para activar su cuenta y elegir
                      su contraseña.
                    </p>
                  )}
                  <div className="flex gap-2 md:col-span-2">
                    <Button type="submit" variant="dark" disabled={guardando}>
                      {guardando ? <Spinner size="sm" /> : "Guardar"}
                    </Button>
                    <Button type="button" variant="outlineSecondary" onClick={() => setPanel(null)}>
                      Cancelar
                    </Button>
                  </div>
                </form>
              </Card.Body>
            </Card>
          )}

          <Card className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 text-gray-600">
                <tr>
                  <th className="px-3 py-2">Nombre</th>
                  <th className="px-3 py-2">Correo</th>
                  <th className="px-3 py-2">Área</th>
                  <th className="px-3 py-2">Rol</th>
                  <th className="px-3 py-2">Estado</th>
                  <th className="px-3 py-2 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {visibles.map((u) => (
                  <tr key={u.id} className="hover:bg-gray-50">
                    <td className="px-3 py-2 font-medium text-gray-900">
                      {u.nombre}
                      {u.id === yo.id && <span className="ml-2 text-xs text-gray-400">(tú)</span>}
                    </td>
                    <td className="px-3 py-2 text-gray-500">{u.email}</td>
                    <td className="px-3 py-2">{u.area}</td>
                    <td className="px-3 py-2">{ETIQUETA_ROL[u.rol] || u.rol}</td>
                    <td className="px-3 py-2">
                      {!u.activo ? (
                        <Badge color="gray">Inactivo</Badge>
                      ) : u.pendiente_activacion ? (
                        <Badge color="amber">Pendiente de activar</Badge>
                      ) : (
                        <Badge color="green">Activo</Badge>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex justify-end gap-2">
                        <Button variant="outlineSecondary" size="sm" onClick={() => abrirEditar(u)}>
                          Editar
                        </Button>
                        {u.activo && (
                          <Button variant="outlineSecondary" size="sm" onClick={() => enviarEnlace(u)}>
                            <Mail size={14} /> Enviar enlace
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {visibles.length === 0 && (
              <p className="p-4 text-sm text-gray-500">No hay usuarios para este filtro.</p>
            )}
          </Card>
        </>
      )}
    </>
  );
}
