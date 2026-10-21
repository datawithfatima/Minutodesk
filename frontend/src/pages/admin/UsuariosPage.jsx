import { KeyRound, Plus, Search, Trash2, Users } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  actualizarUsuario,
  crearUsuario,
  eliminarUsuario,
  listarAreas,
  listarUsuarios,
  restablecerPassword,
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

// Si no hay SMTP configurado el correo no sale: queda como archivo en el servidor.
const SIN_SMTP =
  "No se pudo enviar el correo porque el servidor no tiene configurado el envío (SMTP). " +
  "El enlace quedó guardado en backend/correos_enviados/ del servidor.";

function EstadoCuenta({ usuario: u }) {
  if (!u.activo) return <Badge color="gray">Inactivo</Badge>;
  if (u.pendiente_activacion) return <Badge color="amber">Pendiente de activar</Badge>;
  if (u.debe_cambiar_password) return <Badge color="amber">Debe cambiar contraseña</Badge>;
  return <Badge color="green">Activo</Badge>;
}

function AccionesUsuario({ usuario: u, esYo, onEditar, onRestablecer, onEliminar, className = "" }) {
  return (
    <div className={`flex flex-wrap gap-2 ${className}`}>
      <Button variant="outlineSecondary" size="sm" onClick={() => onEditar(u)}>
        Editar
      </Button>
      {u.activo && !esYo && (
        <Button
          variant="outlineSecondary"
          size="sm"
          onClick={() => onRestablecer(u)}
          title="Restablecer contraseña"
        >
          <KeyRound size={14} /> Restablecer
          <span className="-ml-1.5 hidden sm:inline"> contraseña</span>
        </Button>
      )}
      {!esYo && (
        <Button variant="outlineDanger" size="sm" onClick={() => onEliminar(u)}>
          <Trash2 size={14} /> Eliminar
        </Button>
      )}
    </div>
  );
}

