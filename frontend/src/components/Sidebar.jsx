import { X } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { Marca } from "./Logo";
import { BuscadorTickets } from "./TopBar";

/**
 * Menú lateral. En escritorio (lg) queda fijo a la izquierda; en tablet y móvil es un
 * cajón que se abre con el botón de menú de la barra superior y se cierra al navegar,
 * al tocar fuera o con Escape.
 */
export default function Sidebar({
  navItems,
  footer,
  dark = false,
  rutaBusqueda,
  abierto = false,
  onCerrar,
  children,
}) {
  const location = useLocation();

  const tema = dark
    ? "bg-grafito text-white lg:border-r lg:border-black/40"
    : "border-r border-linea bg-superficie";
  const cajon = abierto
    ? "max-lg:translate-x-0"
    : "max-lg:invisible max-lg:-translate-x-full";

  return (
    <>
      {abierto && (
        <button
          type="button"
          aria-label="Cerrar menú"
          onClick={onCerrar}
          className="fixed inset-0 z-40 bg-grafito/50 lg:hidden"
        />
      )}

      <aside
        id="menu-principal"
        aria-label="Menú principal"
        // Cualquier enlace del menú (secciones, acceso a Minutito) cierra el cajón.
        onClick={(e) => e.target.closest("a") && onCerrar?.()}
        className={`flex shrink-0 flex-col overflow-y-auto ${tema} ${cajon} max-lg:fixed max-lg:inset-y-0 max-lg:left-0 max-lg:z-50 max-lg:w-72 max-lg:max-w-[85vw] max-lg:shadow-2xl max-lg:transition-[transform,visibility] max-lg:duration-200 lg:sticky lg:top-16 lg:h-[calc(100dvh-4rem)] ${
          dark ? "lg:w-60" : "lg:w-56"
        }`}
      >
        <div
          className={`flex items-center justify-between gap-3 border-b px-4 py-3 lg:hidden ${
            dark ? "border-white/10" : "border-linea"
          }`}
        >
          <Marca oscuro={dark} size="h-8 w-8" />
          <button
            type="button"
            onClick={onCerrar}
            aria-label="Cerrar menú"
            className={`rounded-md p-1.5 ${
              dark ? "text-noche-300 hover:bg-white/10 hover:text-white" : "text-gray-500 hover:bg-marfil"
            }`}
          >
            <X size={20} />
          </button>
        </div>

        {rutaBusqueda && (
          <div className="px-3 pt-4 md:hidden">
            <BuscadorTickets rutaBusqueda={rutaBusqueda} oscuro={dark} onBuscar={onCerrar} />
          </div>
        )}

        <nav className="flex-1 space-y-0.5 px-3 py-4" aria-label="Secciones">
          <p
            aria-hidden="true"
            className={`mb-2 px-3 font-mono text-[10px] uppercase tracking-[0.16em] ${
              dark ? "text-noche-300/70" : "text-gray-400"
            }`}
          >
            Secciones
          </p>
          {navItems.map((item) => {
            if (item.disabled) {
              return (
                <div
                  key={item.label}
                  className={`flex cursor-not-allowed items-center justify-between rounded-md px-3 py-2 text-sm ${
                    dark ? "text-noche-300/60" : "text-gray-300"
                  }`}
                  title="Próximamente"
                >
                  <span className="flex items-center gap-2.5">
                    <item.icon size={17} aria-hidden="true" />
                    {item.label}
                  </span>
                  <span
                    className={`rounded px-1.5 py-0.5 font-mono text-[10px] ${
                      dark ? "bg-white/5 text-noche-300" : "bg-gray-100 text-gray-400"
                    }`}
                  >
                    Próx.
                  </span>
                </div>
              );
            }

            const activo = item.isActive
              ? item.isActive(location.pathname)
              : location.pathname === item.to;
            const activoCls = dark
              ? "bg-white/[0.07] font-semibold text-white shadow-[inset_0_0_0_1px_rgb(255_255_255/0.06)]"
              : "bg-acento-50 font-semibold text-noche";
            const inactivoCls = dark
              ? "text-noche-300 hover:bg-white/[0.04] hover:text-white"
              : "text-gray-600 hover:bg-marfil hover:text-noche";

            return (
              <span key={item.label} className="relative block">
                <Link
                  to={item.to}
                  aria-current={activo ? "page" : undefined}
                  className={`group/nav relative flex items-center gap-2.5 rounded-md px-3 py-2.5 text-sm transition-colors duration-150 lg:py-2 ${
                    activo ? activoCls : inactivoCls
                  }`}
                >
                  {/* Viga de acento: la sección activa se reconoce también por forma, no solo por color.
                      Crece desde el centro como una columna recién vaciada. */}
                  {activo && (
                    <span
                      aria-hidden="true"
                      className={`viga absolute inset-y-1 left-0 w-[3px] rounded-r-[1px] ${dark ? "bg-casco" : "bg-acento"}`}
                    />
                  )}
                  <item.icon
                    size={17}
                    aria-hidden="true"
                    className={`shrink-0 transition-transform duration-200 ease-[cubic-bezier(.34,1.4,.64,1)] group-hover/nav:-translate-y-0.5 ${
                      activo ? (dark ? "text-casco" : "text-acento") : ""
                    }`}
                  />
                  <span className="cota">{item.label}</span>
                </Link>
                {item.badge != null && (
                  <span
                    className={`absolute right-3 top-1/2 -translate-y-1/2 rounded px-1.5 py-0.5 font-mono text-[10px] font-medium ${
                      dark ? "bg-white/10 text-white" : "bg-gray-200 text-gray-700"
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </span>
            );
          })}
        </nav>

        {children}

        {footer && (
          <p
            className={`border-t px-4 py-3 text-center font-mono text-[10px] uppercase leading-relaxed tracking-[0.08em] ${
              dark ? "border-white/10 text-noche-300/80" : "border-linea text-gray-400"
            }`}
          >
            {footer}
          </p>
        )}
      </aside>
    </>
  );
}
