import { Bot } from "lucide-react";

export default function MinutitoPanelProximamente() {
  return (
    <div className="flex h-full flex-col rounded-lg border border-gray-200 bg-white shadow-sm">
      <div className="flex items-center gap-3 border-b border-gray-100 p-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gray-300 text-white">
          <Bot size={18} />
        </div>
        <div>
          <div className="text-sm font-semibold text-gray-400">Minutito</div>
          <div className="text-xs text-gray-400">Asistente de soporte</div>
        </div>
      </div>
      <div className="flex flex-1 items-center justify-center p-6 text-center text-sm text-gray-400">
        Minutito para técnicos (sugerencias y chat sobre el ticket) llega próximamente.
      </div>
      <div className="border-t border-gray-100 p-3">
        <input
          disabled
          placeholder="Próximamente..."
          className="w-full cursor-not-allowed rounded-full border border-gray-200 bg-gray-50 px-4 py-2 text-sm text-gray-400"
        />
      </div>
    </div>
  );
}
