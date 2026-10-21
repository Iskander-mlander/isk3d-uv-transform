# SPDX-License-Identifier: GPL-3.0-or-later

bl_info = {
    "name": "ISK3d UV Transform",
    "author": "ISK3d",
    "version": (1, 4, 1),
    "blender": (5, 2, 0),
    "location": "View3D > Sidebar > ISK3d",
    "description": "Desplaza, estira y proyecta las UV del objeto o de las caras seleccionadas",
    "category": "Object",
}

import bmesh
import bpy
import math
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import Operator, Panel, PropertyGroup

BASE_ATTR = "_isk3d_uv_base_v"
UV_EPS = 1e-7


def _active_uv(ob):
    return ob.data.uv_layers.active


def _bounds(values):
    values = list(values)
    if not values:
        return None
    return (
        min(v[0] for v in values),
        max(v[0] for v in values),
        min(v[1] for v in values),
        max(v[1] for v in values),
    )


def _layer_bounds(layer):
    if layer is None or len(layer.data) == 0:
        return None
    return _bounds((d.uv[0], d.uv[1]) for d in layer.data)


def _attr_bounds(attr):
    if attr is None or len(attr.data) == 0:
        return None
    return _bounds((d.vector.x, d.vector.y) for d in attr.data)


def _usable_bounds(bounds):
    if bounds is None:
        return False
    return (bounds[1] - bounds[0]) > UV_EPS and (bounds[3] - bounds[2]) > UV_EPS


def _valid_attr(me):
    attr = me.attributes.get(BASE_ATTR)
    if attr is None:
        return None
    if (
        attr.data_type != "FLOAT_VECTOR"
        or attr.domain != "CORNER"
        or len(attr.data) != len(me.loops)
    ):
        me.attributes.remove(attr)
        return None
    return attr


def _reset_props(props):
    props.suspend = True
    props.offset_u = 0.0
    props.offset_v = 0.0
    props.scale_u = 1.0
    props.scale_v = 1.0
    props.suspend = False


def _capture_base(ob, props, layer):
    bounds = _layer_bounds(layer)
    if not _usable_bounds(bounds):
        props.base_valid = False
        return False

    me = ob.data
    attr = _valid_attr(me)
    if attr is None:
        attr = me.attributes.new(name=BASE_ATTR, type="FLOAT_VECTOR", domain="CORNER")
    if len(attr.data) != len(me.loops):
        me.attributes.remove(attr)
        attr = me.attributes.new(name=BASE_ATTR, type="FLOAT_VECTOR", domain="CORNER")

    for index in range(len(me.loops)):
        u, v = layer.data[index].uv
        attr.data[index].vector = (u, v, 0.0)

    props.pivot_u = (bounds[0] + bounds[1]) * 0.5
    props.pivot_v = (bounds[2] + bounds[3]) * 0.5
    props.base_layer = layer.name
    props.base_valid = True
    me.update()
    return True


def _ensure_base(ob, props):
    layer = _active_uv(ob)
    if layer is None:
        return None

    me = ob.data
    attr = _valid_attr(me)
    if attr is not None:
        if not props.base_valid or not props.base_layer:
            me.attributes.remove(attr)
            attr = None
    if attr is not None:
        bounds = _attr_bounds(attr)
        if _usable_bounds(bounds):
            if props.base_layer and props.base_layer != layer.name:
                if _capture_base(ob, props, layer):
                    return layer
                return None
            return layer
        me.attributes.remove(attr)
        props.base_valid = False

    if _capture_base(ob, props, layer):
        return layer
    return None


def _base_ready(ob, props):
    layer = _active_uv(ob)
    if layer is None:
        return False
    if not props.base_valid or props.base_layer != layer.name:
        return False
    me = ob.data
    attr = me.attributes.get(BASE_ATTR)
    if attr is None:
        return False
    return (
        attr.data_type == "FLOAT_VECTOR"
        and attr.domain == "CORNER"
        and len(attr.data) == len(me.loops)
    )


