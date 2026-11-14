import { CheckCircle2, Pause, Play, TimerOff, TimerReset } from "lucide-react";
import { useEffect, useState } from "react";
import { ESTADO_AVISO, ESTADO_OK, GRIS_SIN_DATO } from "../charts/tokens";
import Button from "../ui/Button";
import Spinner from "../ui/Spinner";
import { inputClass, labelClass } from "../ui/formStyles";
import { Pastilla } from "./Pastillas";

/*
 * Temporizador del plazo de atención (SLA). El backend calcula los segundos; aquí solo se
 * muestran y, mientras el reloj corre, se descuentan en vivo desde que llegaron.
 */

const ROJO = "#d64545";
const CORRIENDO = new Set(["en_tiempo", "por_vencer", "vencido"]);

const ETIQUETA = {
  en_tiempo: "En tiempo",
  por_vencer: "Por vencer",
  vencido: "Vencido",
  pausado: "En pausa",
  cumplido: "A tiempo",
  incumplido: "Fuera de plazo",
};

const COLOR = {
  en_tiempo: ESTADO_OK,
  por_vencer: ESTADO_AVISO,
  vencido: ROJO,
  pausado: GRIS_SIN_DATO,
  cumplido: ESTADO_OK,
  incumplido: ROJO,
};

/** «3 d 04 h», «5 h 12 min» o «08:45» según cuánto falte (siempre en positivo). */
export function formatearTiempo(segundos) {
  const s = Math.abs(Math.round(segundos));
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  const seg = s % 60;
  if (d > 0) return `${d} d ${String(h).padStart(2, "0")} h`;
  if (h > 0) return `${h} h ${String(m).padStart(2, "0")} min`;
  return `${String(m).padStart(2, "0")}:${String(seg).padStart(2, "0")}`;
}

function formatearCorto(segundos) {
  const s = Math.abs(Math.round(segundos));
  if (s >= 86400) return `${Math.floor(s / 86400)} d`;
  if (s >= 3600) return `${Math.floor(s / 3600)} h`;
  return `${Math.max(1, Math.floor(s / 60))} min`;
}

/** Descuenta segundos en vivo mientras el reloj corre; se reinicia cuando llega un sla nuevo. */
function useRestante(sla) {
  const [restante, setRestante] = useState(sla?.restante_segundos ?? 0);
  useEffect(() => {
    if (!sla) return undefined;
    setRestante(sla.restante_segundos);
    if (!CORRIENDO.has(sla.estado)) return undefined;
    const desde = Date.now();
    const id = setInterval(() => {
      setRestante(sla.restante_segundos - Math.floor((Date.now() - desde) / 1000));
    }, 1000);
    return () => clearInterval(id);
  }, [sla]);
  return restante;
}

/** Pastilla corta para listas y tarjetas. */
export function SlaPastilla({ sla }) {
  if (!sla) return null;
  const texto =
    sla.estado === "en_tiempo" || sla.estado === "por_vencer"
      ? `${formatearCorto(sla.restante_segundos)} de plazo`
      : sla.estado === "vencido"
        ? `Vencido · ${formatearCorto(sla.restante_segundos)}`
        : ETIQUETA[sla.estado];
  return <Pastilla texto={texto} color={COLOR[sla.estado]} />;
}

