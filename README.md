# ISK3d UV Transform

Addon de Blender para ajustar y proyectar UV sin pelearse con el editor UV. Está pensado como ayuda de aprendizaje: no sustituye al editor UV, pero hace cómodo lo más común.

Probado con **Blender 5.2 LTS**.

## Funciones

- Desplazar la textura en U y V con valores numéricos.
- Estirar o contraer la textura en U y V.
- Aplicar los cambios a **todo el objeto** o solo a las **caras seleccionadas**.
- Resetear las UV a su estado base.
- Fijar las UV actuales como nueva base.
- Proyectar UV con **Cube**, **Cylinder**, **Sphere**, **Unwrap**, **Smart UV Project**, **Lightmap Pack**, **Project from View**, **Project from View (Bounds)** y **Follow Active Quads**.
- Botón propio para entrar/salir de **Edit Mode** desde el panel, sin depender de `Tab` sobre la barra lateral.
- Panel de atajos para seleccionar caras sin memorizar Blender.

## Instalación

1. Descarga `isk3d_uv_transform.py`.
2. En Blender: **Edit → Preferences → Add-ons → Install from Disk...**.
3. Selecciona el archivo y activa **ISK3d UV Transform**.
4. En el viewport 3D pulsa `N` y abre la pestaña **ISK3d**.

## Uso

1. Selecciona un objeto de malla en **Object Mode**.
2. Abre `N → ISK3d → Textura UV`.
3. Elige el ámbito:
   - **Objeto completo**: afecta a todas las caras.
   - **Caras seleccionadas**: afecta solo a las caras marcadas.
4. Mueve los campos de **Desplazar textura** o **Estirar / contraer textura**.

La base UV se captura automáticamente al mover el primer control. También puedes fijarla explícitamente con **Fijar UV actuales**.

### Modificar solo una cara

1. Pulsa **Entrar en Edit Mode para seleccionar caras** en el panel, o `Tab` con el ratón sobre el viewport 3D.
2. `3` para activar el modo de selección de caras.
3. Haz clic en la cara que quieras ajustar.
4. Vuelve a **Object Mode** con el botón del panel o `Tab`.
5. En el addon elige **Caras seleccionadas** y mueve los campos.

La selección de caras se conserva al volver a Object Mode. Las UVs son por loop, así que las caras vecinas no se mueven, aunque puede aparecer una costura.

> `Tab` solo funciona si el ratón está sobre el visor 3D. Si estás en la barra lateral, usa el botón del panel.

## Proyecciones UV

Las proyecciones usan el ámbito seleccionado en **Aplicar a**. En **Object Mode** el addon entra en Edit Mode, aplica la proyección y vuelve a Object Mode; en **Edit Mode** respeta la selección actual de caras.

| Botón | Qué hace |
|---|---|
| **Cubo** | Proyección cúbica sobre las caras seleccionadas |
| **Cilindro** | Proyección cilíndrica, con eje de objeto o de vista |
| **Esfera** | Proyección esférica, con eje de objeto o de vista |
| **Unwrap** | Desplegado por ángulos, conformal o mínimo estiramiento |
| **Smart UV** | Desplegado automático por islas |
| **Lightmap** | Empaqueta las islas en la capa UV activa (no hornea iluminación) |
| **Desde vista** | Proyecta desde la vista actual del visor 3D |
| **Vista bounds** | Igual que la anterior, ajustando el resultado al rango 0–1 |
| **Seguir cara** | Follow Active Quads; necesita una cara activa cuadrada |

### Ajustes de proyección

- **Eje**: usa los ejes locales del objeto o la vista actual para cilindro y esfera.
- **Ajustar a 0–1**: escala el resultado para ocupar el rango UV 0–1 en cubo, cilindro, esfera y Smart UV.
- **Smart ángulo / Smart margen**: parámetros de Smart UV Project.
- **Unwrap / Margen**: método y separación del desplegado.

Notas:

- **Project from View** y **Vista bounds** necesitan un visor 3D abierto y usan la vista actual.
- **Follow Active Quads** requiere una cara activa que sea un quad; si la cara activa no lo es, el addon busca un quad seleccionado y, si no existe, avisa.
- **Lightmap Pack** empaqueta islas; no genera un bake de iluminación.

## Atajos incluidos en el panel

| Atajo | Acción |
|---|---|
| `Tab` | Entrar / salir de Edit Mode (solo sobre el visor 3D) |
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
- Después de una proyección la base se invalida y se vuelve a capturar al regresar a Object Mode.

## Licencia

GPL-3.0-or-later. Ver `LICENSE`.