def _invalidate_base(ob, props):
    me = ob.data
    attr = me.attributes.get(BASE_ATTR)
    if attr is not None:
        me.attributes.remove(attr)
    props.base_valid = False
    props.base_layer = ""
    _reset_props(props)
    me.update()


def _selected_loop_indices(me):
    indices = []
    for poly in me.polygons:
        if poly.select:
            indices.extend(poly.loop_indices)
    return indices


def _target_loop_indices(me, props):
    if props.scope == "FACES":
        return _selected_loop_indices(me)
    return range(len(me.loops))


def _apply(ob, props, layer):
    me = ob.data
    attr = _valid_attr(me)
    if attr is None or not props.base_valid:
        return False
    if not _usable_bounds(_attr_bounds(attr)):
        return False

    indices = _target_loop_indices(me, props)
    if not indices:
        return False

    factor_u = 1.0 / max(props.scale_u, 0.001)
    factor_v = 1.0 / max(props.scale_v, 0.001)
    pivot_u = props.pivot_u
    pivot_v = props.pivot_v
    offset_u = props.offset_u
    offset_v = props.offset_v

    for index in indices:
        base = attr.data[index].vector
        layer.data[index].uv = (
            pivot_u + (base.x - pivot_u) * factor_u + offset_u,
            pivot_v + (base.y - pivot_v) * factor_v + offset_v,
        )
    me.update()
    return True


def _update(self, context):
    if self.suspend:
        return
    ob = self.id_data
    if not isinstance(ob, bpy.types.Object):
        ob = bpy.context.active_object
    if ob is None or ob.type != "MESH" or ob.mode != "OBJECT":
        return
    layer = _ensure_base(ob, self)
    if layer is None:
        return
    _apply(ob, self, layer)


def _view3d_override(context):
    area = context.area
    if area is None or area.type != "VIEW_3D":
        screen = context.screen
        area = None
        if screen is not None:
            area = next((a for a in screen.areas if a.type == "VIEW_3D"), None)
    if area is None:
        return None
    region = next((r for r in area.regions if r.type == "WINDOW"), None)
    if region is None:
        return None
    return {"area": area, "region": region, "space_data": area.spaces.active}


def _set_active_face(me):
    bm = bmesh.from_edit_mesh(me)
    bm.faces.ensure_lookup_table()
    active = bm.faces.active
    if active is None or not active.select or len(active.verts) != 4:
        active = next((f for f in bm.faces if f.select and len(f.verts) == 4), None)
        if active is None:
            raise RuntimeError(
                "Follow Active Quads necesita una cara activa cuadrada; selecciona un quad"
            )
        bm.faces.active = active
    bmesh.update_edit_mesh(me)