/** Temporizador grande para la cabecera grafito de la ficha (usuario y técnico). */
export function TemporizadorSla({ sla, className = "" }) {
  const restante = useRestante(sla);
  if (!sla) return null;
  const color = COLOR[sla.estado];
  const pct = Math.min(100, Math.max(0, sla.porcentaje));
  const cerrado = sla.estado === "cumplido" || sla.estado === "incumplido";
  const pausado = sla.estado === "pausado";
  const vencidoAhora = restante <= 0;

  const titulo = cerrado
    ? sla.vencido
      ? `Se pasó ${formatearTiempo(sla.restante_segundos)} del plazo`
      : `Resuelto con ${formatearTiempo(sla.restante_segundos)} de margen`
    : pausado
      ? `${formatearTiempo(sla.restante_segundos)} ${sla.vencido ? "de retraso" : "restantes"}, en pausa`
      : vencidoAhora
        ? `${formatearTiempo(restante)} de retraso`
        : `${formatearTiempo(restante)} restantes`;

  const Icono = cerrado ? (sla.vencido ? TimerOff : CheckCircle2) : pausado ? Pause : TimerReset;

  return (
    <div
      className={`rounded-md border border-white/15 bg-white/[0.05] px-3 py-2.5 ${className}`}
      role="timer"
      aria-live="off"
      aria-label={`Plazo de atención: ${titulo}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-casco">
          Plazo de atención · {sla.dias} {sla.dias === 1 ? "día" : "días"}
        </span>
        <span
          className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] font-semibold"
          style={{ background: `${color}33`, color: "#fff" }}
        >
          <span className="h-1.5 w-1.5 rounded-[1px]" style={{ background: color }} />
          {ETIQUETA[sla.estado]}
        </span>
      </div>
      <div className="mt-1 flex items-center gap-2">
        <Icono size={18} aria-hidden="true" className={pausado ? "text-white/60" : "text-white"} />
        <span className="font-mono text-xl font-bold tabular-nums leading-tight text-white sm:text-2xl">{titulo}</span>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-[2px] bg-white/10">
        <div
          className={`h-full rounded-[2px] transition-[width] duration-700 ${pausado ? "franja-obra" : ""}`}
          style={{ width: `${pct}%`, background: pausado ? undefined : color }}
        />
      </div>
      <div className="mt-1.5 flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-[11px] text-white/70">
        <span>{sla.porcentaje}% del plazo consumido</span>
        {sla.vence_en && <span>Vence el {new Date(sla.vence_en).toLocaleString()}</span>}
      </div>
      {sla.pausa_actual && (
        <p className="mt-2 rounded border border-dashed border-white/20 bg-white/[0.04] px-2.5 py-1.5 text-xs text-white/85">
          <strong className="font-semibold text-white">Motivo de la pausa:</strong> {sla.pausa_actual.motivo_titulo}
          {sla.pausa_actual.detalle && <> · {sla.pausa_actual.detalle}</>}
          <span className="block text-white/60">
            Desde el {new Date(sla.pausa_actual.inicio).toLocaleString()}
            {sla.pausa_actual.automatica ? " · se reanuda sola al responder la aprobación" : ` · ${sla.pausa_actual.iniciada_por}`}
          </span>
        </p>
      )}
    </div>
  );
}

const MIN_DETALLE = 5;

/** Controles del personal en Gestión: pausar con motivo, o reanudar. */
export function PanelPausaSla({ sla, motivos, deshabilitado, onPausar, onReanudar }) {
  const [abierto, setAbierto] = useState(false);
  const [motivo, setMotivo] = useState("");
  const [detalle, setDetalle] = useState("");
  const [enviando, setEnviando] = useState(false);
  if (!sla) return null;

  if (sla.pausa_actual) {
    const automatica = sla.pausa_actual.automatica;
    return (
      <div className="space-y-2">
        <p className="text-xs text-gray-500">
          El plazo está en pausa: <strong className="font-medium text-noche">{sla.pausa_actual.motivo_titulo}</strong>.
          {automatica ? " Se reanuda solo cuando respondan la aprobación." : ""}
        </p>
        <Button
          variant="outlineSecondary"
          size="sm"
          className="w-full"
          disabled={deshabilitado || automatica}
          onClick={onReanudar}
        >
          <Play size={14} aria-hidden="true" /> Reanudar el plazo
        </Button>
      </div>
    );
  }

  if (!abierto) {
    return (
      <Button variant="outlineSecondary" size="sm" className="w-full" disabled={deshabilitado} onClick={() => setAbierto(true)}>
        <Pause size={14} aria-hidden="true" /> Pausar el plazo
      </Button>
    );
  }

  async function confirmar(e) {
    e.preventDefault();
    setEnviando(true);
    const ok = await onPausar(motivo, detalle.trim());
    setEnviando(false);
    if (ok) {
      setAbierto(false);
      setMotivo("");
      setDetalle("");
    }
  }

  const valido = motivo && detalle.trim().length >= MIN_DETALLE;
  return (
    <form onSubmit={confirmar} className="space-y-2 rounded-lg border border-dashed border-linea bg-gray-50 p-3">
      <div>
        <label htmlFor="pausa-motivo" className={labelClass}>
          Motivo de la pausa
        </label>
        <select id="pausa-motivo" className={inputClass} value={motivo} onChange={(e) => setMotivo(e.target.value)} autoFocus>
          <option value="">Elige un motivo</option>
          {motivos.map((m) => (
            <option key={m.clave} value={m.clave}>
              {m.titulo}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="pausa-detalle" className={labelClass}>
          Detalle
        </label>
        <textarea
          id="pausa-detalle"
          rows={3}
          maxLength={500}
          value={detalle}
          onChange={(e) => setDetalle(e.target.value)}
          placeholder="Ej.: esperamos el repuesto del proveedor, llega el lunes."
          className={`${inputClass} resize-y`}
        />
        <p className="mt-1 text-xs text-gray-500">El usuario verá el motivo en su ticket y recibirá un correo.</p>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button type="submit" size="sm" disabled={!valido || enviando}>
          {enviando ? <Spinner size="sm" /> : "Confirmar pausa"}
        </Button>
        <Button type="button" variant="outlineSecondary" size="sm" onClick={() => setAbierto(false)}>
          Volver
        </Button>
      </div>
    </form>
  );
}
