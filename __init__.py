import bpy
from bpy.utils import register_class, unregister_class

from .render_strip import RenderStripOperator, RsStrip, RsSettings, RENDER_UL_render_strip_list, RENDER_PT_render_strip, RENDER_PT_render_strip_detail, RENDER_PT_render_strip_settings, OBJECT_OT_NewStrip, OBJECT_OT_DeleteStrip, OBJECT_OT_PlayStrip, OBJECT_OT_CopyRenderSettings, OBJECT_OT_ApplyRenderSettings, OBJECT_MT_RenderSettingsMenu, OBJECT_OT_RenderStrip

bl_info = {
    "name": "Render Strip",
    "category": "Render",
    "blender": (2, 80, 0),
    "author" : "Lucky Kadam <luckykadam94@gmail.com>",
    "version" : (1, 0, 2),
    "description" : "Render camera strips",
}

classes = [RenderStripOperator, RsStrip, RsSettings, RENDER_UL_render_strip_list, RENDER_PT_render_strip, RENDER_PT_render_strip_detail, RENDER_PT_render_strip_settings, OBJECT_OT_NewStrip, OBJECT_OT_DeleteStrip, OBJECT_OT_PlayStrip, OBJECT_OT_CopyRenderSettings, OBJECT_OT_ApplyRenderSettings, OBJECT_MT_RenderSettingsMenu, OBJECT_OT_RenderStrip]

def menu_func(self, context):
    self.layout.operator(OBJECT_OT_RenderStrip.bl_idname, icon="RENDER_ANIMATION")

def register():
    for cls in classes:
        register_class(cls)

    bpy.types.Scene.rs_settings = bpy.props.PointerProperty(type=RsSettings)
    bpy.types.TOPBAR_MT_render.append(menu_func)

def unregister():
    for cls in classes:
        unregister_class(cls)

    bpy.types.TOPBAR_MT_render.remove(menu_func)

if __name__ == "__main__":
    register()
