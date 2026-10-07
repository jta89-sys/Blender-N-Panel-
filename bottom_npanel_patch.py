#!/usr/bin/env python3
"""Experimental native bottom sidebar patch. Run from checkout parent."""
from pathlib import Path

def transform(space, area):
    old = '  region->regiontype = RGN_TYPE_UI;\n  region->alignment = RGN_ALIGN_RIGHT;'
    new = old.replace('RGN_ALIGN_RIGHT', 'RGN_ALIGN_BOTTOM')
    assert space.count(old) == 1, 'Sidebar creation anchor changed'
    space = space.replace(old, new)
    old = '  art->prefsizex = UI_SIDEBAR_PANEL_WIDTH;'
    assert space.count(old) == 1
    space = space.replace(old, old + '\n  art->prefsizey = 240; /* Bottom sidebar initial height in UI units. */')
    old = '  region_rect_recursive(\n      area, static_cast<ARegion *>(area->regionbase.first), &rect, &overlap_rect, 0);'
    assert area.count(old) == 2, 'Region size update anchors changed'
    migration = """  /* iPad bottom N-panel: migrate startup and loaded .blend sidebars before sizing. */
  if (area->spacetype == SPACE_VIEW3D) {
    LISTBASE_FOREACH (ARegion *, sidebar, &area->regionbase) {
      if (sidebar->regiontype == RGN_TYPE_UI && sidebar->alignment != RGN_ALIGN_BOTTOM) {
        sidebar->alignment = RGN_ALIGN_BOTTOM;
        sidebar->sizey = 240;
      }
    }
  }
"""
    area = area.replace(old, migration + old)
    return space, area

if __name__ == '__main__':
    s = Path('blender/source/blender/editors/space_view3d/space_view3d.cc')
    a = Path('blender/source/blender/editors/screen/area.cc')
    st, at = transform(s.read_text(), a.read_text())
    s.write_text(st); a.write_text(at)
    print('Experimental bottom N-panel patch applied')
