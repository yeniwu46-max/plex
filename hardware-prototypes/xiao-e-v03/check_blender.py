"""Run against the saved assembly to check units, neutral placement and rig."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parent
parts=json.loads((root/'parts.json').read_text(encoding='utf-8'))
scene=bpy.context.scene
assert scene.unit_settings.system=='METRIC'
assert abs(scene.unit_settings.scale_length-.001)<1e-8
objects={o.get('part_id'):o for o in bpy.data.objects if o.get('part_id')}
checked=[]
for p in parts:
    obj=objects[p['id']]
    if not p['assembled']:continue
    pts=[obj.matrix_world@v.co for v in obj.data.vertices]
    bounds=[[min(v[i] for v in pts) for i in range(3)],[max(v[i] for v in pts) for i in range(3)]]
    err=max(abs(bounds[j][i]-p['assembly_bounds'][j][i]) for j in range(2) for i in range(3))
    assert err<.001,(p['id'],err)
    checked.append(p['id'])
ctrl=next(o for o in bpy.data.objects if o.name.startswith('CONTROLS'))
for key in ['J1_yaw_deg','J2_pitch_deg','J3_left_arm_deg','J4_right_arm_deg']:assert ctrl[key]==0
ctrl['J1_yaw_deg']=30;ctrl['J2_pitch_deg']=15;ctrl['J3_left_arm_deg']=45;ctrl['J4_right_arm_deg']=30
ctrl.update_tag();scene.frame_set(2);bpy.context.view_layer.update()
for name,index,degrees in [('J1 / yaw',2,30),('J2 / pitch',0,15),('J3 / left shoulder',1,45),('J4 / right shoulder',1,-30)]:
    assert abs(math.degrees(bpy.data.objects[name].rotation_euler[index])-degrees)<.001,name
result={'result':'PASS','assembled_print_parts':len(checked),'units':'millimeters','neutral_mesh_placements':'match CAD export within 0.001 mm','four_joint_controls':'evaluated correctly','saved_file_mutated':False}
(root/'blender-validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result),flush=True)
