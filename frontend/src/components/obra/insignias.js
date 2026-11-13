import { Blocks, BrickWall, Building, DraftingCompass, KeyRound, ScanSearch, Shovel, Timer } from "lucide-react";

// Iconos de línea (en lugar de emojis) para que las insignias y etapas compartan el trazo de la interfaz.
export const ICONO_INSIGNIA = {
  primera_piedra: Blocks,
  planos_al_dia: DraftingCompass,
  obra_sin_retrasos: Timer,
  inspector: ScanSearch,
};

// Una por etapa de obra, en orden: Cimientos, Estructura, Acabados, Entrega.
export const ICONO_ETAPA = [Shovel, BrickWall, Building, KeyRound];
