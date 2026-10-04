import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { establecerPassword } from "../api";
import AuthShell from "../components/AuthShell";
import Alert from "../components/ui/Alert";
import Button from "../components/ui/Button";
import Spinner from "../components/ui/Spinner";
import { inputClass, labelClass } from "../components/ui/formStyles";

export default function EstablecerPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get("token");
  const [password, setPassword] = useState("");
  const [confirmacion, setConfirmacion] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [mensaje, setMensaje] = useState(null);
  const [error, setError] = useState(null);

  async function manejarEnvio(e) {
    e.preventDefault();
    setError(null);
    if (password !== confirmacion) {
      setError("Las contraseñas no coinciden");
      return;
    }
    setEnviando(true);
    try {
      const respuesta = await establecerPassword({ token, password });
      setMensaje(respuesta.mensaje);
    } catch (e) {
      setError(e.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <AuthShell>
      <h2 className="mb-1 text-base font-semibold text-gray-900">Elige tu contraseña</h2>

      {!token && (
        <Alert variant="danger" className="mb-3">
          Falta el enlace de activación. Solicita uno nuevo desde "¿Olvidaste tu contraseña?".
        </Alert>
      )}

      {error && (
        <Alert variant="danger" className="mb-3">
          {error}
        </Alert>
      )}

      {mensaje ? (
        <>
          <Alert variant="success" className="mb-3">
            {mensaje}
          </Alert>
          <Link
            to="/login"
            className="block rounded-md bg-slate-800 px-4 py-2 text-center text-sm font-medium text-white hover:bg-slate-900"
          >
            Ir a iniciar sesión
          </Link>
        </>
      ) : (
        token && (
          <form onSubmit={manejarEnvio} className="flex flex-col gap-3">
            <p className="text-sm text-gray-500">
              Mínimo 8 caracteres, con letras y números.
            </p>
            <div>
              <label className={labelClass}>Contraseña nueva</label>
              <input
                type="password"
                className={inputClass}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
              />
            </div>
            <div>
              <label className={labelClass}>Repite la contraseña</label>
              <input
                type="password"
                className={inputClass}
                value={confirmacion}
                onChange={(e) => setConfirmacion(e.target.value)}
                required
                autoComplete="new-password"
              />
            </div>
            <Button type="submit" variant="dark" disabled={enviando} className="w-full">
              {enviando ? <Spinner size="sm" /> : "Guardar contraseña"}
            </Button>
          </form>
        )
      )}
    </AuthShell>
  );
}
