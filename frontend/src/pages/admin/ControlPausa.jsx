import { Pause, Play } from "lucide-react";
import { useState } from "react";
import Button from "../../components/ui/Button";

/**
 * Botón para pausar una corrida con Minutito mientras corre, o reanudarla si quedó en
 * pausa. Al pausar termina el caso que está haciendo; lo generado y lo marcado se quedan.
 */
export default function ControlPausa({ enCurso, pausada, pausando, onPausar, onReanudar }) {
  const [ocupado, setOcupado] = useState(false);

  async function correr(accion) {
    setOcupado(true);
    try {
      await accion();
    } finally {
      setOcupado(false);
    }
  }

  if (enCurso) {
    return (
      <Button size="sm" variant="outlinePrimary" disabled={ocupado || pausando} onClick={() => correr(onPausar)}>
        <Pause size={14} aria-hidden="true" />
        {pausando ? "Pausando… (termina el caso actual)" : "Pausar"}
      </Button>
    );
  }
  if (!pausada) return null;
  return (
    <div className="space-y-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
      <p className="text-sm text-amber-800">En pausa. Lo generado y lo que marcaste se conservan.</p>
      <Button size="sm" variant="dark" disabled={ocupado} onClick={() => correr(onReanudar)}>
        <Play size={14} aria-hidden="true" />
        Reanudar
      </Button>
    </div>
  );
}
