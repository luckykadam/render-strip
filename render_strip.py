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
    render_engine = None
    samples = None
    resolution_x = None
    resolution_y = None
    resolution_percentage = None
    pixel_aspect_x = None
    pixel_aspect_y = None

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
            if not all(strip.name for strip in active_strips):
                raise Exception("Invalid Name in strips!")
            self.strips = OrderedDict({
                strip.name: strip
                for strip in active_strips
            })

            if len(self.strips) < 0:
                raise Exception("No strip defined")

            self.camera = scene.camera
            self.frame_start = scene.frame_start
            self.frame_end = scene.frame_end
            self.path = scene.render.filepath
            self.render_engine = scene.render.engine
            if scene.render.engine=="BLENDER_EEVEE":
                self.samples = scene.eevee.taa_render_samples
            elif scene.render.engine=="CYCLES":
                self.samples = scene.cycles.samples
            self.resolution_x = scene.render.resolution_x
            self.resolution_y = scene.render.resolution_y
            self.resolution_percentage = scene.render.resolution_percentage
            self.pixel_aspect_x = scene.render.pixel_aspect_x
            self.pixel_aspect_y = scene.render.pixel_aspect_y

            bpy.app.handlers.render_init.append(self._init)
            bpy.app.handlers.render_complete.append(self._complete)
            bpy.app.handlers.render_cancel.append(self._cancel)

            self._timer = bpy.context.window_manager.event_timer_add(0.5, window=bpy.context.window)
            bpy.context.window_manager.modal_handler_add(self)

            return {"RUNNING_MODAL"}
        except Exception as e:
            ShowMessageBox(icon="ERROR", message=str(e))
            return {"CANCELLED"}


    def apply_render_settings(self, render_engine,samples,resolution_x,resolution_y,resolution_percentage,pixel_aspect_x,pixel_aspect_y):
        bpy.context.scene.render.engine = render_engine
        if render_engine=="BLENDER_EEVEE":
            bpy.context.scene.eevee.taa_render_samples = samples
        elif render_engine=="CYCLES":
            bpy.context.scene.cycles.samples = samples
        bpy.context.scene.render.resolution_x = resolution_x
        bpy.context.scene.render.resolution_y = resolution_y
        bpy.context.scene.render.resolution_percentage = resolution_percentage
        bpy.context.scene.render.pixel_aspect_x = pixel_aspect_x
        bpy.context.scene.render.pixel_aspect_y = pixel_aspect_y

    def apply_default_render_settings(self):
        self.apply_render_settings(self.render_engine,self.samples,self.resolution_x,self.resolution_y,self.resolution_percentage,self.pixel_aspect_x,self.pixel_aspect_y)

    def apply_strip_render_settings(self, strip):
        self.apply_render_settings(strip.render_engine,strip.samples,strip.resolution_x,strip.resolution_y,strip.resolution_percentage,strip.pixel_aspect_x,strip.pixel_aspect_y)


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
                self.apply_default_render_settings()
                return {"FINISHED"}

            elif self.rendering is False:
                path,strip = list(self.strips.items())[0]
                sc = bpy.context.scene
                sc.camera = bpy.data.objects[strip.cam]
                sc.frame_start = strip.start
                sc.frame_end = strip.end
                sc.render.filepath = self.path + path
                sc.render.filepath += "/" if sc.rs_settings.separate_dir else "."
                print("path: {}, {}".format(sc.render.filepath, path))
                if strip.custom_render:
                    self.apply_strip_render_settings(strip)
                else:
                    self.apply_default_render_settings()
                bpy.ops.render.render("INVOKE_DEFAULT", animation=True)

        return {"PASS_THROUGH"}


def get_cameras(self, context):
    cameras = []
    for object in context.scene.objects:
        if object.type == "CAMERA":
            cameras.append(object)
    return [(cam.name, cam.name, cam.name) for cam in cameras]

