import { cedulaValida } from "../../components/tickets/formato";
import { inputClass } from "../../components/ui/formStyles";

export const ALTA_VACIA = {
  nombres: "",
  fecha_ingreso: "",
  cedula: "",
  cargo: "",
  monitor: null,
  telefono_fijo: null,
  grupo: "",
  listas_distribucion: [],
  aplicaciones: [],
  licencia_sap: null,
  permisos_sap: "",
  observaciones: "",
};

/** Primer problema del formulario de alta, o null si está completo. */
export function problemaDelAlta(a) {
  if (!a.nombres.trim()) return "Escribe los nombres y apellidos del colaborador.";
  if (!a.fecha_ingreso) return "Indica la fecha de ingreso.";
  if (!cedulaValida(a.cedula.trim())) return "La cédula no es válida: escribe la cédula real del colaborador (10 dígitos).";
  if (!a.cargo.trim()) return "Indica el cargo.";
  if (!a.observaciones.trim()) return "Escribe las observaciones (por ejemplo, qué necesita para empezar).";
  return null;
}

function Pregunta({ numero, titulo, requerido, children }) {
  return (
    <div>
      <div className="mb-2 text-sm font-medium text-noche">
        {numero}. {titulo} {requerido && <span className="text-red-600">*</span>}
      </div>
      {children}
    </div>
  );
}

function SiNo({ valor, onCambio, nombre }) {
  return (
    <div className="flex gap-5 text-sm text-gray-700">
      {[
        [true, "Sí"],
        [false, "No"],
      ].map(([v, etiqueta]) => (
        <label key={etiqueta} className="flex cursor-pointer items-center gap-2">
          <input type="radio" name={nombre} checked={valor === v} onChange={() => onCambio(v)} />
          {etiqueta}
        </label>
      ))}
      {valor !== null && (
        <button type="button" onClick={() => onCambio(null)} className="text-xs text-gray-400 hover:underline">
          Quitar
        </button>
      )}
    </div>
  );
}

function Casillas({ opciones, elegidas, onCambio }) {
  const alternar = (o) =>
    onCambio(elegidas.includes(o) ? elegidas.filter((x) => x !== o) : [...elegidas, o]);
  return (
    <div className="grid grid-cols-1 gap-x-4 gap-y-1.5 sm:grid-cols-2">
      {opciones.map((o) => (
        <label key={o} className="flex cursor-pointer items-center gap-2 text-sm text-gray-700">
          <input type="checkbox" checked={elegidas.includes(o)} onChange={() => alternar(o)} />
          {o}
        </label>
      ))}
    </div>
  );
}

/** Campos del alta de colaborador (estado en el padre, para enviarlo junto con la prioridad y los archivos). */
export default function FormAltaColaborador({ datos, onCambio, catalogos }) {
  const poner = (campo) => (valor) => onCambio({ ...datos, [campo]: valor });
  const escribir = (campo) => (e) => poner(campo)(e.target.value);
  const cedulaMal = datos.cedula.length === 10 && !cedulaValida(datos.cedula);

  return (
    <div className="space-y-5">
      <Pregunta numero={1} titulo="Nombres y apellidos" requerido>
        <input className={inputClass} value={datos.nombres} onChange={escribir("nombres")} autoComplete="off" />
      </Pregunta>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <Pregunta numero={2} titulo="Fecha de ingreso" requerido>
          <input type="date" className={inputClass} value={datos.fecha_ingreso} onChange={escribir("fecha_ingreso")} />
        </Pregunta>
        <Pregunta numero={3} titulo="Cédula del nuevo colaborador" requerido>
          <input
            className={`${inputClass} ${cedulaMal ? "border-red-400" : ""}`}
            value={datos.cedula}
            inputMode="numeric"
            maxLength={10}
            onChange={(e) => poner("cedula")(e.target.value.replace(/\D/g, ""))}
            placeholder="10 dígitos"
            autoComplete="off"
          />
          <p className={`mt-1 text-xs ${cedulaMal ? "text-red-600" : "text-gray-400"}`}>
            {cedulaMal ? "Esa cédula no es válida." : "Debe ser la cédula real de la persona."}
          </p>
        </Pregunta>
      </div>

      <Pregunta numero={4} titulo="Cargo" requerido>
        <input className={inputClass} value={datos.cargo} onChange={escribir("cargo")} autoComplete="off" />
      </Pregunta>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <Pregunta numero={5} titulo="Monitor (opcional)">
          <SiNo valor={datos.monitor} onCambio={poner("monitor")} nombre="monitor" />
        </Pregunta>
        <Pregunta numero={6} titulo="Teléfono fijo (opcional)">
          <SiNo valor={datos.telefono_fijo} onCambio={poner("telefono_fijo")} nombre="telefono" />
        </Pregunta>
      </div>

      <Pregunta numero={7} titulo="Grupo (opcional)">
        <input className={inputClass} value={datos.grupo} onChange={escribir("grupo")} autoComplete="off" />
      </Pregunta>

      <Pregunta numero={8} titulo="Listas de distribución de correo (opcional)">
        <Casillas opciones={catalogos.listas_distribucion} elegidas={datos.listas_distribucion} onCambio={poner("listas_distribucion")} />
      </Pregunta>

      <Pregunta numero={9} titulo="Aplicaciones a usar (opcional)">
        <Casillas opciones={catalogos.aplicaciones} elegidas={datos.aplicaciones} onCambio={poner("aplicaciones")} />
      </Pregunta>

      <Pregunta numero={10} titulo="Licencia SAP (opcional)">
        <div className="space-y-1.5">
          {catalogos.licencias_sap.map((l) => (
            <label key={l.nombre} className="flex cursor-pointer items-start gap-2 text-sm text-gray-700">
              <input
                type="radio"
                name="licencia"
                className="mt-1"
                checked={datos.licencia_sap === l.nombre}
                onChange={() => poner("licencia_sap")(l.nombre)}
              />
              <span>
                <strong className="font-medium">{l.nombre}:</strong> {l.ayuda}
              </span>
            </label>
          ))}
          {datos.licencia_sap && (
            <button type="button" onClick={() => poner("licencia_sap")(null)} className="text-xs text-gray-400 hover:underline">
              Quitar licencia
            </button>
          )}
        </div>
      </Pregunta>

      <Pregunta numero={11} titulo="Permisos SAP (opcional)">
        <input
          className={inputClass}
          value={datos.permisos_sap}
          onChange={escribir("permisos_sap")}
          placeholder="Si usará SAP: módulos o usuario de referencia"
        />
      </Pregunta>

      <Pregunta numero={12} titulo="Observaciones" requerido>
        <textarea
          rows={4}
          className={`${inputClass} resize-y`}
          value={datos.observaciones}
          onChange={escribir("observaciones")}
          maxLength={5000}
        />
      </Pregunta>
    </div>
  );
}
