import { Heart, LogOut } from "lucide-react";
import { Link, useLocation } from "react-router-dom";

export default function Sidebar({ navItems, onLogout, footer, dark = false, children }) {
  const location = useLocation();

  const base = dark
    ? "flex w-60 shrink-0 flex-col bg-slate-900 text-white"
    : "flex w-56 shrink-0 flex-col border-r border-gray-200 bg-white";

  return (
    <aside className={base}>
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navItems.map((item) => {
          if (item.disabled) {
            return (
              <div
                key={item.label}
                className={`flex cursor-not-allowed items-center justify-between rounded-md px-3 py-2 text-sm ${
                  dark ? "text-slate-500" : "text-gray-300"
                }`}
                title="Próximamente"
              >
                <span className="flex items-center gap-2">
                  <item.icon size={16} />
                  {item.label}
                </span>
                <span
                  className={`rounded-full px-1.5 py-0.5 text-[10px] ${
                    dark ? "bg-slate-800 text-slate-500" : "bg-gray-100 text-gray-400"
                  }`}
                >
                  Próx.
                </span>
              </div>
            );
          }

          const activo = location.pathname === item.to;
          const activoCls = dark
            ? "bg-slate-800 font-medium text-white"
            : "bg-gray-100 font-medium text-gray-900";
          const inactivoCls = dark
            ? "text-slate-300 hover:bg-slate-800"
            : "text-gray-600 hover:bg-gray-50";

          return (
            <span key={item.label} className="relative block">
              <Link
                to={item.to}
                className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors ${
                  activo ? activoCls : inactivoCls
                }`}
              >
                <item.icon size={16} />
                {item.label}
              </Link>
              {item.badge != null && (
                <span
                  className={`absolute right-3 top-1/2 -translate-y-1/2 rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
                    dark ? "bg-slate-700 text-slate-200" : "bg-gray-200 text-gray-700"
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

      <div className="p-3">
        <button
          onClick={onLogout}
          className={`flex w-full items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium ${
            dark
              ? "bg-slate-800 text-white hover:bg-slate-700"
              : "bg-slate-900 text-white hover:bg-slate-800"
          }`}
        >
          <LogOut size={16} />
          Cerrar sesión
        </button>
      </div>

      {footer && (
        <div
          className={`flex flex-col items-center gap-1 border-t p-4 text-center text-xs ${
            dark ? "border-slate-800 text-slate-500" : "border-gray-100 text-gray-400"
          }`}
        >
          <span>{footer}</span>
          <Heart size={14} />
        </div>
      )}
    </aside>
  );
}
