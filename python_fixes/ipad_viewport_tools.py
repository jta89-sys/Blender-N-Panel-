# SPDX-License-Identifier: GPL-3.0-or-later
"""Optional viewport-only controls for an experimental Blender iPad bundle."""
import bpy
from bpy.props import EnumProperty
_saved = {}

def views():
    for wm in bpy.data.window_managers:
        for window in wm.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    yield area, area.spaces.active

def apply_profile(profile):
    count = 0
    for area, space in views():
        shading = space.shading
        key = space.as_pointer()
        if key not in _saved:
            _saved[key] = (space, {name:getattr(shading,name) for name in ('type','light','show_shadows','show_cavity')}, space.overlay.show_overlays)
        shading.type = 'SOLID'
        shading.light = 'FLAT' if profile == 'FAST' else 'STUDIO'
        shading.show_shadows = profile != 'FAST'
        shading.show_cavity = False
        if profile == 'FAST': space.overlay.show_overlays = False
        area.tag_redraw();count += 1
    return count

def restore_profile():
    count = 0
    for space, fields, overlays in list(_saved.values()):
        try:
            for name,value in fields.items():setattr(space.shading,name,value)
            space.overlay.show_overlays = overlays;count += 1
        except (ReferenceError,RuntimeError):pass
    _saved.clear()
    for area,space in views():area.tag_redraw()
    return count

class IPAD_OT_viewport(bpy.types.Operator):
    bl_idname = 'ipad.viewport_profile'
    bl_label = 'iPad Viewport Profile'
    profile: EnumProperty(items=[('BALANCED','Balanced','Solid studio shading without cavity'),('FAST','Fast','Flat solid shading with shadows, cavity and overlays off'),('RESTORE','Restore','Restore views changed during this session')])
    def execute(self,context):
        count = restore_profile() if self.profile == 'RESTORE' else apply_profile(self.profile)
        self.report({'INFO'},f'{self.profile.title()}: {count} viewport(s). Final render settings unchanged.')
        return {'FINISHED'}

class IPAD_MT_viewport(bpy.types.Menu):
    bl_idname='IPAD_MT_viewport'
    bl_label='iPad Viewport'
    def draw(self,context):
        for profile,label in [('BALANCED','Balanced Viewport'),('FAST','Fast Viewport'),('RESTORE','Restore Previous Viewports')]:
            self.layout.operator('ipad.viewport_profile',text=label).profile=profile

class IPAD_PT_viewport(bpy.types.Panel):
    bl_idname='IPAD_PT_viewport';bl_label='iPad Viewport';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='iPad'
    def draw(self,context):
        self.layout.label(text='Viewport only; render settings stay unchanged.')
        for profile,label in [('BALANCED','Balanced'),('FAST','Fast'),('RESTORE','Restore')]:
            self.layout.operator('ipad.viewport_profile',text=label).profile=profile

def draw_menu(self,context):self.layout.menu('IPAD_MT_viewport')
classes=(IPAD_OT_viewport,IPAD_MT_viewport,IPAD_PT_viewport)
def register():
    for cls in classes:bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_editor_menus.append(draw_menu)
def unregister():
    bpy.types.TOPBAR_MT_editor_menus.remove(draw_menu)
    restore_profile()
    for cls in reversed(classes):bpy.utils.unregister_class(cls)
