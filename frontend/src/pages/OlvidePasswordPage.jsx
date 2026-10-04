import { useState } from "react";
import { Link } from "react-router-dom";
import { olvidePassword } from "../api";
import AuthShell from "../components/AuthShell";
import Alert from "../components/ui/Alert";
import Button from "../components/ui/Button";
import Spinner from "../components/ui/Spinner";
import { inputClass, labelClass } from "../components/ui/formStyles";

export default function OlvidePasswordPage() {
  const [email, setEmail] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [mensaje, setMensaje] = useState(null);
  const [error, setError] = useState(null);

  async function manejarEnvio(e) {
    e.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      const respuesta = await olvidePassword(email);
      setMensaje(respuesta.mensaje);
    } catch (e) {
      setError(e.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <AuthShell>
      <h2 className="mb-1 text-base font-semibold text-gray-900">Recupera tu contraseña</h2>
      <p className="mb-3 text-sm text-gray-500">
        Escribe tu correo y te enviaremos un enlace para elegir una contraseña nueva.
      </p>

      {error && (
        <Alert variant="danger" className="mb-3">
          {error}
        </Alert>
      )}

      {mensaje ? (
        <Alert variant="success" className="mb-3">
          {mensaje}
        </Alert>
      ) : (
        <form onSubmit={manejarEnvio} className="flex flex-col gap-3">
          <div>
            <label className={labelClass}>Correo electrónico</label>
            <input
              type="email"
              className={inputClass}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="correo@ejemplo.com"
            />
          </div>
          <Button type="submit" variant="dark" disabled={enviando} className="w-full">
            {enviando ? <Spinner size="sm" /> : "Enviar enlace"}
          </Button>
        </form>
      )}

      <div className="mt-4 border-t border-gray-100 pt-3 text-center text-sm">
        <Link to="/login" className="text-blue-600 hover:underline">
          Volver a iniciar sesión
        </Link>
      </div>
    </AuthShell>
  );
}
