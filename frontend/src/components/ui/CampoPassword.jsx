import { Eye, EyeOff } from "lucide-react";
import { useState } from "react";
import { inputClass } from "./formStyles";

/** Campo de contraseña con botón para mostrarla u ocultarla (útil al escribir la temporal). */
export default function CampoPassword({ id, className = "", ...props }) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="relative">
      <input id={id} type={visible ? "text" : "password"} className={`${inputClass} pr-11 ${className}`} {...props} />
      <button
        type="button"
        onClick={() => setVisible((v) => !v)}
        aria-label={visible ? "Ocultar contraseña" : "Mostrar contraseña"}
        aria-pressed={visible}
        aria-controls={id}
        className="absolute inset-y-0 right-0 flex w-10 items-center justify-center rounded-r-lg text-gray-400 transition-colors duration-150 hover:text-noche"
      >
        {visible ? <EyeOff size={17} aria-hidden="true" /> : <Eye size={17} aria-hidden="true" />}
      </button>
    </div>
  );
}
