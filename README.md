# ISK3d UV Transform

Addon sencillo para ajustar texturas UV sin pelearse con el editor UV de Blender. Está pensado como ayuda de aprendizaje: no sustituye al editor UV, solo hace cómodo lo más común.

## Funciones

- Desplazar la textura en U y V con valores numéricos.
- Estirar o contraer la textura en U y V.
- Aplicar los cambios a **todo el objeto** o solo a las **caras seleccionadas**.
- Resetear las UV a su estado base.
- Fijar las UV actuales como nueva base.
- Panel de atajos para seleccionar caras sin memorizar Blender.

## Instalación

1. Descarga `isk3d_uv_transform.py`.
2. En Blender: **Edit → Preferences → Add-ons → Install from Disk...**.
3. Selecciona el archivo y activa **ISK3d UV Transform**.
4. En el viewport 3D pulsa `N` y abre la pestaña **ISK3d**.

Probado con **Blender 5.2 LTS**.

## Uso

1. Selecciona un objeto de malla en **Object Mode**.
2. Abre `N → ISK3d → Textura UV`.
3. Elige el ámbito:
   - **Objeto completo**: afecta a todas las caras.
   - **Caras seleccionadas**: afecta solo a las caras marcadas.
4. Mueve los campos de **Desplazar textura** o **Estirar / contraer textura**.

### Modificar solo una cara

1. `Tab` para entrar en **Edit Mode**.
2. `3` para activar el modo de selección de caras.
3. Haz clic en la cara que quieras ajustar.
4. `Tab` para volver a **Object Mode**.
5. En el addon elige **Caras seleccionadas** y mueve los campos.

La selección de caras se conserva al volver a Object Mode. Las UVs son por loop, así que las caras vecinas no se mueven, aunque puede aparecer una costura.

## Atajos incluidos en el panel

| Atajo | Acción |
|---|---|
| `Tab` | Entrar / salir de Edit Mode |
| `3` | Modo de selección de caras |
| `A` | Seleccionar todo |
| `Alt+A` | Deseleccionar todo |
| `B` | Selección por caja |
| `C` | Selección circular |
| `Shift+clic` | Ampliar la selección |
| `N` | Mostrar / ocultar el panel lateral |

## Notas

- Cada ajuste se calcula desde la UV base. Si vuelves a una cara ya modificada y cambias el valor, se recalcula desde la base.
- El botón **Fijar UV actuales** toma todas las UV actuales del objeto como nuevo punto de partida.
- Si un objeto se queda gris o sin textura, revisa que sus UV no estén colapsadas y usa **Reset UV** o **Fijar UV actuales**.
- El addon trabaja sobre el objeto activo y su capa UV activa.

## Licencia

GPL-3.0-or-later. Ver `LICENSE`.
