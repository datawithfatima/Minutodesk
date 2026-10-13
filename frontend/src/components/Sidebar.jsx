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
    ? "bg-noche text-white"
    : "border-r border-linea bg-white";
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
          className="fixed inset-0 z-40 bg-noche/50 lg:hidden"
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
            className={`rounded-lg p-1.5 ${
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
          {navItems.map((item) => {
            if (item.disabled) {
              return (
                <div
                  key={item.label}
                  className={`flex cursor-not-allowed items-center justify-between rounded-lg px-3 py-2 text-sm ${
                    dark ? "text-noche-300/60" : "text-gray-300"
                  }`}
                  title="Próximamente"
                >
                  <span className="flex items-center gap-2.5">
                    <item.icon size={17} aria-hidden="true" />
                    {item.label}
                  </span>
                  <span
                    className={`rounded-full px-1.5 py-0.5 text-[10px] ${
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
              ? "bg-white/[0.08] font-medium text-white"
              : "bg-acento-50 font-medium text-noche";
            const inactivoCls = dark
              ? "text-noche-300 hover:bg-white/[0.05] hover:text-white"
              : "text-gray-600 hover:bg-marfil hover:text-noche";

            return (
              <span key={item.label} className="relative block">
                <Link
                  to={item.to}
                  aria-current={activo ? "page" : undefined}
                  className={`relative flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm transition-colors duration-150 lg:py-2 ${
                    activo ? activoCls : inactivoCls
                  }`}
                >
                  {/* Barra de acento: la sección activa se reconoce también por forma, no solo por color. */}
                  {activo && (
                    <span
                      aria-hidden="true"
                      className="absolute inset-y-1.5 left-0 w-[3px] rounded-r-full bg-acento"
                    />
                  )}
                  <item.icon size={17} aria-hidden="true" className={activo ? "text-white" : ""} />
                  {item.label}
                </Link>
                {item.badge != null && (
                  <span
                    className={`absolute right-3 top-1/2 -translate-y-1/2 rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
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
            className={`border-t px-4 py-3 text-center text-[11px] leading-relaxed ${
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
