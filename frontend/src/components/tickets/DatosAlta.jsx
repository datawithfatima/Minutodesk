import { UserPlus } from "lucide-react";
import { textoSiNo } from "./formato";

function Fila({ etiqueta, children }) {
  return (
    <div>
      <dt className="text-xs text-gray-500">{etiqueta}</dt>
      <dd className="mt-0.5 text-sm text-noche">{children || "—"}</dd>
    </div>
  );
}

function Fichas({ items }) {
  if (!items?.length) return "—";
  return (
    <span className="flex flex-wrap gap-1.5">
      {items.map((i) => (
        <span key={i} className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-700">
          {i}
        </span>
      ))}
    </span>
  );
}

/** Datos del formulario de alta de colaborador (vienen como JSON en el ticket). */
export default function DatosAlta({ datosJson }) {
  let d;
  try {
    d = JSON.parse(datosJson);
  } catch {
    return null;
  }
  const ingreso = d.fecha_ingreso ? new Date(`${d.fecha_ingreso}T00:00:00`).toLocaleDateString("es-EC") : null;

  return (
    <div className="rounded-lg border border-linea bg-white p-4">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-noche">
        <UserPlus size={16} /> Datos del alta de colaborador
      </div>
      <dl className="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
        <Fila etiqueta="Nombres y apellidos">{d.nombres}</Fila>
        <Fila etiqueta="Cédula">{d.cedula}</Fila>
        <Fila etiqueta="Cargo">{d.cargo}</Fila>
        <Fila etiqueta="Fecha de ingreso">{ingreso}</Fila>
        <Fila etiqueta="Monitor">{textoSiNo(d.monitor)}</Fila>
        <Fila etiqueta="Teléfono fijo">{textoSiNo(d.telefono_fijo)}</Fila>
        <Fila etiqueta="Grupo">{d.grupo}</Fila>
        <Fila etiqueta="Licencia SAP">{d.licencia_sap}</Fila>
        <div className="sm:col-span-2">
          <Fila etiqueta="Listas de distribución de correo">
            <Fichas items={d.listas_distribucion} />
          </Fila>
        </div>
        <div className="sm:col-span-2">
          <Fila etiqueta="Aplicaciones a usar">
            <Fichas items={d.aplicaciones} />
          </Fila>
        </div>
        <div className="sm:col-span-2">
          <Fila etiqueta="Permisos SAP">{d.permisos_sap}</Fila>
        </div>
        <div className="sm:col-span-2">
          <Fila etiqueta="Observaciones">
            <span className="whitespace-pre-line">{d.observaciones}</span>
          </Fila>
        </div>
      </dl>
    </div>
  );
}
