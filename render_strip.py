import bpy
import os
from collections import OrderedDict

def ShowMessageBox(message = "", title = "Message Box", icon = 'INFO'):

    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)


class RenderStripOperator(bpy.types.Operator):
    """Render all strips"""
    bl_idname = "render.renderstrip"
    bl_label = "Render Strip"

    _timer = None
    strips = None
    stop = None
    rendering = None

    # help revert to original
    camera = None
    frame_start = None
    frame_end = None
    path = None
    separate_dir = None

    def _init(self, dummy, thrd = None):
        self.rendering = True

    def _complete(self, dummy, thrd = None):
        self.strips.popitem(last=False)
        self.rendering = False

    def _cancel(self, dummy, thrd = None):
        self.stop = True

    def execute(self, context):
        try:
            self.stop = False
            self.rendering = False
            scene = bpy.context.scene
            active_strips = [strip for strip in scene.rs_settings.strips if strip.enabled]
            if any(strip.cam not in scene.objects or scene.objects[strip.cam].type != "CAMERA" for strip in active_strips):
                raise Exception("Invalid Camera in strips!")
            if not all(strip.name for strip in active_strips if strip.named):
                raise Exception("Invalid Name in named strips!")
            self.strips = OrderedDict({
                "{}.{}-{}".format(strip.cam,strip.start,strip.end) if not strip.named else strip.name : (strip.cam, strip.start,strip.end)
                for strip in active_strips
            })

            if len(self.strips) < 0:
                raise Exception("No strip defined")

            self.camera = scene.camera
            self.frame_start = scene.frame_start
            self.frame_end = scene.frame_end
            self.path = scene.render.filepath
            self.separate_dir = scene.rs_settings.separate_dir

            bpy.app.handlers.render_init.append(self._init)
            bpy.app.handlers.render_complete.append(self._complete)
            bpy.app.handlers.render_cancel.append(self._cancel)

            self._timer = bpy.context.window_manager.event_timer_add(0.5, window=bpy.context.window)
            bpy.context.window_manager.modal_handler_add(self)

            return {"RUNNING_MODAL"}
        except Exception as e:
            ShowMessageBox(icon="ERROR", message=str(e))
            return {"CANCELLED"}

    def modal(self, context, event):
        if event.type == 'TIMER':
            if self.stop or not self.strips:
                bpy.app.handlers.render_init.remove(self._init)
                bpy.app.handlers.render_complete.remove(self._complete)
                bpy.app.handlers.render_cancel.remove(self._cancel)
                bpy.context.window_manager.event_timer_remove(self._timer)
                # revert to original
                bpy.context.scene.camera = self.camera
                bpy.context.scene.frame_start = self.frame_start
                bpy.context.scene.frame_end = self.frame_end
                bpy.context.scene.render.filepath = self.path
                return {"FINISHED"} 

            elif self.rendering is False:
                path,(cam, frame_start, frame_end) = list(self.strips.items())[0]
                sc = bpy.context.scene
                sc.camera = bpy.data.objects[cam]
                sc.frame_start = frame_start
                sc.frame_end = frame_end
                sc.render.filepath = self.path + path
                sc.render.filepath += "/" if self.separate_dir else "."
                bpy.ops.render.render("INVOKE_DEFAULT", animation=True)

        return {"PASS_THROUGH"}


def get_cameras(self, context):
    cameras = []
    for object in context.scene.objects:
        if object.type == "CAMERA":
            cameras.append(object)
    return [(cam.name, cam.name, cam.name) for cam in cameras]


