import {
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  CloudUpload,
  DatabaseBackup,
  Download,
  HardDriveDownload,
  NotebookPen,
  Search,
  ShieldAlert,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { crearRespaldo, descargarRespaldo, obtenerBitacora, obtenerRespaldos } from "../../api";
import { Panel } from "../../components/charts/Charts";
import { EncabezadoSeccion } from "../../components/charts/Tablero";
import Alert from "../../components/ui/Alert";
import Button from "../../components/ui/Button";
import PageHeader from "../../components/ui/PageHeader";
import Spinner from "../../components/ui/Spinner";
import { inputClass } from "../../components/ui/formStyles";
import Selector from "../../components/ui/Selector";

/*
 * Bitácora de auditoría como «libro de obra»: cada asiento dice quién hizo qué y cuándo.
 * Arriba, los respaldos de la base de datos (automáticos y manuales).
 */

const fechaHora = (iso) =>
  new Date(iso).toLocaleString("es-EC", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });

function tamano(bytes) {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

function Respaldos() {
  const [estado, setEstado] = useState(null);
  const [error, setError] = useState(null);
  const [creando, setCreando] = useState(false);
  const [aviso, setAviso] = useState(null);

  const cargar = useCallback(() => obtenerRespaldos().then(setEstado).catch((e) => setError(e.message)), []);
  useEffect(() => {
    cargar();
  }, [cargar]);

  async function crear() {
    setCreando(true);
    setError(null);
    setAviso(null);
    try {
      const hecho = await crearRespaldo();
      setAviso(
        hecho.error_copia
          ? `Respaldo creado, pero no se pudo copiar a OneDrive: ${hecho.error_copia}`
          : `Respaldo creado y verificado${hecho.copia_externa ? " (también copiado a OneDrive)" : ""}: ${hecho.nombre}`
      );
      await cargar();
    } catch (e) {
      setError(e.message);
    } finally {
      setCreando(false);
    }
  }

  async function descargar(nombre) {
    setError(null);
    try {
      await descargarRespaldo(nombre);
    } catch (e) {
      setError(e.message);
    }
  }

  if (!estado) return error ? <Alert variant="danger">{error}</Alert> : <Spinner size="sm" />;
  const horasDesde = estado.ultimo ? (Date.now() - new Date(estado.ultimo).getTime()) / 3.6e6 : null;
  const atrasado = horasDesde == null || horasDesde > estado.cada_horas * 1.5;

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
      <Panel className="lg:col-span-5">
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-grafito text-casco">
            <DatabaseBackup size={19} aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <p className="font-mono text-[10.5px] uppercase tracking-[0.14em] text-gray-500">Último respaldo</p>
            <p className="text-xl font-bold text-noche">{estado.ultimo ? fechaHora(estado.ultimo) : "Ninguno todavía"}</p>
            <p className={`mt-1 flex items-center gap-1.5 text-sm ${atrasado ? "text-amber-700" : "text-gray-600"}`}>
              {atrasado && <AlertTriangle size={14} aria-hidden="true" />}
              {estado.automatico
                ? `Automático cada ${estado.cada_horas} h; se guardan los últimos ${estado.conservar}.`
                : "El respaldo automático está apagado (RESPALDO_AUTOMATICO=0)."}
            </p>
          </div>
        </div>
        {estado.copia_externa && (
          <p className="mt-3 flex items-center gap-1.5 text-sm text-green-700">
            <CloudUpload size={15} aria-hidden="true" />
            Cada respaldo también se copia a tu OneDrive ({estado.copia_externa_respaldos} guardados allí).
          </p>
        )}
        <p className="mt-4 rounded-md border border-dashed border-linea bg-gray-50 p-3 text-xs leading-relaxed text-gray-600">
          Cada respaldo es una copia completa de la base, verificada al crearla. Se guardan en{" "}
          <span className="break-all font-mono text-[11px] text-noche">{estado.carpeta}</span>. Para restaurar uno, detén el
          backend y reemplaza <span className="font-mono text-[11px] text-noche">minutodesk.db</span> por la copia.
        </p>
        <Button className="mt-4" onClick={crear} disabled={creando}>
          <HardDriveDownload size={16} aria-hidden="true" />
          {creando ? "Creando respaldo…" : "Crear respaldo ahora"}
        </Button>
        {aviso && (
          <Alert variant="success" className="mt-3">
            {aviso}
          </Alert>
        )}
        {error && (
          <Alert variant="danger" className="mt-3">
            {error}
          </Alert>
        )}
      </Panel>

      <Panel className="lg:col-span-7" relleno="p-0">
        <div className="flex items-center justify-between border-b border-linea px-4 py-3 sm:px-5">
          <h3 className="flex items-center gap-2 text-sm font-bold text-noche">
            <span aria-hidden="true" className="h-3 w-[3px] shrink-0 rounded-[1px] bg-acento" />
            Respaldos guardados
          </h3>
          <span className="font-mono text-xs text-gray-500">{estado.respaldos.length}</span>
        </div>
        {estado.respaldos.length === 0 ? (
          <p className="px-5 py-6 text-sm text-gray-500">Aún no hay respaldos. El primero se crea solo al arrancar el backend.</p>
        ) : (
          <ul className="max-h-72 divide-y divide-dashed divide-linea overflow-auto">
            {estado.respaldos.map((r) => (
              <li key={r.nombre} className="flex items-center gap-3 px-4 py-2.5 sm:px-5">
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-semibold text-noche">{fechaHora(r.fecha)}</span>
                  <span className="block truncate font-mono text-[11px] text-gray-500">
                    {r.manual ? "Manual" : "Automático"} · {tamano(r.tamano)}
                  </span>
                </span>
                <Button size="sm" variant="outlineSecondary" onClick={() => descargar(r.nombre)} aria-label={`Descargar ${r.nombre}`}>
                  <Download size={14} aria-hidden="true" /> Descargar
                </Button>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}

function Bitacora() {
  const [filtros, setFiltros] = useState({ accion: "", actor_id: "", q: "", desde: "", hasta: "", solo_fallos: false });
  const [busqueda, setBusqueda] = useState("");
  const [pagina, setPagina] = useState(1);
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const espera = setTimeout(() => setFiltros((f) => (f.q === busqueda ? f : { ...f, q: busqueda })), 350);
    return () => clearTimeout(espera);
  }, [busqueda]);

  useEffect(() => {
    setPagina(1);
  }, [filtros]);

  useEffect(() => {
    obtenerBitacora({ ...filtros, solo_fallos: filtros.solo_fallos || undefined, pagina })
      .then((d) => {
        setDatos(d);
        setError(null);
      })
      .catch((e) => setError(e.message));
  }, [filtros, pagina]);

  const cambiar = (campo) => (e) =>
    setFiltros((f) => ({ ...f, [campo]: e.target.type === "checkbox" ? e.target.checked : e.target.value }));
  const paginas = datos ? Math.max(1, Math.ceil(datos.total / datos.por_pagina)) : 1;

  return (
    <Panel relleno="p-0" className="overflow-hidden">
      <div className="grid grid-cols-1 gap-2 border-b border-linea bg-gray-50 p-3 sm:grid-cols-2 sm:p-4 2xl:grid-cols-[minmax(0,1.4fr)_repeat(2,minmax(0,1fr))_auto_auto]">
        <label className="relative">
          <span className="sr-only">Buscar en la bitácora</span>
          <Search size={15} aria-hidden="true" className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="search"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            placeholder="Buscar: ticket #12, correo, detalle…"
            className={`${inputClass} pl-9`}
          />
        </label>
        <Selector value={filtros.accion} onChange={cambiar("accion")} className={inputClass} aria-label="Acción">
          <option value="">Todas las acciones</option>
          {datos?.acciones.map((a) => (
            <option key={a.clave} value={a.clave}>
              {a.titulo}
            </option>
          ))}
        </Selector>
        <Selector value={filtros.actor_id} onChange={cambiar("actor_id")} className={inputClass} aria-label="Persona">
          <option value="">Todas las personas</option>
          {datos?.personas.map(([id, nombre]) => (
            <option key={id} value={id}>
              {nombre}
            </option>
          ))}
        </Selector>
        <div className="flex items-center gap-1.5">
          <input type="date" value={filtros.desde} onChange={cambiar("desde")} className={inputClass} aria-label="Desde" />
          <input type="date" value={filtros.hasta} onChange={cambiar("hasta")} className={inputClass} aria-label="Hasta" />
        </div>
        <label className="flex items-center gap-2 whitespace-nowrap text-sm text-gray-700">
          <input type="checkbox" checked={filtros.solo_fallos} onChange={cambiar("solo_fallos")} className="h-4 w-4 accent-[var(--color-acento)]" />
          Solo fallos y accesos denegados
        </label>
      </div>

      {error && (
        <Alert variant="danger" className="m-4">
          {error}
        </Alert>
      )}
      {!datos && !error && (
        <div className="p-5">
          <Spinner size="sm" />
        </div>
      )}

      {datos && datos.registros.length === 0 && (
        <p className="px-5 py-8 text-center text-sm text-gray-500">No hay asientos que coincidan con estos filtros.</p>
      )}

      {datos && datos.registros.length > 0 && (
        <ol className="divide-y divide-dashed divide-linea">
          {datos.registros.map((r) => (
            <li key={r.id} className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 px-4 py-3 sm:grid-cols-[172px_auto_minmax(0,1fr)] sm:px-5">
              <time className="col-span-2 font-mono text-[11px] tabular-nums text-gray-500 sm:col-span-1 sm:pt-0.5">
                {fechaHora(r.fecha)}
              </time>
              <span
                aria-hidden="true"
                className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-[2px] ${r.exito ? "bg-casco" : "bg-red-600"}`}
              />
              <div className="min-w-0">
                <p className="text-sm text-noche">
                  <span className="font-semibold">{r.actor || "Sin sesión"}</span>{" "}
                  <span className={r.exito ? "" : "text-red-700"}>
                    {!r.exito && <ShieldAlert size={13} aria-hidden="true" className="mr-1 inline -translate-y-px" />}
                    {r.descripcion.charAt(0).toLowerCase() + r.descripcion.slice(1)}
                  </span>
                </p>
                {(r.detalle || r.ip) && (
                  <p className="mt-0.5 break-words font-mono text-[11px] text-gray-500">
                    {r.detalle}
                    {r.detalle && r.ip ? " · " : ""}
                    {r.ip && `IP ${r.ip}`}
                  </p>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}

      {datos && datos.total > 0 && (
        <div className="flex items-center justify-between gap-3 border-t border-linea px-4 py-2.5 text-sm text-gray-600 sm:px-5">
          <span className="font-mono text-xs">
            {datos.total} asientos · página {pagina} de {paginas}
          </span>
          <div className="flex gap-1.5">
            <Button size="sm" variant="outlineSecondary" disabled={pagina <= 1} onClick={() => setPagina((p) => p - 1)} aria-label="Página anterior">
              <ChevronLeft size={15} />
            </Button>
            <Button size="sm" variant="outlineSecondary" disabled={pagina >= paginas} onClick={() => setPagina((p) => p + 1)} aria-label="Página siguiente">
              <ChevronRight size={15} />
            </Button>
          </div>
        </div>
      )}
    </Panel>
  );
}

export default function BitacoraPage() {
  return (
    <>
      <PageHeader icon={NotebookPen} title="Bitácora y respaldos" />
      <EncabezadoSeccion
        numero={1}
        titulo="Respaldos de la base de datos"
        subtitulo="Copias automáticas para no perder tickets, conversaciones ni las cifras medidas."
      />
      <Respaldos />
      <EncabezadoSeccion
        numero={2}
        titulo="Libro de obra · bitácora de auditoría"
        subtitulo="Quién hizo qué y cuándo: inicios de sesión, cambios de usuarios y áreas, acciones sobre tickets, descargas, exportaciones y respaldos. Nunca guarda contraseñas ni el texto de los mensajes."
      />
      <Bitacora />
      <div className="h-6" />
    </>
  );
}
