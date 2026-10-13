import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { establecerPassword } from "../api";
import AuthShell from "../components/AuthShell";
import Alert from "../components/ui/Alert";
import Button from "../components/ui/Button";
import CampoPassword from "../components/ui/CampoPassword";
import Spinner from "../components/ui/Spinner";
import { labelClass } from "../components/ui/formStyles";

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
    <AuthShell
      titulo="Elige tu contraseña"
      descripcion={token && !mensaje ? "Mínimo 8 caracteres, con letras y números." : undefined}
      pie={
        !mensaje && (
          <Link to="/login" className="rounded text-acento hover:underline">
            Volver a iniciar sesión
          </Link>
        )
      }
    >
      {!token && (
        <Alert variant="danger" className="mb-4">
          Falta el enlace de recuperación. Solicita uno nuevo desde{" "}
          <Link to="/olvide-password" className="font-medium underline">
            ¿Olvidaste tu contraseña?
          </Link>
        </Alert>
      )}

      {error && (
        <Alert variant="danger" className="mb-4">
          {error}
        </Alert>
      )}

      {mensaje ? (
        <>
          <Alert variant="success" className="mb-4">
            {mensaje}
          </Alert>
          <Link
            to="/login"
            className="flex h-12 items-center justify-center rounded-lg bg-acento px-5 text-[15px] font-medium text-white shadow-sm transition-colors duration-150 hover:bg-acento-600"
          >
            Ir a iniciar sesión
          </Link>
        </>
      ) : (
        token && (
          <form onSubmit={manejarEnvio} className="flex flex-col gap-4">
            <div>
              <label htmlFor="nueva-password" className={labelClass}>
                Contraseña nueva
              </label>
              <CampoPassword
                id="nueva-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
                autoFocus
              />
            </div>
            <div>
              <label htmlFor="nueva-password-2" className={labelClass}>
                Repite la contraseña
              </label>
              <CampoPassword
                id="nueva-password-2"
                value={confirmacion}
                onChange={(e) => setConfirmacion(e.target.value)}
                required
                autoComplete="new-password"
              />
            </div>
            <Button type="submit" size="lg" disabled={enviando} className="mt-1 w-full">
              {enviando ? <Spinner size="sm" /> : "Guardar contraseña"}
            </Button>
          </form>
        )
      )}
    </AuthShell>
  );
}
