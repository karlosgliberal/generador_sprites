# Plan de investigación: generación de sprites pixel art

## Contrato universal (todas las líneas)

```
INPUT:  description (str) + action (str: idle/walk/run/jump/punch/sword_attack/death)
OUTPUT: sprite strip PNG (N frames, estilo pixel art)
```

## Cómo usar

Ejecutar siempre desde el directorio raíz del proyecto (`generador_sprites/`):

```bash
# Ejecutar un experimento
python -m research run --line L1 --action idle

# Con personaje de test predefinido
python -m research run --line L1 --action idle --character ninja

# Test smoke (solo idle)
python -m research test --line L1 --level smoke

# Test standard (idle + walk + punch)
python -m research test --line L1 --level standard
```

## Mecanismo de rollback

Cada línea vive en su rama `research/L{N}-*`. Cada subfase es un commit atómico.

- **Revertir una subfase**: `git revert <commit>` (mantiene historial)
- **Descartar línea entera**: `git checkout main` (la rama queda como registro)
- **Comparar líneas**: los outputs se guardan en `research_output/` con metadata JSON

## Líneas de investigación

### L1: Frame-a-frame condicionado (rama: research/L1-frame-conditioned)

**Hipótesis**: Si en vez de recortar partes, le pasamos al modelo generativo el avatar como referencia de identidad + cada template frame como guía de pose, el modelo genera frames completos coherentes.

**Subfases**:

| ID | Subfase | Entrada | Salida | Criterio de éxito |
|----|---------|---------|--------|-------------------|
| L1.1 | Gemini directo: avatar ref + template como pose guide | description + template frames | frames individuales | El personaje mantiene identidad entre frames |
| L1.2 | Prompt engineering: optimizar instrucciones de pose | Resultado L1.1 + prompts mejorados | frames mejorados | Mejor adherencia a la pose del template |
| L1.3 | Consistencia temporal: referencias cruzadas entre frames | Resultado L1.2 + frames previos como ref | frames más consistentes | Menos variación de estilo/proporciones |
| L1.4 | Post-proceso pixel art: cuantización + grid alignment | Frames de L1.3 | sprites pixel art limpios | Paleta reducida, bordes nítidos |

### L2: Pipeline 3D (rama: research/L2-pipeline-3d)

**Hipótesis**: Generar un modelo 3D del avatar, aplicar animaciones predefinidas (Mixamo) y renderizar con pixel art shader garantiza consistencia perfecta.

**Subfases**: (se planificarán cuando L1 se complete o se descarte)

| ID | Subfase | Entrada | Salida |
|----|---------|---------|--------|
| L2.1 | Imagen → modelo 3D (TripoSR/Meshy) | avatar image | mesh 3D |
| L2.2 | Auto-rig + animaciones (Mixamo) | mesh 3D | mesh animado |
| L2.3 | Render pixel art (Blender shader) | mesh animado | sprite frames |
| L2.4 | Post-proceso | frames raw | sprites pixel art |

### L3: Video-to-sprite (rama: research/L3-video-to-sprite)

**Hipótesis**: Los modelos de video generativo pueden producir animaciones coherentes que luego se extraen como frames.

### L4: Skeleton-conditioned generation (rama: research/L4-skeleton-conditioned)

**Hipótesis**: Definir skeletons explícitos como representación intermedia entre acción y frame, y condicionar la generación con skeleton + identidad.
