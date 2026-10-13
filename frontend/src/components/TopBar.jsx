import { Menu, Search } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Marca } from "./Logo";
import MenuUsuario from "./MenuUsuario";

/** Caja de búsqueda de tickets: en la barra superior (tablet/escritorio) y en el menú (móvil). */
export function BuscadorTickets({ rutaBusqueda, oscuro = false, onBuscar, className = "" }) {
  const [busqueda, setBusqueda] = useState("");
  const navegar = useNavigate();

  function buscar(e) {
    e.preventDefault();
    const texto = busqueda.trim();
    navegar(texto ? `${rutaBusqueda}?q=${encodeURIComponent(texto)}` : rutaBusqueda);
    onBuscar?.();
  }

  return (
    <form
      onSubmit={buscar}
      role="search"
      className={`flex h-10 items-center gap-2 rounded-lg border px-3 text-sm transition-colors duration-150 ${
        oscuro
          ? "border-white/10 bg-white/[0.06] text-white focus-within:border-acento"
          : "border-linea bg-marfil text-noche focus-within:border-acento focus-within:bg-white focus-within:ring-3 focus-within:ring-acento/15"
      } ${className}`}
    >
      <Search size={16} aria-hidden="true" className={`shrink-0 ${oscuro ? "text-noche-300" : "text-gray-400"}`} />
      <input
        value={busqueda}
        onChange={(e) => setBusqueda(e.target.value)}
        placeholder="Buscar tickets…"
        aria-label="Buscar tickets"
        className={`w-full min-w-0 bg-transparent text-base outline-none focus-visible:outline-none md:text-sm ${
          oscuro ? "placeholder:text-noche-300" : "placeholder:text-gray-400"
        }`}
      />
    </form>
  );
}

export default function TopBar({ usuario, rutaBusqueda, menuAbierto, onAbrirMenu, onLogout }) {
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-3 border-b border-linea bg-white px-3 sm:gap-4 sm:px-6">
      <div className="flex min-w-0 shrink-0 items-center gap-1.5 sm:gap-3">
        <button
          type="button"
          onClick={onAbrirMenu}
          aria-label="Abrir menú"
          aria-controls="menu-principal"
          aria-expanded={menuAbierto}
          className="rounded-lg p-2 text-gray-600 hover:bg-marfil lg:hidden"
        >
          <Menu size={22} aria-hidden="true" />
        </button>
        <span className="sm:hidden">
          <Marca size="h-8 w-8" />
        </span>
        <span className="hidden sm:inline-flex">
          <Marca subtitulo />
        </span>
      </div>

      <BuscadorTickets rutaBusqueda={rutaBusqueda} className="hidden w-full max-w-md flex-1 md:flex" />

      <MenuUsuario usuario={usuario} onLogout={onLogout} />
    </header>
  );
}
