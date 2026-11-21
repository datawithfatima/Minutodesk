import { HardHat, Lock, LogOut, UserCheck, UserRound } from "lucide-react";
import { useState } from "react";
import { inputClass, labelClass } from "../ui/formStyles";
import Button from "../ui/Button";
import Spinner from "../ui/Spinner";
import Selector from "../ui/Selector";

const MIN_DETALLE = 5;

/** Tomado: tiene dueño. Sugerido: la asignación automática lo propone, cualquiera lo toma. */
export function situacionAtencion(ticket, yoId) {
  if (ticket.tomado_en && ticket.tecnico_id) return ticket.tecnico_id === yoId ? "mio" : "ajeno";
  return ticket.tecnico_id ? "sugerido" : "libre";
}

/** Pastilla corta para listas y tablas: «Atendido por X», «Sugerido: X» o «Libre». */
export function AtiendePastilla({ ticket, nombre, yoId }) {
  const situacion = situacionAtencion(ticket, yoId);
  const cerrado = ticket.estado === "resuelto" || ticket.estado === "cancelado";
  if (situacion === "mio" || situacion === "ajeno") {
    const mio = situacion === "mio";
    return (
      <span
        title={`${cerrado ? "Lo atendió" : "Atendido por"} ${nombre ?? "otro técnico"}`}
        className={`inline-flex max-w-full items-center gap-1 rounded px-1.5 py-0.5 text-xs font-medium ring-1 ring-inset ${
          mio ? "bg-acento-50 text-acento-600 ring-acento-100" : "bg-gray-100 text-gray-700 ring-gray-200"
        }`}
      >
        <HardHat size={12} aria-hidden="true" className="shrink-0" />
        <span className="truncate">{mio ? "Tú" : nombre ?? "Otro técnico"}</span>
      </span>
    );
  }
  if (cerrado) return <span className="text-xs text-gray-400">—</span>;
  if (situacion === "sugerido" && ticket.estado !== "abierto") {
    // Tickets en proceso de antes de existir «Tomar»: tienen técnico, pero no bloqueado.
    return <span className="block truncate text-xs text-gray-600">{nombre ?? "—"}</span>;
  }
  if (situacion === "sugerido") {
    return (
      <span title="Sugerido por sistema: aún nadie lo toma" className="inline-flex max-w-full items-center gap-1 text-xs text-gray-500">
        <UserRound size={12} aria-hidden="true" className="shrink-0" />
        <span className="truncate">{ticket.tecnico_id === yoId ? "Sugerido a ti" : `Sugerido: ${nombre ?? "—"}`}</span>
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium text-amber-800 ring-1 ring-inset ring-amber-200 bg-amber-50">
      Libre
    </span>
  );
}

/**
 * Bloque de «Gestión»: quién atiende, y Tomar / Liberar. Si lo atiende otro técnico,
 * explica que solo esa persona o un administrador pueden cambiarlo.
 */
export function PanelAtencion({ ticket, tecnico, yoId, esAdmin, motivos, deshabilitado, onTomar, onLiberar }) {
  const [liberando, setLiberando] = useState(false);
  const [motivo, setMotivo] = useState("");
  const [detalle, setDetalle] = useState("");
  const [enviando, setEnviando] = useState(false);
  const situacion = situacionAtencion(ticket, yoId);
  const desde = ticket.tomado_en ? new Date(ticket.tomado_en).toLocaleString() : null;

  async function confirmar(e) {
    e.preventDefault();
    setEnviando(true);
    const ok = await onLiberar(motivo, detalle.trim());
    setEnviando(false);
    if (ok) {
      setLiberando(false);
      setMotivo("");
      setDetalle("");
    }
  }

  if (situacion === "libre" || situacion === "sugerido") {
    return (
      <div className="space-y-2">
        <p className="text-xs text-gray-500">
          {situacion === "sugerido" && ticket.estado !== "abierto" ? (
            <>
              Lo lleva <strong className="font-medium text-noche">{tecnico?.nombre ?? "otro técnico"}</strong>, pero sin
              haberlo tomado (es anterior a esta función).
            </>
          ) : situacion === "sugerido" ? (
            <>
              Sugerido a <strong className="font-medium text-noche">{ticket.tecnico_id === yoId ? "ti" : tecnico?.nombre ?? "otro técnico"}</strong>{" "}
              según el sistema, pero aún nadie lo ha tomado.
            </>
          ) : (
            <>Nadie atiende este ticket todavía.</>
          )}{" "}
          Al tomarlo o responder primero queda a tu nombre.
        </p>
        <Button variant="primary" onClick={onTomar} disabled={deshabilitado} className="w-full">
          <UserCheck size={16} aria-hidden="true" /> Tomar ticket
        </Button>
      </div>
    );
  }

  const mio = situacion === "mio";
  const puedeLiberar = mio || esAdmin;
  return (
    <div className="space-y-2">
      <div
        className={`flex items-start gap-3 rounded-md border p-3 ${
          mio ? "border-acento-100 bg-acento-50" : "border-linea bg-gray-50"
        }`}
      >
        <span
          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-md ${
            mio ? "bg-acento text-white" : "bg-grafito text-casco"
          }`}
        >
          {mio ? <HardHat size={18} aria-hidden="true" /> : <Lock size={16} aria-hidden="true" />}
        </span>
        <div className="min-w-0 text-sm">
          <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-gray-500">Atendido por</div>
          <div className="truncate font-semibold text-noche">{mio ? `Ti (${tecnico?.nombre ?? ""})` : tecnico?.nombre ?? "Otro técnico"}</div>
          {desde && <div className="text-xs text-gray-500">Desde {desde}</div>}
        </div>
      </div>
      {!mio && !esAdmin && (
        <p className="text-xs text-gray-500">
          Solo {tecnico?.nombre ?? "quien lo atiende"} o un administrador pueden cambiar este ticket o escribirle al solicitante.
        </p>
      )}
      {!mio && esAdmin && (
        <p className="text-xs text-gray-500">Como administrador puedes reasignarlo abajo o liberarlo.</p>
      )}

      {puedeLiberar && !liberando && (
        <Button variant="outlineSecondary" size="sm" className="w-full" disabled={deshabilitado} onClick={() => setLiberando(true)}>
          <LogOut size={14} aria-hidden="true" /> Liberar ticket
        </Button>
      )}
      {puedeLiberar && liberando && (
        <form onSubmit={confirmar} className="space-y-2 rounded-lg border border-dashed border-linea bg-gray-50 p-3">
          <div>
            <label htmlFor="liberar-motivo" className={labelClass}>
              Motivo
            </label>
            <Selector id="liberar-motivo" className={inputClass} value={motivo} onChange={(e) => setMotivo(e.target.value)} autoFocus>
              <option value="">Elige un motivo</option>
              {motivos.map((m) => (
                <option key={m.clave} value={m.clave}>
                  {m.titulo}
                </option>
              ))}
            </Selector>
          </div>
          <div>
            <label htmlFor="liberar-detalle" className={labelClass}>
              Detalle
            </label>
            <textarea
              id="liberar-detalle"
              rows={3}
              maxLength={500}
              value={detalle}
              onChange={(e) => setDetalle(e.target.value)}
              placeholder="Ej.: es un tema de licencias de Office, no de Power BI."
              className={`${inputClass} resize-y`}
            />
            <p className="mt-1 text-xs text-gray-500">
              Vuelve a «Nuevo» y se sugiere a otro técnico del sistema. Queda en el historial y en la bitácora.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="submit" size="sm" disabled={!motivo || detalle.trim().length < MIN_DETALLE || enviando}>
              {enviando ? <Spinner size="sm" /> : "Confirmar liberación"}
            </Button>
            <Button type="button" variant="outlineSecondary" size="sm" onClick={() => setLiberando(false)}>
              Volver
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