def get_render_engines(self, context):
    # return [("BLENDER_EEVEE","Eevee","Eevee"), ("BLENDER_WORKBENCH","Workbench","Workbench"), ("CYCLES","Cycles","Cycles")]
    return [("BLENDER_EEVEE","Eevee","Eevee"), ("CYCLES","Cycles","Cycles")]


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
    name: bpy.props.StringProperty(name="Name", default="strip")
    cam: bpy.props.EnumProperty(name="Camera", items=get_cameras)
    start: bpy.props.IntProperty(name="Start Frame", get=get_start, set=set_start, min=1)
    end: bpy.props.IntProperty(name="End Frame", get=get_end, set=set_end, min=1)

    # render settings
    custom_render: bpy.props.BoolProperty(name="Custom Render settings", default=False)
    render_engine: bpy.props.EnumProperty(name="Render Engine", items=get_render_engines)
    samples: bpy.props.IntProperty(name="Samples", default=128, min=1)
    resolution_x: bpy.props.IntProperty(name="Resolution X", default=1920, min=4, subtype="PIXEL")
    resolution_y: bpy.props.IntProperty(name="Resolution Y", default=1080, min=4, subtype="PIXEL")
    resolution_percentage: bpy.props.FloatProperty(name="Resolution %", default=100, min=1, max=100, subtype="PERCENTAGE")
    pixel_aspect_x: bpy.props.FloatProperty(name="Aspect X", default=1, min=1, max=200)
    pixel_aspect_y: bpy.props.FloatProperty(name="Aspect Y", default=1, min=1, max=200)


    def draw(self, context, layout):
        row = layout.row()

        cam_field = row.row(align=True)
        cam_field.prop(self, 'cam', text="")
        cam_field.scale_x = 2
        frame_field = row.row(align=True)
        frame_field.prop(self, 'start', text="")
        frame_field.prop(self, 'end', text="")
        layout.separator()

        row = layout.row()
        row.prop(self, 'custom_render')

        if self.custom_render:
            col = layout.column()
            col.use_property_split = True
            col.use_property_decorate = False

            col.prop(self, 'render_engine')
            col.prop(self, 'samples')
            
            subcol = col.column(align=True)
            subcol.prop(self, "resolution_x", text="Resolution X")
            subcol.prop(self, "resolution_y", text="Y")
            subcol.prop(self, "resolution_percentage", text="%")

            subcol = col.column(align=True)
            subcol.prop(self, "pixel_aspect_x", text="Aspect X")
            subcol.prop(self, "pixel_aspect_y", text="Y")


    def draw_list_item(self, context, layout):
        row = layout.row(align=True)
        row.prop(self, 'enabled', text="")
        row.prop(self, 'name', text="", emboss=False)
        row.label(text=self.cam)
        row.label(text="{}-{}".format(self.start,self.end))


class RsSettings(bpy.types.PropertyGroup):
    separate_dir: bpy.props.BoolProperty(name="Separate Directories", description="Create separate directories for each strip", default=True)
    strips: bpy.props.CollectionProperty(type=RsStrip)
    active_index: bpy.props.IntProperty(default=0)


class RENDER_UL_render_strip_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        item.draw_list_item(context, layout)


class RENDER_PT_render_strip(bpy.types.Panel):
    bl_label = "Render Strip"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.template_list("RENDER_UL_render_strip_list", "", context.scene.rs_settings, "strips", context.scene.rs_settings, "active_index")
        col = row.column()
        sub = col.column(align=True)
        sub.operator('rs.newstrip', text="", icon='ADD')
        sub.operator('rs.delstrip', text="", icon='REMOVE')
        sub = col.column(align=True)
        sub.operator('rs.playstrip', text="", icon='PLAY')
        # sub = col.column(align=True)
        # sub.operator('rs.renderstrip', text="", icon='RENDER_ANIMATION')

        row = layout.row()
        row.operator('rs.renderstrip', text="Render")


class RENDER_PT_render_strip_detail(bpy.types.Panel):
    bl_label = "Strip"
    bl_parent_id = "RENDER_PT_render_strip"
    bl_options = {'DRAW_BOX'}
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"

    def draw(self, context):
        layout = self.layout
        index = context.scene.rs_settings.active_index
        strips = context.scene.rs_settings.strips
        if 0<=index and index<len(strips):
            active_strip = strips[index]
            active_strip.draw(context, layout.column())
        else:
            layout.label(text="No active strip")


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
        context.scene.rs_settings.active_index = len(context.scene.rs_settings.strips)-1
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
        strips.remove(index)
        if index==len(strips):
            context.scene.rs_settings.active_index = index-1
        return {'FINISHED'}


class OBJECT_OT_PlayStrip(bpy.types.Operator):
    """Play the selected strip"""
    bl_idname = "rs.playstrip"
    bl_label = "Play Strip"

    @classmethod
    def poll(cls, context):
        index = context.scene.rs_settings.active_index
        strips = context.scene.rs_settings.strips
        return 0<=index and index<len(strips)

    def execute(self, context):
        index = context.scene.rs_settings.active_index
        strips = context.scene.rs_settings.strips
        strip = strips[index]
        if strip.cam:
            sc = bpy.context.scene
            sc.camera = bpy.data.objects[strip.cam]
            sc.frame_start = strip.start
            sc.frame_end = strip.end
            sc.frame_current = strip.start
            return {'FINISHED'}
        else:
            return {'CANELLED'}


class OBJECT_OT_RenderStrip(bpy.types.Operator):
    """Render all enabled strips"""
    bl_idname = "rs.renderstrip"
    bl_label = "Render Strip"

    def execute(self, context):
        if bpy.context.scene.render.filepath is None or len(bpy.context.scene.render.filepath)<1:
            ShowMessageBox(icon="ERROR", message="Output path not defined. Please, define the output path on the render settings panel")
            return {"FINISHED"}

        bpy.ops.render.renderstrip()
        return{'FINISHED'}
