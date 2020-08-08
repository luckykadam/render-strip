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
            if any(strip.cam not in scene.objects or scene.objects[strip.cam].type != "CAMERA" for strip in scene.rs_settings.strips):
                raise Exception("Invalid Camera in strips!")
            self.strips = OrderedDict({
                "{}.{}-{}".format(strip.cam,strip.start,strip.end): (strip.cam, strip.start,strip.end)
                for strip in bpy.context.scene.rs_settings.strips
                if strip.enabled and not strip.deleted and bpy.context.scene.objects[strip.cam].type == "CAMERA"
            })

            if len(self.strips) < 0:
                raise Exception("No strip defined")

            self.camera = scene.camera
            self.frame_start = scene.frame_start
            self.frame_end = scene.frame_end
            self.path = scene.render.filepath

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
                sc.render.filepath = self.path + path + "/"
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
    cam: bpy.props.EnumProperty(name="Camera", items=get_cameras)
    start: bpy.props.IntProperty(name="Start Frame", get=get_start, set=set_start, min=1)
    end: bpy.props.IntProperty(name="End Frame", get=get_end, set=set_end, min=1)
    deleted: bpy.props.BoolProperty(name="Delete Strip", default=False)

    def draw(self, context, layout):
        row = layout.row(align=True)
        row.prop(self, 'enabled', text="")
        row = layout.row(align=True)
        row.prop(self, 'cam', text="")
        row.scale_x = 2
        row = layout.row(align=True)
        row.prop(self, 'start', text="")
        row.prop(self, 'end', text="")
        row = layout.row(align=True)
        row.prop(self, 'deleted', text="", icon="TRASH", emboss=False)


class RsSettings(bpy.types.PropertyGroup):
    strips: bpy.props.CollectionProperty(type=RsStrip)


class RenderStripPanel(bpy.types.Panel):
    """Creates a Panel in the scene context of the properties editor"""
    bl_label = "Render Strip"
    bl_idname = "SCENE_PT_layout"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"

    def draw(self, context):
        layout = self.layout
        for strip in context.scene.rs_settings.strips:
            if not strip.deleted:
                row = layout.row()
                strip.draw(strip, row)
        row = layout.row(align=True)
        row.operator('rs.newstrip', icon='ADD')
        row.operator('rs.addcurrentstrip')
        row = layout.row()
        row.operator("rs.renderbutton", text='Render')


class OBJECT_OT_NewStrip(bpy.types.Operator):
    """Add a new strip"""
    bl_idname = "rs.newstrip"
    bl_label = "New Strip"

    def execute(self, context):
        strip = context.scene.rs_settings.strips.add()
        return {'FINISHED'}


class OBJECT_OT_AddCurrentStrip(bpy.types.Operator):
    """Add strip from current camera, start-end frame"""
    bl_idname = "rs.addcurrentstrip"
    bl_label = "Add Current Strip"

    def execute(self, context):
        strip = context.scene.rs_settings.strips.add()
        if context.scene.camera:
            strip.cam = context.scene.camera.name 
        strip.start = context.scene.frame_start
        strip.end = context.scene.frame_end
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
