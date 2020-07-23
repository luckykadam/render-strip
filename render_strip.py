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

    # help revert to original
    camera = None
    frame = None
    path = None

    def pre(self, dummy, thrd = None):
        self.rendering = True

    def post(self, dummy, thrd = None):
        self.shots.pop(0) 
        self.rendering = False

    def cancelled(self, dummy, thrd = None):
        self.stop = True

    def execute(self, context):
        try:
            self.stop = False
            self.rendering = False
            scene = bpy.context.scene
            strips = [(strip.cam,strip.start,strip.end) for strip in bpy.context.scene.rs_settings.strips if strip.enabled and not strip.deleted and bpy.context.scene.objects[strip.cam].type == "CAMERA"]
            self.shots = [(cam,"{}.{}-{}".format(cam,start,end),frame) for (cam,start,end) in strips for frame in range(start,end+1)]

            if len(self.shots) < 0:
                self.report({"WARNING"}, 'No cameras defined')
                return {"FINISHED"}

            self.camera = bpy.context.scene.camera
            self.frame = bpy.context.scene.frame_current
            self.path = bpy.context.scene.render.filepath

            bpy.app.handlers.render_pre.append(self.pre)
            bpy.app.handlers.render_post.append(self.post)
            bpy.app.handlers.render_cancel.append(self.cancelled)

            self._timer = bpy.context.window_manager.event_timer_add(0.5, window=bpy.context.window)
            bpy.context.window_manager.modal_handler_add(self)

            return {"RUNNING_MODAL"}
        except Exception as e:
            ShowMessageBox(message="Invalid camera in strips")
            return {"CANCELLED"}

    def modal(self, context, event):
        if event.type == 'TIMER':
            if self.stop or not self.shots :
                bpy.app.handlers.render_pre.remove(self.pre)
                bpy.app.handlers.render_post.remove(self.post)
                bpy.app.handlers.render_cancel.remove(self.cancelled)
                bpy.context.window_manager.event_timer_remove(self._timer)
                # revert to original
                bpy.context.scene.camera = self.camera
                bpy.context.scene.frame_set(self.frame)
                bpy.context.scene.render.filepath = self.path
                return {"FINISHED"} 

            elif self.rendering is False:
                cam,path,frame = self.shots[0]
                bpy.context.scene.frame_set(frame)
                sc = bpy.context.scene
                sc.camera = bpy.data.objects[cam]
                sc.render.filepath = self.path + path + "/" + str(frame)
                bpy.ops.render.render("INVOKE_DEFAULT", write_still=True)

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

    enabled: bpy.props.BoolProperty(default=True)
    cam: bpy.props.EnumProperty(items=get_cameras)
    start: bpy.props.IntProperty(get=get_start, set=set_start, min=1)
    end: bpy.props.IntProperty(get=get_end, set=set_end, min=1)
    deleted: bpy.props.BoolProperty(default=False)

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
        row.operator("rs.renderbutton", text='Render', icon='RENDER_ANIMATION')


class OBJECT_OT_NewStrip(bpy.types.Operator):
    bl_idname = "rs.newstrip"
    bl_label = "New Strip"

    def execute(self, context):
        strip = context.scene.rs_settings.strips.add()
        return {'FINISHED'}


class OBJECT_OT_AddCurrentStrip(bpy.types.Operator):
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
