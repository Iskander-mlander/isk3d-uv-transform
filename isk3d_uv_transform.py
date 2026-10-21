# SPDX-License-Identifier: GPL-3.0-or-later

bl_info = {
    "name": "ISK3d UV Transform",
    "author": "ISK3d",
    "version": (1, 3, 1),
    "blender": (5, 2, 0),
    "location": "View3D > Sidebar > ISK3d",
    "description": "Desplaza y estira las UV del objeto o de las caras seleccionadas",
    "category": "Object",
}

import bpy
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
        bounds = _attr_bounds(attr)
        if _usable_bounds(bounds):
            if props.base_layer and props.base_layer != layer.name:
                if _capture_base(ob, props, layer):
                    _reset_props(props)
                    return layer
                return None
            if not props.base_valid or not props.base_layer:
                props.pivot_u = (bounds[0] + bounds[1]) * 0.5
                props.pivot_v = (bounds[2] + bounds[3]) * 0.5
                props.base_layer = layer.name
                props.base_valid = True
            return layer
        me.attributes.remove(attr)
        props.base_valid = False

    if _capture_base(ob, props, layer):
        _reset_props(props)
        return layer
    return None


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
        col.label(text="Tab: entrar / salir de Edit Mode")
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
        if ob.mode != "OBJECT":
            layout.label(text="Sal de Edit Mode", icon="ERROR")
            return

        layer = _active_uv(ob)
        if layer is None:
            layout.label(text="El objeto no tiene UV", icon="ERROR")
            return

        props = ob.isk3d_uv_transform
        base_ok = _ensure_base(ob, props) is not None
        if not base_ok:
            layout.label(text="UV base no validas", icon="ERROR")

        layout.label(text=ob.name)
        layout.label(text=f"Capa UV: {layer.name}")

        box = layout.box()
        box.label(text="Aplicar a")
        box.prop(props, "scope", expand=True)
        if props.scope == "FACES":
            count = sum(1 for poly in ob.data.polygons if poly.select)
            if count:
                box.label(text=f"{count} caras seleccionadas", icon="FACESEL")
            else:
                box.label(text="Selecciona caras en Edit Mode", icon="INFO")
            box.label(text="Luego vuelve a Object Mode")

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


classes = (
    ISK3D_UVTransformProps,
    ISK3D_OT_uv_transform_reset,
    ISK3D_OT_uv_capture_base,
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