class ISK3D_UVTransformProps(PropertyGroup):
    scope: EnumProperty(
        name="Aplicar a",
        description="Ambito de la transformacion UV",
        items=(
            ("OBJECT", "Objeto completo", "Todas las caras del objeto"),
            ("FACES", "Caras seleccionadas", "Solo las caras seleccionadas"),
        ),
        default="OBJECT",
        update=_update,
    )
    offset_u: FloatProperty(
        name="U",
        description="Desplazamiento en U, en unidades UV",
        default=0.0,
        min=-100.0,
        max=100.0,
        soft_min=-1.0,
        soft_max=1.0,
        precision=4,
        step=1,
        update=_update,
    )
    offset_v: FloatProperty(
        name="V",
        description="Desplazamiento en V, en unidades UV",
        default=0.0,
        min=-100.0,
        max=100.0,
        soft_min=-1.0,
        soft_max=1.0,
        precision=4,
        step=1,
        update=_update,
    )
    scale_u: FloatProperty(
        name="U",
        description="Tamano de la textura en U: 1.0 es el original",
        default=1.0,
        min=0.01,
        max=100.0,
        soft_min=0.1,
        soft_max=10.0,
        precision=4,
        step=1,
        update=_update,
    )
    scale_v: FloatProperty(
        name="V",
        description="Tamano de la textura en V: 1.0 es el original",
        default=1.0,
        min=0.01,
        max=100.0,
        soft_min=0.1,
        soft_max=10.0,
        precision=4,
        step=1,
        update=_update,
    )
    proj_direction: EnumProperty(
        name="Eje",
        description="Orientacion de las proyecciones cilindrica y esferica",
        items=(
            ("OBJECT", "Objeto", "Usar los ejes locales del objeto"),
            ("VIEW", "Vista", "Usar la vista actual del visor 3D"),
        ),
        default="OBJECT",
    )
    proj_fit_bounds: BoolProperty(
        name="Ajustar a 0-1",
        description="Escalar el resultado para ocupar el rango UV 0-1",
        default=False,
    )
    smart_angle: FloatProperty(
        name="Smart angulo",
        description="Angulo maximo entre caras para Smart UV Project",
        default=66.0,
        min=1.0,
        max=89.0,
    )
    smart_margin: FloatProperty(
        name="Smart margen",
        description="Margen entre islas de Smart UV Project",
        default=0.02,
        min=0.0,
        max=1.0,
        precision=4,
    )
    unwrap_method: EnumProperty(
        name="Unwrap",
        description="Metodo de desplegado",
        items=(
            ("ANGLE_BASED", "Angle Based", "Desplegado por angulos"),
            ("CONFORMAL", "Conformal", "Desplegado conformal"),
            ("MINIMUM_STRETCH", "Minimum Stretch", "Minimo estiramiento"),
        ),
        default="ANGLE_BASED",
    )
    unwrap_margin: FloatProperty(
        name="Margen",
        description="Margen del desplegado",
        default=0.001,
        min=0.0,
        max=1.0,
        precision=4,
    )
    pivot_u: FloatProperty(default=0.0, options={"HIDDEN"})
    pivot_v: FloatProperty(default=0.0, options={"HIDDEN"})
    base_layer: StringProperty(default="", options={"HIDDEN"})
    base_valid: BoolProperty(default=False, options={"HIDDEN"})
    suspend: BoolProperty(default=False, options={"HIDDEN"})


class ISK3D_OT_uv_transform_reset(Operator):
    bl_idname = "isk3d.uv_transform_reset"
    bl_label = "Reset UV"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ob = context.active_object
        if ob is None or ob.type != "MESH" or not hasattr(ob, "isk3d_uv_transform"):
            self.report({"ERROR"}, "Selecciona un objeto de malla")
            return {"CANCELLED"}

        props = ob.isk3d_uv_transform
        props.suspend = True
        props.offset_u = 0.0
        props.offset_v = 0.0
        props.scale_u = 1.0
        props.scale_v = 1.0
        props.suspend = False

        layer = _ensure_base(ob, props)
        if layer is None:
            self.report({"ERROR"}, "La base UV no es valida; usa 'Fijar UV actuales'")
            return {"CANCELLED"}
        if not _apply(ob, props, layer):
            if props.scope == "FACES":
                self.report({"ERROR"}, "Selecciona al menos una cara")
            else:
                self.report({"ERROR"}, "La base UV no es valida")
            return {"CANCELLED"}
        return {"FINISHED"}


class ISK3D_OT_uv_capture_base(Operator):
    bl_idname = "isk3d.uv_transform_capture_base"
    bl_label = "Fijar UV actuales como base"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ob = context.active_object
        if ob is None or ob.type != "MESH" or not hasattr(ob, "isk3d_uv_transform"):
            self.report({"ERROR"}, "Selecciona un objeto de malla")
            return {"CANCELLED"}

        layer = _active_uv(ob)
        if layer is None:
            self.report({"ERROR"}, "El objeto no tiene UV")
            return {"CANCELLED"}

        props = ob.isk3d_uv_transform
        if not _capture_base(ob, props, layer):
            self.report({"ERROR"}, "Las UV actuales estan colapsadas")
            return {"CANCELLED"}
        _reset_props(props)
        _apply(ob, props, layer)
        return {"FINISHED"}


