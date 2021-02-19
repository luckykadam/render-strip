import bpy

def apply_render_settings(render_engine,resolution_x,resolution_y,resolution_percentage,pixel_aspect_x,pixel_aspect_y):
    bpy.context.scene.render.engine = render_engine
    bpy.context.scene.render.resolution_x = resolution_x
    bpy.context.scene.render.resolution_y = resolution_y
    bpy.context.scene.render.resolution_percentage = resolution_percentage
    bpy.context.scene.render.pixel_aspect_x = pixel_aspect_x
    bpy.context.scene.render.pixel_aspect_y = pixel_aspect_y

def copy_render_settings(strip):
    scene = bpy.context.scene
    strip.render_engine = scene.render.engine
    strip.resolution_x = scene.render.resolution_x
    strip.resolution_y = scene.render.resolution_y
    strip.resolution_percentage = scene.render.resolution_percentage
    strip.pixel_aspect_x = scene.render.pixel_aspect_x
    strip.pixel_aspect_y = scene.render.pixel_aspect_y

def get_available_render_engines():
    internal_engines = [("BLENDER_EEVEE","Eevee","Eevee"), ("BLENDER_WORKBENCH","Workbench","Workbench")]
    external_engines = set((e.bl_idname,e.bl_label,e.bl_label) for e in bpy.types.RenderEngine.__subclasses__())
    return internal_engines + list(external_engines)

def get_available_render_engines_values():
    return [e[0] for e in get_available_render_engines()]

def ShowMessageBox(message = "", title = "Message Box", icon = 'INFO'):

    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)