export default function UsuariosPage() {
  const yo = obtenerUsuario();
  const [usuarios, setUsuarios] = useState([]);
  const [areas, setAreas] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [aviso, setAviso] = useState(null);
  const [advertencia, setAdvertencia] = useState(null);
  const [busqueda, setBusqueda] = useState("");
  const [filtroRol, setFiltroRol] = useState("");
  const [filtroEstado, setFiltroEstado] = useState("");
  const [panel, setPanel] = useState(null); // { modo: "crear" } | { modo: "editar", usuario }
  const [form, setForm] = useState(FORM_VACIO);
  const [guardando, setGuardando] = useState(false);
  const formulario = useRef(null);

  // En móvil el formulario queda arriba de la lista: se lleva la vista hasta él al abrirlo.
  useEffect(() => {
    if (panel) formulario.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [panel]);

  // Los avisos aparecen arriba: se suben para que se vean.
  useEffect(() => {
    if (advertencia || aviso) window.scrollTo({ top: 0, behavior: "smooth" });
  }, [advertencia, aviso]);

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
    setAdvertencia(null);
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
        if (resultado.envio === "smtp") {
          setAviso(
            `Se creó la cuenta de ${resultado.usuario.nombre}. Le enviamos a ${resultado.usuario.email} un enlace para que elija su contraseña.`
          );
        } else {
          setAdvertencia(`Se creó la cuenta de ${resultado.usuario.nombre}. ${SIN_SMTP}`);
        }
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

  async function restablecer(usuario) {
    const confirmado = window.confirm(
      `¿Enviar a ${usuario.email} un enlace para que ${usuario.nombre} elija una contraseña nueva? Nadie más verá la contraseña.`
    );
    if (!confirmado) return;
    setError(null);
    setAviso(null);
    setAdvertencia(null);
    try {
      const r = await restablecerPassword(usuario.id);
      if (r.envio === "smtp") setAviso(r.mensaje);
      else setAdvertencia(SIN_SMTP);
      await cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  async function eliminar(usuario) {
    const confirmado = window.confirm(
      `¿Eliminar a ${usuario.nombre} (${usuario.email})? Esta acción no se puede deshacer.`
    );
    if (!confirmado) return;
    setError(null);
    setAviso(null);
    try {
      await eliminarUsuario(usuario.id);
      setAviso(`Se eliminó a ${usuario.nombre}.`);
      if (panel?.usuario?.id === usuario.id) setPanel(null);
      await cargar();
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
      {advertencia && (
        <Alert variant="warning" className="mb-3">
          {advertencia}
        </Alert>
      )}
      {cargando && <Spinner size="sm" />}

      {!cargando && (
        <>
          <Card className="mb-4">
            <Card.Body className="flex flex-wrap items-end gap-3">
              <div className="w-full min-w-0 sm:w-auto sm:min-w-[200px] sm:flex-1">
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
              <div className="min-w-0 flex-1 sm:flex-none">
                <label className={labelClass}>Rol</label>
                <select
                  className={`${inputClass} sm:w-44`}
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
              <div className="min-w-0 flex-1 sm:flex-none">
                <label className={labelClass}>Estado</label>
                <select
                  className={`${inputClass} sm:w-36`}
                  value={filtroEstado}
                  onChange={(e) => setFiltroEstado(e.target.value)}
                >
                  <option value="">Todos</option>
                  <option value="activo">Activos</option>
                  <option value="inactivo">Inactivos</option>
                </select>
              </div>
              <Button variant="dark" onClick={abrirCrear} className="w-full sm:w-auto">
                <Plus size={16} /> Nuevo usuario
              </Button>
            </Card.Body>
          </Card>

          {panel && (
            <div ref={formulario} className="scroll-mt-20">
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
                        La persona recibirá en este correo un enlace para elegir su contraseña
                        (vale 3 días). Nadie más la conoce, ni siquiera el administrador.
                      </p>
                    )}
                    <div className="flex flex-wrap gap-2 md:col-span-2">
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
            </div>
          )}

          {/* Móvil y tablet: una tarjeta por persona. */}
          <Card className="divide-y divide-gray-100 overflow-hidden lg:hidden">
            {visibles.map((u) => (
              <div key={u.id} className="space-y-2 px-4 py-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="truncate font-medium text-noche">
                      {u.nombre}
                      {u.id === yo.id && <span className="ml-2 text-xs text-gray-400">(tú)</span>}
                    </div>
                    <div className="truncate text-sm text-gray-500">{u.email}</div>
                  </div>
                  <EstadoCuenta usuario={u} />
                </div>
                <div className="text-xs text-gray-500">
                  {ETIQUETA_ROL[u.rol] || u.rol} · {u.area}
                </div>
                <AccionesUsuario
                  usuario={u}
                  esYo={u.id === yo.id}
                  onEditar={abrirEditar}
                  onRestablecer={restablecer}
                  onEliminar={eliminar}
                />
              </div>
            ))}
            {visibles.length === 0 && (
              <p className="p-4 text-sm text-gray-500">No hay usuarios para este filtro.</p>
            )}
          </Card>

          <Card className="hidden overflow-x-auto lg:block">
            <table className="w-full text-left text-sm">
              <thead className="bg-marfil text-xs uppercase tracking-wide text-gray-500 [&_th]:font-medium">
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
                  <tr key={u.id} className="hover:bg-marfil">
                    <td className="px-3 py-2 font-medium text-noche">
                      {u.nombre}
                      {u.id === yo.id && <span className="ml-2 text-xs text-gray-400">(tú)</span>}
                    </td>
                    <td className="px-3 py-2 text-gray-500">{u.email}</td>
                    <td className="px-3 py-2">{u.area}</td>
                    <td className="px-3 py-2">{ETIQUETA_ROL[u.rol] || u.rol}</td>
                    <td className="px-3 py-2">
                      <EstadoCuenta usuario={u} />
                    </td>
                    <td className="px-3 py-2">
                      <AccionesUsuario
                        usuario={u}
                        esYo={u.id === yo.id}
                        onEditar={abrirEditar}
                        onRestablecer={restablecer}
                        onEliminar={eliminar}
                        className="justify-end"
                      />
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