class RsStrip(bpy.types.PropertyGroup):

    def get_start(self):
        return self.get("start", 1)

    def set_start(self, value):
        self["start"] = value
        if self["start"] > self.get_end():
            self.set_end(self["start"])

    def get_end(self):
        return self.get("end", 1)

    def set_end(self, value):
        self["end"] = value
        if self["end"] < self.get_start():
            self.set_start(self["end"])

    enabled: bpy.props.BoolProperty(name="Enable", default=True)
    named: bpy.props.BoolProperty(name="Custom Name", default=False)
    name: bpy.props.StringProperty(name="Name", default="strip")
    cam: bpy.props.EnumProperty(name="Camera", items=get_cameras)
    start: bpy.props.IntProperty(name="Start Frame", get=get_start, set=set_start, min=1)
    end: bpy.props.IntProperty(name="End Frame", get=get_end, set=set_end, min=1)

    def draw(self, context, layout):
        layout.use_property_split = True

        # custom name
        row = layout.row(align=True, heading="Custom Name")
        row.use_property_decorate = False
        sub = row.row(align=True)
        sub.prop(self, "named", text="")
        subsub = sub.row(align=True)
        subsub.active = self.named
        subsub.prop(self, "name", text="")
        row.prop_decorator(self, "name")

        layout.prop(self, 'cam')
        layout.prop(self, 'start')
        layout.prop(self, 'end')

    def draw_list_item(self, context, layout):
        row = layout.row(align=True)
        row.prop(self, 'enabled', text="")
        if self.named:
            row.label(text=self.name)
        else:
            row.label(text="{}.{}-{}".format(self.cam,self.start,self.end))


class RsSettings(bpy.types.PropertyGroup):
    separate_dir: bpy.props.BoolProperty(name="Separate Directories", description="Create separate directories for each strip", default=True)
    strips: bpy.props.CollectionProperty(type=RsStrip)
    active_index: bpy.props.IntProperty(default=0)


class RENDER_UL_render_strip_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        item.draw_list_item(context, layout)


class RENDER_PT_render_strip(bpy.types.Panel):
    """Creates a Panel in the scene context of the properties editor"""
    bl_label = "Render Strip"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.template_list("RENDER_UL_render_strip_list", "", context.scene.rs_settings, "strips", context.scene.rs_settings, "active_index")
        col = row.column(align=True)
        col.operator('rs.newstrip', text="", icon='ADD')
        col.operator('rs.delstrip', text="", icon='REMOVE')

        index = context.scene.rs_settings.active_index
        strips = context.scene.rs_settings.strips

        if 0<=index and index<len(strips):
            active_strip = strips[index]
            active_strip.draw(context, layout.column())

        layout.separator()
        row = layout.row(align=True)
        row.operator("rs.renderbutton", text='Render')


class RENDER_PT_render_strip_settings(bpy.types.Panel):
    bl_label = "Output Settings"
    bl_parent_id = "RENDER_PT_render_strip"
    bl_options = {'DEFAULT_CLOSED'}
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"
    
    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(context.scene.render, "filepath")
        col.prop(context.scene.rs_settings, 'separate_dir')


class OBJECT_OT_NewStrip(bpy.types.Operator):
    """Add strip from current camera, start-end frame"""
    bl_idname = "rs.newstrip"
    bl_label = "New Strip"

    def execute(self, context):
        strip = context.scene.rs_settings.strips.add()
        if context.scene.camera:
            strip.cam = context.scene.camera.name 
        strip.start = context.scene.frame_start
        strip.end = context.scene.frame_end
        return {'FINISHED'}


class OBJECT_OT_DeleteStrip(bpy.types.Operator):
    """Delete the selected strip"""
    bl_idname = "rs.delstrip"
    bl_label = "Delete Strip"

    @classmethod
    def poll(cls, context):
        index = context.scene.rs_settings.active_index
        strips = context.scene.rs_settings.strips

        return 0<=index and index<len(strips)

    def execute(self, context):
        index = context.scene.rs_settings.active_index
        strips = context.scene.rs_settings.strips
        strip = context.scene.rs_settings.strips.remove(context.scene.rs_settings.active_index)
        if index==len(strips):
            context.scene.rs_settings.active_index = index-1
        return {'FINISHED'}


class OBJECT_OT_RenderButton(bpy.types.Operator):
    """Render all enabled strips"""
    bl_idname = "rs.renderbutton"
    bl_label = "Render Strip"

    def execute(self, context):
        if bpy.context.scene.render.filepath is None or len(bpy.context.scene.render.filepath)<1:
            ShowMessageBox(icon="ERROR", message="Output path not defined. Please, define the output path on the render settings panel")
            return {"FINISHED"}

        bpy.ops.render.renderstrip()
        return{'FINISHED'}