class ISK3D_OT_uv_toggle_edit(Operator):
    bl_idname = "isk3d.uv_toggle_edit"
    bl_label = "Cambiar Object/Edit Mode"
    bl_description = "Cambia de modo sin depender del atajo Tab sobre la barra lateral"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        return ob is not None and ob.type == "MESH"

    def execute(self, context):
        ob = context.active_object
        target = "EDIT" if ob.mode == "OBJECT" else "OBJECT"
        try:
            bpy.ops.object.mode_set(mode=target)
        except RuntimeError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        return {"FINISHED"}


class ISK3D_OT_uv_project(Operator):
    bl_idname = "isk3d.uv_project"
    bl_label = "Proyectar UV"
    bl_description = "Aplica una proyeccion o desplegado UV a las caras del ambito"
    bl_options = {"REGISTER", "UNDO"}

    method: EnumProperty(
        items=(
            ("CUBE", "Cubo", ""),
            ("CYLINDER", "Cilindro", ""),
            ("SPHERE", "Esfera", ""),
            ("UNWRAP", "Unwrap", ""),
            ("SMART", "Smart UV", ""),
            ("LIGHTMAP", "Lightmap", ""),
            ("VIEW", "Desde vista", ""),
            ("VIEW_BOUNDS", "Vista bounds", ""),
            ("FOLLOW", "Seguir cara activa", ""),
        ),
        default="CUBE",
    )

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        return ob is not None and ob.type == "MESH"

    def _run(self, context, props):
        ob = context.active_object
        me = ob.data
        direction = (
            "ALIGN_TO_OBJECT" if props.proj_direction == "OBJECT" else "VIEW_ON_EQUATOR"
        )
        fit = props.proj_fit_bounds

        if self.method == "CUBE":
            bpy.ops.uv.cube_project(
                cube_size=1.0,
                correct_aspect=True,
                clip_to_bounds=False,
                scale_to_bounds=fit,
            )
        elif self.method == "CYLINDER":
            bpy.ops.uv.cylinder_project(
                direction=direction,
                align="POLAR_ZX",
                pole="PINCH",
                seam=False,
                radius=1.0,
                correct_aspect=True,
                clip_to_bounds=False,
                scale_to_bounds=fit,
            )
        elif self.method == "SPHERE":
            bpy.ops.uv.sphere_project(
                direction=direction,
                align="POLAR_ZX",
                pole="PINCH",
                seam=False,
                correct_aspect=True,
                clip_to_bounds=False,
                scale_to_bounds=fit,
            )
        elif self.method == "UNWRAP":
            bpy.ops.uv.unwrap(
                method=props.unwrap_method,
                fill_holes=True,
                correct_aspect=True,
                margin_method="SCALED",
                margin=props.unwrap_margin,
                no_flip=False,
                iterations=10,
            )
        elif self.method == "SMART":
            bpy.ops.uv.smart_project(
                angle_limit=math.radians(props.smart_angle),
                margin_method="SCALED",
                island_margin=props.smart_margin,
                area_weight=0.0,
                correct_aspect=True,
                scale_to_bounds=fit,
            )
        elif self.method == "LIGHTMAP":
            bpy.ops.uv.lightmap_pack(
                PREF_CONTEXT="SEL_FACES",
                PREF_PACK_IN_ONE=True,
                PREF_NEW_UVLAYER=False,
                PREF_BOX_DIV=12,
                PREF_MARGIN_DIV=0.1,
            )
        elif self.method == "VIEW":
            override = _view3d_override(context)
            if override is None:
                raise RuntimeError("Abre un visor 3D para proyectar desde la vista")
            with context.temp_override(**override):
                bpy.ops.uv.project_from_view(
                    camera_bounds=False,
                    correct_aspect=True,
                    clip_to_bounds=False,
                    scale_to_bounds=False,
                )
        elif self.method == "VIEW_BOUNDS":
            override = _view3d_override(context)
            if override is None:
                raise RuntimeError("Abre un visor 3D para proyectar desde la vista")
            with context.temp_override(**override):
                bpy.ops.uv.project_from_view(
                    camera_bounds=False,
                    correct_aspect=True,
                    clip_to_bounds=False,
                    scale_to_bounds=True,
                )
        elif self.method == "FOLLOW":
            _set_active_face(me)
            bpy.ops.uv.follow_active_quads(mode="LENGTH_AVERAGE")

    def execute(self, context):
        ob = context.active_object
        if ob is None or ob.type != "MESH":
            self.report({"ERROR"}, "Selecciona un objeto de malla")
            return {"CANCELLED"}
        if not hasattr(ob, "isk3d_uv_transform"):
            self.report({"ERROR"}, "El addon no esta registrado en este objeto")
            return {"CANCELLED"}

        me = ob.data
        layer = _active_uv(ob)
        if layer is None:
            self.report({"ERROR"}, "El objeto no tiene capa UV")
            return {"CANCELLED"}

        props = ob.isk3d_uv_transform
        was_mode = ob.mode
        if was_mode == "OBJECT":
            if props.scope == "FACES" and not any(p.select for p in me.polygons):
                self.report({"ERROR"}, "Selecciona al menos una cara")
                return {"CANCELLED"}
            try:
                bpy.ops.object.mode_set(mode="EDIT")
            except RuntimeError as exc:
                self.report({"ERROR"}, str(exc))
                return {"CANCELLED"}

        error = ""
        try:
            try:
                bpy.ops.mesh.select_mode(type="FACE")
            except RuntimeError:
                pass
            if props.scope == "OBJECT":
                bpy.ops.mesh.select_all(action="SELECT")
            elif not any(p.select for p in me.polygons):
                raise RuntimeError("Selecciona al menos una cara")
            self._run(context, props)
        except RuntimeError as exc:
            error = str(exc)

        if was_mode == "OBJECT":
            try:
                bpy.ops.object.mode_set(mode="OBJECT")
            except RuntimeError:
                pass

        if error:
            self.report({"ERROR"}, error)
            return {"CANCELLED"}

        _invalidate_base(ob, props)
        if was_mode == "OBJECT":
            layer = _active_uv(ob)
            if layer is not None and _capture_base(ob, props, layer):
                _reset_props(props)
        return {"FINISHED"}


