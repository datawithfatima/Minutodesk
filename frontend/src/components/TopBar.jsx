import { Bell, Search } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ETIQUETA_ROL } from "../texto";
import Logo from "./Logo";

export default function TopBar({ usuario, rutaBusqueda }) {
  const [busqueda, setBusqueda] = useState("");
  const navegar = useNavigate();

  const iniciales = (usuario?.nombre || "")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0])
    .join("")
    .toUpperCase();

  function buscar(e) {
    e.preventDefault();
    const texto = busqueda.trim();
    navegar(texto ? `${rutaBusqueda}?q=${encodeURIComponent(texto)}` : rutaBusqueda);
  }

  return (
    <header className="flex items-center justify-between gap-4 border-b border-gray-200 bg-white px-6 py-3">
      <div className="flex shrink-0 items-center gap-3">
        <Logo size="h-9 w-9" />
        <div>
          <div className="text-base font-bold leading-tight text-gray-900">MinutoDesk</div>
          <div className="text-xs text-gray-400">Tu soporte, más cerca</div>
        </div>
      </div>

      <form
        onSubmit={buscar}
        className="hidden w-full max-w-md flex-1 items-center gap-2 rounded-full border border-gray-200 bg-gray-50 px-4 py-2 text-sm text-gray-500 md:flex"
      >
        <Search size={16} className="shrink-0 text-gray-400" />
        <input
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          placeholder="Buscar tickets..."
          className="w-full bg-transparent outline-none placeholder:text-gray-400"
        />
      </form>

      <div className="flex shrink-0 items-center gap-4">
        <Bell size={18} className="text-gray-400" />
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gray-900 text-xs font-semibold text-white">
            {iniciales}
          </div>
          <div>
            <div className="text-sm font-medium leading-tight text-gray-900">{usuario?.nombre}</div>
            <div className="text-xs text-gray-400">{ETIQUETA_ROL[usuario?.rol] || ""}</div>
          </div>
        </div>
      </div>
    </header>
  );
}
