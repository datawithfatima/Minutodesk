import { ArrowLeft } from "lucide-react";
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
    <AuthShell
      titulo="Recupera tu contraseña"
      descripcion="Escribe tu correo y te enviaremos un enlace para elegir una contraseña nueva."
      pie={
        <Link to="/login" className="inline-flex items-center gap-1.5 rounded text-acento hover:underline">
          <ArrowLeft size={15} aria-hidden="true" /> Volver a iniciar sesión
        </Link>
      }
    >
      {error && (
        <Alert variant="danger" className="mb-4">
          {error}
        </Alert>
      )}

      {mensaje ? (
        <Alert variant="success">{mensaje}</Alert>
      ) : (
        <form onSubmit={manejarEnvio} className="flex flex-col gap-4">
          <div>
            <label htmlFor="olvide-email" className={labelClass}>
              Correo electrónico
            </label>
            <input
              id="olvide-email"
              type="email"
              className={inputClass}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              autoFocus
              placeholder="nombre@empresa.com"
            />
          </div>
          <Button type="submit" size="lg" disabled={enviando} className="w-full">
            {enviando ? (
              <>
                <Spinner size="sm" /> Enviando…
              </>
            ) : (
              "Enviar enlace"
            )}
          </Button>
        </form>
      )}
    </AuthShell>
  );
}
