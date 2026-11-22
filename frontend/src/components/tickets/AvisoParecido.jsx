import { ArrowRight, Copy } from "lucide-react";
import { Link } from "react-router-dom";
import EstadoBadge from "../EstadoBadge";

/*
 * «Ya tienes un ticket abierto parecido»: aparece al pulsar «Crear ticket» si la persona
 * tiene uno abierto casi igual. Lo principal es ir a ese ticket; si de verdad es otro
 * problema, puede crear el nuevo igual (enlace discreto). Solo usa colores con token, así
 * que se ve bien en el tema oscuro.
 */
export default function AvisoParecido({ parecidos, onCrearIgual, enviando = false }) {
  if (!parecidos?.length) return null;
  const uno = parecidos.length === 1;
  return (
    <div
      role="alertdialog"
      aria-labelledby="aviso-parecido-titulo"
      className="anim-desplegar relative overflow-hidden rounded-md border border-amber-200 bg-amber-50 pl-1.5 text-sm text-amber-900"
    >
      <span aria-hidden="true" className="franja-obra absolute inset-y-0 left-0 w-1.5" />
      <div className="px-4 py-3.5">
        <div className="flex items-start gap-2.5">
          <Copy size={17} aria-hidden="true" className="mt-0.5 shrink-0 opacity-80" />
          <div className="min-w-0">
            <p id="aviso-parecido-titulo" className="font-semibold">
              {uno ? `Ya tienes el ticket #${parecidos[0].id} abierto con algo muy parecido` : "Ya tienes tickets abiertos muy parecidos"}
            </p>
            <p className="mt-0.5 text-[13px] text-amber-800">
              Continúa en {uno ? "ese ticket" : "el que corresponda"}.
            </p>
          </div>
        </div>

        <ul className="mt-3 space-y-2">
          {parecidos.map((p) => (
            <li key={p.id} className="rounded-md border border-amber-200 bg-superficie p-2.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="flex items-center gap-2">
                  <span className="font-mono text-xs font-semibold text-noche">#{p.id}</span>
                  <EstadoBadge estado={p.estado} />
                </span>
                <span className="font-mono text-[10.5px] text-gray-500">{new Date(p.creado_en).toLocaleDateString()}</span>
              </div>
              <p className="mt-1 line-clamp-2 text-[13px] text-gray-700">{p.texto}</p>
              <Link
                to={`/usuario/tickets/${p.id}`}
                className="btn-obra mt-2 inline-flex h-8 items-center gap-1.5 rounded-md bg-grafito px-3 text-xs font-semibold text-white hover:bg-grafito-700"
              >
                Ir al ticket #{p.id} <ArrowRight size={14} aria-hidden="true" />
              </Link>
            </li>
          ))}
        </ul>

        <button
          type="button"
          onClick={onCrearIgual}
          disabled={enviando}
          className="mt-3 text-xs font-medium text-amber-800 underline decoration-dotted underline-offset-2 hover:text-amber-900 disabled:opacity-40"
        >
          No, es un problema distinto: crear el ticket nuevo
        </button>
      </div>
    </div>
  );
}
