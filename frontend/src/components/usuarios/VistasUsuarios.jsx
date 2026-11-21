import { Columns3, LayoutGrid, Mail, MapPin, Table2 } from "lucide-react";
import { ETIQUETA_ROL } from "../../texto";

/*
 * Tres formas de ver la lista de usuarios, como en la bandeja de tickets: tabla, tablero
 * por rol (una columna para usuarios, técnicos y administradores) y tarjetas. Reciben la
 * lista ya filtrada y las mismas acciones; cada pantalla decide qué botones mostrar.
 */

export const VISTAS_USUARIOS = [
  { clave: "tabla", etiqueta: "Tabla", Icono: Table2 },
  { clave: "tablero", etiqueta: "Por rol", Icono: Columns3 },
  { clave: "tarjetas", etiqueta: "Tarjetas", Icono: LayoutGrid },
];

const CLAVE_GUARDADA = "minutodesk_vista_usuarios";

export function vistaGuardada() {
  try {
    const v = localStorage.getItem(CLAVE_GUARDADA);
    return VISTAS_USUARIOS.some((x) => x.clave === v) ? v : "tabla";
  } catch {
    return "tabla";
  }
}

export function guardarVista(vista) {
  try {
    localStorage.setItem(CLAVE_GUARDADA, vista);
  } catch {
    // sin almacenamiento (modo privado): la vista simplemente no se recuerda
  }
}

/** Control segmentado con indicador que se desliza (mismo gesto que en tickets). */
export function SelectorVistaUsuarios({ vista, onCambiar }) {
  const indice = Math.max(0, VISTAS_USUARIOS.findIndex((v) => v.clave === vista));
  return (
    <div role="radiogroup" aria-label="Forma de ver los usuarios" className="relative grid grid-cols-3 rounded-lg border border-linea bg-gray-100 p-1">
      <span
        aria-hidden="true"
        className="absolute inset-y-1 left-1 w-[calc((100%-0.5rem)/3)] rounded-md bg-superficie shadow-[0_1px_2px_rgb(27_30_34/0.12)] ring-1 ring-linea transition-transform duration-300 ease-[cubic-bezier(.34,1.4,.64,1)]"
        style={{ transform: `translateX(${indice * 100}%)` }}
      />
      {VISTAS_USUARIOS.map(({ clave, etiqueta, Icono }) => (
        <button
          key={clave}
          type="button"
          role="radio"
          aria-checked={vista === clave}
          onClick={() => onCambiar(clave)}
          className={`relative z-10 inline-flex items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
            vista === clave ? "text-noche" : "text-gray-500 hover:text-noche"
          }`}
        >
          <Icono size={15} aria-hidden="true" className={vista === clave ? "text-acento" : ""} />
          {etiqueta}
        </button>
      ))}
    </div>
  );
}

export function Iniciales({ nombre, className = "" }) {
  const partes = (nombre || "?").trim().split(/\s+/);
  const letras = ((partes[0]?.[0] || "") + (partes.length > 1 ? partes[partes.length - 1][0] : "")).toUpperCase();
  return (
    <span
      aria-hidden="true"
      className={`flex shrink-0 items-center justify-center rounded-md bg-grafito font-mono font-semibold text-white ring-1 ring-linea ${className}`}
    >
      {letras}
    </span>
  );
}

function Persona({ usuario: u, esYo, Estado, Acciones, compacta = false }) {
  return (
    <article
      className={`group relative overflow-hidden rounded-lg border border-linea bg-superficie shadow-[0_1px_0_rgb(27_30_34/0.04),0_1px_3px_rgb(27_30_34/0.05)] transition-[transform,box-shadow] duration-200 hover:-translate-y-0.5 hover:shadow-[0_10px_24px_-14px_rgb(27_30_34/0.35)] ${
        u.activo ? "" : "opacity-70"
      }`}
    >
      <span aria-hidden="true" className="franja-obra absolute inset-x-0 top-0 h-[3px] opacity-0 transition-opacity group-hover:opacity-100" />
      <div className={compacta ? "p-3" : "p-4"}>
        <div className="flex items-start gap-3">
          <Iniciales nombre={u.nombre} className={compacta ? "h-9 w-9 text-xs" : "h-11 w-11 text-sm"} />
          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-2">
              <p className="truncate font-semibold text-noche" title={u.nombre}>
                {u.nombre}
                {esYo && <span className="ml-1.5 text-xs font-normal text-gray-400">(tú)</span>}
              </p>
              {Estado && <Estado usuario={u} />}
            </div>
            <p className="mt-0.5 flex items-center gap-1.5 truncate text-[13px] text-gray-500" title={u.email}>
              <Mail size={12} aria-hidden="true" className="shrink-0" /> {u.email}
            </p>
            <p className="mt-0.5 flex items-center gap-1.5 truncate text-[13px] text-gray-500">
              <MapPin size={12} aria-hidden="true" className="shrink-0" /> {u.area || "Sin área"}
              {!compacta && (
                <>
                  <span aria-hidden="true">·</span>
                  <span className="font-mono text-[10.5px] uppercase tracking-[0.12em]">{ETIQUETA_ROL[u.rol] || u.rol}</span>
                </>
              )}
            </p>
          </div>
        </div>
        {Acciones && (
          <div className="mt-3 border-t border-dashed border-linea pt-3">
            <Acciones usuario={u} />
          </div>
        )}
      </div>
    </article>
  );
}

/** Cuadrícula de tarjetas. */
export function VistaTarjetas({ usuarios, yoId, Estado, Acciones }) {
  if (!usuarios.length) return <p className="rounded-lg border border-dashed border-linea p-6 text-center text-sm text-gray-500">No hay usuarios para este filtro.</p>;
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {usuarios.map((u) => (
        <Persona key={u.id} usuario={u} esYo={u.id === yoId} Estado={Estado} Acciones={Acciones} />
      ))}
    </div>
  );
}

/** Tablero con una columna por rol, como las cuadrillas de una obra. */
export function VistaTablero({ usuarios, yoId, Estado, Acciones }) {
  const roles = Object.keys(ETIQUETA_ROL);
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      {roles.map((rol) => {
        const del_rol = usuarios.filter((u) => u.rol === rol);
        const activos = del_rol.filter((u) => u.activo).length;
        return (
          <section key={rol} aria-label={ETIQUETA_ROL[rol]} className="flex min-w-0 flex-col rounded-lg border border-linea bg-gray-50">
            <header className="flex items-center justify-between gap-2 border-b border-linea px-3 py-2.5">
              <h3 className="font-mono text-[11px] font-semibold uppercase tracking-[0.14em] text-noche">{ETIQUETA_ROL[rol]}</h3>
              <span className="font-mono text-[11px] text-gray-500">
                {del_rol.length} · {activos} {activos === 1 ? "activo" : "activos"}
              </span>
            </header>
            <div className="max-h-[70vh] space-y-2.5 overflow-y-auto p-2.5">
              {del_rol.map((u) => (
                <Persona key={u.id} usuario={u} esYo={u.id === yoId} Estado={Estado} Acciones={Acciones} compacta />
              ))}
              {del_rol.length === 0 && <p className="px-1 py-4 text-center text-xs text-gray-400">Nadie con este rol en el filtro.</p>}
            </div>
          </section>
        );
      })}
    </div>
  );
}
