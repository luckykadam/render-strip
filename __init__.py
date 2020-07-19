import bpy
from bpy.utils import register_class, unregister_class

from .render_strip import RenderStripOperator, RsStrip, RsSettings, RenderStripPanel, OBJECT_OT_NewStrip, OBJECT_OT_AddCurrentStrip, OBJECT_OT_RenderButton

bl_info = {
    "name": "Render Strip",
    "category": "Render",
    "blender": (2, 80, 0),
    "author" : "Lucky Kadam <luckykadam94@gmail.com>",
    "version" : (0, 0, 1),
    "description" :
            "Render camera strips",
}

classes = [RenderStripOperator, RsStrip, RsSettings, RenderStripPanel, OBJECT_OT_NewStrip, OBJECT_OT_AddCurrentStrip, OBJECT_OT_RenderButton]

def menu_func(self, context):
    self.layout.operator(OBJECT_OT_RenderButton.bl_idname)

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