def _draw_scope(layout, props, ob, edit_mode):
    box = layout.box()
    box.label(text="Aplicar a")
    box.prop(props, "scope", expand=True)
    if props.scope == "FACES":
        count = sum(1 for poly in ob.data.polygons if poly.select)
        if count:
            box.label(text=f"{count} caras seleccionadas", icon="FACESEL")
        else:
            box.label(text="Selecciona caras en Edit Mode", icon="INFO")
        if not edit_mode:
            box.label(text="Luego vuelve a Object Mode")


def _draw_projections(layout, props):
    box = layout.box()
    box.label(text="Proyecciones UV", icon="UV")
    col = box.column(align=True)

    row = col.row(align=True)
    row.operator("isk3d.uv_project", text="Cubo").method = "CUBE"
    row.operator("isk3d.uv_project", text="Cilindro").method = "CYLINDER"
    row.operator("isk3d.uv_project", text="Esfera").method = "SPHERE"

    row = col.row(align=True)
    row.operator("isk3d.uv_project", text="Unwrap").method = "UNWRAP"
    row.operator("isk3d.uv_project", text="Smart UV").method = "SMART"
    row.operator("isk3d.uv_project", text="Lightmap").method = "LIGHTMAP"

    row = col.row(align=True)
    row.operator("isk3d.uv_project", text="Desde vista").method = "VIEW"
    row.operator("isk3d.uv_project", text="Vista bounds").method = "VIEW_BOUNDS"
    row.operator("isk3d.uv_project", text="Seguir cara").method = "FOLLOW"

    col.separator()
    col.prop(props, "proj_direction")
    col.prop(props, "proj_fit_bounds")
    col.prop(props, "smart_angle")
    col.prop(props, "smart_margin")
    col.prop(props, "unwrap_method")
    col.prop(props, "unwrap_margin")
    col.label(text="El ambito es 'Aplicar a'", icon="INFO")
    col.label(text="'Desde vista' usa la vista actual del visor 3D")


