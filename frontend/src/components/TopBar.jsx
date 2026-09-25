import { Bell, Search } from "lucide-react";
import Logo from "./Logo";

export default function TopBar({ usuario, rolLabel }) {
  const iniciales = (usuario?.nombre || "")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0])
    .join("")
    .toUpperCase();

  return (
    <header className="flex items-center justify-between gap-4 border-b border-gray-200 bg-white px-6 py-3">
      <div className="flex shrink-0 items-center gap-3">
        <Logo size="h-9 w-9" />
        <div>
          <div className="text-base font-bold leading-tight text-gray-900">MinutoDesk</div>
          <div className="text-xs text-gray-400">Tu soporte, más cerca</div>
        </div>
      </div>

      <div className="hidden flex-1 justify-center md:flex">
        <div className="flex w-full max-w-md items-center gap-2 rounded-full border border-gray-200 bg-gray-50 px-4 py-2 text-sm text-gray-400">
          <Search size={16} />
          <span title="Próximamente">Buscar en la base de conocimiento...</span>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-4">
        <Bell size={18} className="text-gray-400" />
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gray-900 text-xs font-semibold text-white">
            {iniciales}
          </div>
          <div>
            <div className="text-sm font-medium leading-tight text-gray-900">{usuario?.nombre}</div>
            <div className="text-xs text-gray-400">{rolLabel}</div>
          </div>
        </div>
      </div>
    </header>
  );
}
