import { Bot, CheckCircle2, Inbox, Plus, Ticket, Trophy } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { listarTickets, obtenerGamificacion, obtenerResumen } from "../../api";
import { obtenerUsuario } from "../../auth";
import { Panel, StatTile } from "../../components/charts/Charts";
import { formatoNumero } from "../../components/charts/tokens";
import EstadoBadge from "../../components/EstadoBadge";
import MinutitoPanel from "../../components/MinutitoPanel";
import { PrioridadPastilla } from "../../components/tickets/Pastillas";
import Spinner from "../../components/ui/Spinner";

export default function DashboardPage() {
  const usuario = obtenerUsuario();
  const [tickets, setTickets] = useState([]);
  const [resumen, setResumen] = useState(null);
  const [logros, setLogros] = useState(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    Promise.all([
      listarTickets().then((lista) => setTickets(lista.slice(0, 5))),
      obtenerResumen().then(setResumen),
      obtenerGamificacion(usuario.id).then(setLogros),
    ])
      .catch(() => {})
      .finally(() => setCargando(false));
  }, [usuario.id]);

  // Desde el acceso del menú («Pídele ayuda ahora») se llega con #minutito: se lleva la vista al chat.
  const { hash } = useLocation();
  useEffect(() => {
    if (hash !== "#minutito") return;
    const panel = document.getElementById("minutito");
    panel?.scrollIntoView({ block: "start" });
    panel?.querySelector("input")?.focus({ preventScroll: true });
  }, [hash]);

  const pendientes = resumen ? resumen.abiertos + resumen.en_proceso : 0;

  return (
    <div className="grid grid-cols-1 gap-4 sm:gap-6 lg:grid-cols-3">
      <div className="min-w-0 space-y-4 lg:col-span-2">
        {/* Bienvenida como lámina de plano: grafito con cuadrícula, cota y franja de obra. */}
        <section className="relative flex items-center justify-between gap-4 overflow-hidden rounded-lg bg-noche p-5 text-white shadow-[0_1px_0_rgb(0_0_0/0.2)] sm:p-6">
          <svg aria-hidden="true" className="pointer-events-none absolute inset-0 h-full w-full">
            <defs>
              <pattern id="trama-bienvenida" width="24" height="24" patternUnits="userSpaceOnUse">
                <path d="M24 0H0v24" fill="none" stroke="#fff" strokeOpacity=".05" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#trama-bienvenida)" />
          </svg>
          <span aria-hidden="true" className="franja-obra absolute inset-x-0 bottom-0 h-1.5" />
          <div className="relative min-w-0">
            <p className="mb-2 font-mono text-[10.5px] uppercase tracking-[0.16em] text-casco">
              Mesa de ayuda · {new Date().toLocaleDateString("es-EC", { weekday: "long", day: "numeric", month: "long" })}
            </p>
            <h1 className="text-[26px] font-bold leading-tight text-white sm:text-3xl">¡Hola, {usuario?.nombre?.split(" ")[0]}!</h1>
            <p className="mb-2 text-white/75">¿En qué podemos ayudarte hoy?</p>
            <p className="max-w-md text-sm text-white/60">
              Crea un ticket, revisa el estado de tus solicitudes o cuéntale tu problema a Minutito.
            </p>
            <div className="mt-5 grid grid-cols-1 gap-2 min-[420px]:flex min-[420px]:flex-wrap">
              <Link
                to="/usuario/nuevo-ticket"
                className="btn-obra inline-flex h-10 items-center justify-center gap-2 rounded-md bg-acento px-4 text-sm font-semibold text-white hover:bg-acento-600"
              >
                <Plus size={16} /> Crear ticket
              </Link>
              {/* En móvil el chat queda debajo: este atajo lleva directo a él. */}
              <a
                href="#minutito"
                className="btn-obra inline-flex h-10 items-center justify-center gap-2 rounded-md border border-white/20 bg-white/[0.06] px-4 text-sm font-semibold text-white hover:border-white/40 hover:bg-white/10 lg:hidden"
              >
                <Bot size={16} /> Hablar con Minutito
              </a>
              <Link
                to="/usuario/mis-tickets"
                className="btn-obra inline-flex h-10 items-center justify-center gap-2 rounded-md border border-white/20 bg-white/[0.06] px-4 text-sm font-semibold text-white hover:border-white/40 hover:bg-white/10"
              >
                Ver mis tickets
              </Link>
            </div>
          </div>
          <div className="group relative hidden shrink-0 sm:block">
            {/* Minutito sobre su «lote»: un pedestal con cota, como una maqueta. */}
            <div className="relative h-36 w-36 rounded-full bg-white/[0.06] p-2 ring-1 ring-white/10">
              <img
                src="/img/robot-minutito.jpg"
                alt="Minutito"
                className="anim-saludo h-full w-full rounded-full bg-white object-contain p-1.5 transition-transform duration-300 ease-[cubic-bezier(.34,1.4,.64,1)] group-hover:-translate-y-1 group-hover:-rotate-3"
              />
            </div>
          </div>
        </section>

        <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
          <Link to="/usuario/mis-tickets" className="block rounded-md transition-transform duration-200 hover:-translate-y-0.5">
            <StatTile
              icono={Ticket}
              tono={0}
              titulo="Mis tickets"
              valor={resumen ? formatoNumero(resumen.total) : "—"}
              detalle={resumen ? `${resumen.resueltos} resueltos` : undefined}
              // Sin tickets en los últimos días la línea quedaría plana: no se muestra.
              tendencia={resumen?.ultimos_dias.some((d) => d.total) ? resumen.ultimos_dias.map((d) => d.total) : undefined}
            />
          </Link>
          <Link to="/usuario/mis-tickets" className="block rounded-md transition-transform duration-200 hover:-translate-y-0.5">
            <StatTile
              icono={Inbox}
              tono={1}
              titulo="Pendientes"
              valor={resumen ? formatoNumero(pendientes) : "—"}
              detalle={resumen ? `${resumen.en_proceso} en proceso` : undefined}
            />
          </Link>
          <Link to="/usuario/historico" className="block rounded-md transition-transform duration-200 hover:-translate-y-0.5">
            <StatTile
              icono={CheckCircle2}
              tono={2}
              titulo="Resueltos por Minutito"
              valor={resumen ? formatoNumero(resumen.resueltos_por_minutito) : "—"}
              detalle="Consultas resueltas sin ticket"
            />
          </Link>
          <Link to="/usuario/logros" className="block rounded-md transition-transform duration-200 hover:-translate-y-0.5">
            <StatTile
              icono={Trophy}
              tono={3}
              titulo="Mis puntos"
              valor={logros ? formatoNumero(logros.puntos) : "—"}
              detalle={logros?.nivel}
            />
          </Link>
        </div>

        <Panel relleno="p-0" className="overflow-hidden">
          <div className="flex items-center justify-between px-4 pb-3 pt-4 sm:px-5">
            <h2 className="text-sm font-semibold text-noche">Mis últimos tickets</h2>
            <Link to="/usuario/mis-tickets" className="text-sm text-acento hover:underline">
              Ver todos →
            </Link>
          </div>

          {cargando && (
            <div className="px-5 pb-5">
              <Spinner size="sm" />
            </div>
          )}
          {!cargando && tickets.length === 0 && (
            <p className="px-5 pb-5 text-sm text-gray-500">
              Todavía no tienes tickets.{" "}
              <Link to="/usuario/nuevo-ticket" className="font-medium text-noche underline">
                Crea el primero
              </Link>{" "}
              o cuéntale tu problema a Minutito.
            </p>
          )}
          {!cargando && tickets.length > 0 && (
            <ul className="divide-y divide-gray-100 border-t border-gray-100 sm:hidden">
              {tickets.map((t) => (
                <li key={t.id}>
                  <Link to={`/usuario/tickets/${t.id}`} className="block px-4 py-3 hover:bg-marfil">
                    <div className="mb-1 flex items-center justify-between gap-2">
                      <span className="text-xs font-medium text-acento">#{t.id}</span>
                      <EstadoBadge estado={t.estado} />
                    </div>
                    <div className="line-clamp-2 text-sm text-gray-800">{t.texto}</div>
                    <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
                      <span className="truncate">{t.categoria || t.categoria_predicha || "Sin categoría"}</span>
                      <PrioridadPastilla prioridad={t.prioridad} />
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
          {!cargando && tickets.length > 0 && (
            <div className="hidden overflow-x-auto sm:block">
              <table className="w-full min-w-[520px] text-left text-sm">
                <thead className="bg-marfil text-xs text-gray-500">
                  <tr>
                    <th className="px-5 py-2 font-medium">#</th>
                    <th className="px-3 py-2 font-medium">Descripción</th>
                    <th className="px-3 py-2 font-medium">Categoría</th>
                    <th className="px-3 py-2 font-medium">Prioridad</th>
                    <th className="px-3 py-2 font-medium">Estado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {tickets.map((t) => (
                    <tr key={t.id} className="hover:bg-marfil">
                      <td className="px-5 py-2.5">
                        <Link to={`/usuario/tickets/${t.id}`} className="font-medium text-acento hover:underline">
                          {t.id}
                        </Link>
                      </td>
                      <td className="max-w-[240px] truncate px-3 py-2.5 text-gray-700">{t.texto}</td>
                      <td className="whitespace-nowrap px-3 py-2.5 text-gray-600">
                        {t.categoria || t.categoria_predicha || "—"}
                      </td>
                      <td className="px-3 py-2.5">
                        <PrioridadPastilla prioridad={t.prioridad} />
                      </td>
                      <td className="px-3 py-2.5">
                        <EstadoBadge estado={t.estado} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      </div>

      <div id="minutito" className="scroll-mt-20 lg:col-span-1">
        <div className="h-[min(560px,calc(100dvh-6rem))] lg:sticky lg:top-22 lg:h-[calc(100dvh-7rem)]">
          <MinutitoPanel />
        </div>
      </div>
    </div>
  );
}