class ISK3D_PT_uv_shortcuts(Panel):
    bl_label = "Atajos: seleccionar caras"
    bl_idname = "ISK3D_PT_uv_shortcuts"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ISK3d"
    bl_parent_id = "ISK3D_PT_uv_transform"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.label(text="Tab: entrar / salir de Edit Mode", icon="INFO")
        col.label(text="Solo funciona con el raton sobre el visor 3D")
        col.label(text="Desde la barra lateral usa el boton del panel")
        col.separator()
        col.label(text="3: modo de seleccion de caras")
        col.label(text="A: seleccionar todo")
        col.label(text="Alt+A: deseleccionar todo")
        col.label(text="B: seleccion por caja")
        col.label(text="C: seleccion circular")
        col.label(text="Shift+clic: ampliar la seleccion")
        col.label(text="N: mostrar / ocultar este panel")
        col.separator()
        col.label(text="Vuelve a Object Mode antes de usar los sliders")


class ISK3D_PT_uv_transform(Panel):
    bl_label = "Textura UV"
    bl_idname = "ISK3D_PT_uv_transform"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ISK3d"

    def draw(self, context):
        layout = self.layout
        ob = context.active_object
        if ob is None or ob.type != "MESH":
            layout.label(text="Selecciona un objeto de malla", icon="INFO")
            return
        if not hasattr(ob, "isk3d_uv_transform"):
            layout.label(text="El addon no esta registrado", icon="ERROR")
            return

        props = ob.isk3d_uv_transform
        if ob.mode != "OBJECT":
            layout.label(text=f"{ob.name} - Edit Mode", icon="EDITMODE_HLT")
            layout.operator(
                "isk3d.uv_toggle_edit",
                text="Volver a Object Mode (Tab)",
                icon="OBJECT_DATAMODE",
            )
            _draw_scope(layout, props, ob, True)
            _draw_projections(layout, props)
            layout.separator()
            layout.label(text="Los sliders UV requieren Object Mode", icon="INFO")
            return

        layer = _active_uv(ob)
        if layer is None:
            layout.label(text="El objeto no tiene UV", icon="ERROR")
            return

        if not _base_ready(ob, props):
            layout.label(text="Base UV pendiente: mueve un slider", icon="INFO")

        layout.label(text=ob.name)
        layout.label(text=f"Capa UV: {layer.name}")

        _draw_scope(layout, props, ob, False)

        box = layout.box()
        box.label(text="Desplazar textura")
        row = box.row(align=True)
        row.prop(props, "offset_u", text="U")
        row.prop(props, "offset_v", text="V")

        box = layout.box()
        box.label(text="Estirar / contraer textura")
        row = box.row(align=True)
        row.prop(props, "scale_u", text="U")
        row.prop(props, "scale_v", text="V")
        box.label(text="1.0 = original; 2.0 = doble")

        layout.separator()
        layout.label(text="Desplazamiento en unidades UV")
        row = layout.row(align=True)
        row.operator("isk3d.uv_transform_reset", text="Reset UV", icon="LOOP_BACK")
        row.operator(
            "isk3d.uv_transform_capture_base", text="Fijar UV actuales", icon="UV"
        )

        layout.separator()
        layout.operator(
            "isk3d.uv_toggle_edit",
            text="Entrar en Edit Mode para seleccionar caras",
            icon="EDITMODE_HLT",
        )
        _draw_projections(layout, props)


classes = (
    ISK3D_UVTransformProps,
    ISK3D_OT_uv_transform_reset,
    ISK3D_OT_uv_capture_base,
    ISK3D_OT_uv_toggle_edit,
    ISK3D_OT_uv_project,
    ISK3D_PT_uv_transform,
    ISK3D_PT_uv_shortcuts,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.isk3d_uv_transform = PointerProperty(type=ISK3D_UVTransformProps)


def unregister():
    del bpy.types.Object.isk3d_uv_transform
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
