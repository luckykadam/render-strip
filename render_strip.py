import bpy
import os

def ShowMessageBox(message = "", title = "Message Box", icon = 'INFO'):

    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)


class RenderStripOperator(bpy.types.Operator):
    """Render all strips"""
    bl_idname = "render.renderstrip"
    bl_label = "Render Strip"

    _timer = None
    shots = None
    stop = None
    rendering = None
    frame = 1
    path = "//"

    def pre(self, dummy, thrd = None):
        self.rendering = True

    def post(self, dummy, thrd = None):
        self.shots.pop(0) 
        self.rendering = False
        bpy.context.scene.render.filepath = self.path
        bpy.context.scene.frame_set(self.frame)

    def cancelled(self, dummy, thrd = None):
        self.stop = True

    def execute(self, context):
        self.stop = False
        self.rendering = False
        scene = bpy.context.scene
        wm = bpy.context.window_manager
        strips = {strip.cam: (strip.start, strip.end+1) for strip in bpy.context.window_manager.rs_settings.strips if strip.enabled}
        self.shots = [ (cam,frame) for cam,frame_range in strips.items() for frame in range(*frame_range)]

        if len(self.shots) < 0:
            self.report({"WARNING"}, 'No cameras defined')
            return {"FINISHED"}
        self.frame = bpy.context.scene.frame_current
        self.path = bpy.context.scene.render.filepath

        bpy.app.handlers.render_pre.append(self.pre)
        bpy.app.handlers.render_post.append(self.post)
        bpy.app.handlers.render_cancel.append(self.cancelled)

        self._timer = bpy.context.window_manager.event_timer_add(0.5, window=bpy.context.window)
        bpy.context.window_manager.modal_handler_add(self)

        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type == 'TIMER':
            if self.stop or not self.shots :
                bpy.app.handlers.render_pre.remove(self.pre)
                bpy.app.handlers.render_post.remove(self.post)
                bpy.app.handlers.render_cancel.remove(self.cancelled)
                bpy.context.window_manager.event_timer_remove(self._timer)

                return {"FINISHED"} 

            elif self.rendering is False:
                cam,frame = self.shots[0]
                bpy.context.scene.frame_set(frame)
                sc = bpy.context.scene
                sc.camera = bpy.data.objects[cam]
                sc.render.filepath = self.path + cam + "/" + str(frame)
                bpy.ops.render.render("INVOKE_DEFAULT", write_still=True)

        return {"PASS_THROUGH"}


def getcameras(self, context):
    cameras = []
    for object in context.scene.objects:
        if object.type == "CAMERA":
            cameras.append(object)
    return [(cam.name, cam.name, cam.name) for cam in cameras]


class RsStrip(bpy.types.PropertyGroup):
    enabled = bpy.props.BoolProperty(default=True)
    cam = bpy.props.EnumProperty(items = getcameras)
    start = bpy.props.IntProperty(min=1, default=1)
    end = bpy.props.IntProperty(min=1, default=1)

    def draw(self, context, layout):
        row = layout.row(align=True)
        row.prop(self, 'enabled', text="")
        row.prop(self, 'cam', text="")
        row = layout.row(align=True)
        row.prop(self, 'start', text="")
        row.prop(self, 'end', text="")

# ui part
class RsSettings(bpy.types.PropertyGroup):
    strips = bpy.props.CollectionProperty(type=RsStrip)


class RenderStripPanel(bpy.types.Panel):
    """Creates a Panel in the scene context of the properties editor"""
    bl_label = "Render Strip"
    bl_idname = "SCENE_PT_layout"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"

    def draw(self, context):
        wm = context.window_manager
        # row.prop(wm.rs_settings, "strips")
        for strip in wm.rs_settings.strips:
            row = self.layout.row()
            strip.draw(strip, row)
        row = self.layout.row()
        row.operator('rs.addstrip', text='Add Strip')
        row = self.layout.row()
        row.operator("rs.renderbutton", text='Render!')


class OBJECT_OT_AddStrip(bpy.types.Operator):
    bl_idname = "rs.addstrip"
    bl_label = "Add Strip"

    def execute(self, context):
        wm = context.window_manager
        strip = wm.rs_settings.strips.add()
        return {'FINISHED'}


class OBJECT_OT_RenderButton(bpy.types.Operator):
    bl_idname = "rs.renderbutton"
    bl_label = "Render Strip"

    #@classmethod
    #def poll(cls, context):
    #    return True
 
    def execute(self, context):
        if bpy.context.scene.render.filepath is None or len(bpy.context.scene.render.filepath)<1:
            self.report({"ERROR"}, 'Output path not defined. Please, define the output path on the render settings panel')
            return {"FINISHED"}

        animation_formats = [ 'FFMPEG', 'AVI_JPEG', 'AVI_RAW', 'FRAMESERVER' ]

        if bpy.context.scene.render.image_settings.file_format in animation_formats:
            self.report({"ERROR"}, 'Animation formats are not supported. Yet :)')
            return {"FINISHED"}

        bpy.ops.render.renderstrip()
        return{'FINISHED'}
