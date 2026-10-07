"""PLEX Xiao E: editable display maquette + fused print study, Blender 5.1.

Run: blender --background --factory-startup --python build_xiao_e.py
Coordinates are millimetres. This is a first maquette, not a production enclosure.
"""
import bpy
import bmesh
import math
import json
import struct
from pathlib import Path
from mathutils import Vector, Quaternion

OUT = Path(__file__).resolve().parent
OUT.mkdir(parents=True, exist_ok=True)
PREVIEW = OUT / 'previews'
PREVIEW.mkdir(exist_ok=True)
TARGET_HEIGHT = 160.0
VOXEL_MM = 0.30

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 0.001
scene.unit_settings.length_unit = 'MILLIMETERS'
scene.render.engine = 'CYCLES'
scene.cycles.samples = 48
scene.cycles.use_denoising = True
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    for device in prefs.devices:
        device.use = device.type == 'OPTIX'
    if any(d.use for d in prefs.devices):
        scene.cycles.device = 'GPU'
except Exception as err:
    print('GPU setup, using default if unavailable:', err, flush=True)
scene.render.resolution_x = 1400
scene.render.resolution_y = 1400
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'AgX'
scene.render.film_transparent = False

model = bpy.data.collections.new('01_XIAO_E_EDITABLE')
scene.collection.children.link(model)
studio = bpy.data.collections.new('02_STUDIO')
scene.collection.children.link(studio)
print_collection = bpy.data.collections.new('03_PRINT_STUDY_HIDDEN')
scene.collection.children.link(print_collection)

def move_to(obj, coll):
    for existing in list(obj.users_collection):
        existing.objects.unlink(obj)
    coll.objects.link(obj)

def material(name, rgb, roughness=.34, metal=0, emission=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*rgb, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*rgb, 1)
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = metal
    if emission:
        bsdf.inputs['Emission Color'].default_value = (*rgb, 1)
        bsdf.inputs['Emission Strength'].default_value = emission
    return mat

pearl = material('Shell | warm porcelain white', (.78, .83, .84), .29, .04)
cape_white = material('Cape | satin white', (.67, .75, .76), .43)
dark = material('Joints | deep graphite', (.013, .028, .035), .38)
glass = material('Visor | obsidian glass', (.006, .014, .020), .19, .18)
teal = material('Trim | PLEX teal', (.008, .42, .34), .30, .12)
cyan = material('Expression | turquoise', (.04, .85, .76), .25, .04, .20)
cape_inner = material('Cape lining | dark petrol', (.015, .115, .13), .46)
base_mat = material('Base | midnight slate', (.016, .043, .053), .39, .15)
silver = material('Trim | silver', (.31, .43, .47), .28, .6)
ground_mat = material('Studio | blue grey', (.046, .073, .087), .62)

def finish(obj, name, mat, coll=model):
    obj.name = name
    move_to(obj, coll)
    if mat:
        obj.data.materials.append(mat)
    if obj.type == 'MESH':
        for p in obj.data.polygons:
            p.use_smooth = True
    return obj

def apply_transform(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

def mesh_obj(name, verts, faces, mat):
    mesh = bpy.data.meshes.new(name + '_mesh')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    # Recalculate normals, including independently closed custom surfaces.
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    model.objects.link(obj)
    return finish(obj, name, mat)

def sgnpow(v, power):
    return math.copysign(abs(v)**power, v)

def superellipsoid(name, loc, scale, mat, e1=.8, e2=.8, nu=96, nv=48):
    verts = [(0, 0, -scale[2])]
    for j in range(1, nv):
        phi = -math.pi/2 + math.pi*j/nv
        cp, sp = sgnpow(math.cos(phi), e1), sgnpow(math.sin(phi), e1)
        for i in range(nu):
            theta = 2*math.pi*i/nu
            verts.append((scale[0]*cp*sgnpow(math.cos(theta), e2),
                          scale[1]*cp*sgnpow(math.sin(theta), e2), scale[2]*sp))
    top = len(verts)
    verts.append((0, 0, scale[2]))
    faces = []
    for i in range(nu):
        faces.append((0, 1+(i+1)%nu, 1+i))
    for j in range(nv-2):
        a, b = 1+j*nu, 1+(j+1)*nu
        for i in range(nu):
            faces.append((a+i, a+(i+1)%nu, b+(i+1)%nu, b+i))
    last = 1+(nv-2)*nu
    for i in range(nu):
        faces.append((last+i, last+(i+1)%nu, top))
    obj = mesh_obj(name, verts, faces, mat)
    obj.location = loc
    return obj

def ellipsoid(name, loc, scale, mat):
    return superellipsoid(name, loc, scale, mat, 1, 1, 64, 32)

def cylinder(name, loc, radius, depth, mat, axis='Z', bevel=.8):
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=radius, depth=depth, location=loc)
    obj = finish(bpy.context.object, name, mat)
    if axis == 'X':
        obj.rotation_euler[1] = math.pi/2
    elif axis == 'Y':
        obj.rotation_euler[0] = math.pi/2
    if bevel:
        mod = obj.modifiers.new('Soft manufactured edge', 'BEVEL')
        mod.width = bevel
        mod.segments = 4
        norm = obj.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    return obj

def torus(name, loc, radius, tube, mat, axis='Z'):
    bpy.ops.mesh.primitive_torus_add(major_radius=radius, minor_radius=tube,
                                   major_segments=96, minor_segments=16, location=loc)
    obj = finish(bpy.context.object, name, mat)
    if axis == 'X':
        obj.rotation_euler[1] = math.pi/2
    elif axis == 'Y':
        obj.rotation_euler[0] = math.pi/2
    return obj

def tube_path(name, points, radius, mat, smooth=False, cyclic=False):
    data = bpy.data.curves.new(name, 'CURVE')
    data.dimensions = '3D'
    data.resolution_u = 16
    data.bevel_depth = radius
    data.bevel_resolution = 4
    data.use_fill_caps = True
    spline = data.splines.new('BEZIER' if smooth else 'POLY')
    if smooth:
        spline.bezier_points.add(len(points)-1)
        for p, co in zip(spline.bezier_points, points):
            p.co = co
            p.handle_left_type = p.handle_right_type = 'AUTO'
    else:
        spline.points.add(len(points)-1)
        for p, co in zip(spline.points, points):
            p.co = (*co, 1)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, data)
    model.objects.link(obj)
    data.materials.append(mat)
    return obj

def capsule_between(name, a, b, radius, mat, squash=1):
    mid = (Vector(a)+Vector(b))/2
    length = (Vector(b)-Vector(a)).length
    obj = ellipsoid(name, mid, (radius, radius*squash, length/2+radius*.60), mat)
    obj.rotation_euler = (Vector(b)-Vector(a)).to_track_quat('Z', 'Y').to_euler()
    return obj

def star_outline(name, center, radius, mat, tube=.8, plane='FRONT'):
    # A four-point navigation star: raised geometry survives monochrome printing.
    pts = []
    for i in range(8):
        ang = math.pi/2 + i*math.pi/4
        r = radius if i%2 == 0 else radius*.30
        x, z = r*math.cos(ang), r*math.sin(ang)
        pts.append((center[0]+x, center[1], center[2]+z))
    return tube_path(name, pts, tube, mat, cyclic=True)

# Low plinth and two firmly planted feet.
cylinder('Base / plinth', (0, 0, 3.4), 46, 6.8, base_mat, bevel=1.6)
torus('Base / orbit inlay', (0, 0, 6.70), 40.5, .50, teal)
for side, sign in [('L', -1), ('R', 1)]:
    superellipsoid('Boot '+side, (sign*13, -3, 13.2), (10, 14, 8.1), dark, .7, .7)
    leg = ellipsoid('Leg shell '+side, (sign*12.3, 0, 26.4), (10.7, 11.6, 17), pearl)
    leg.rotation_euler[1] = sign*-.10

superellipsoid('Torso / rounded suit', (0, 0, 50), (23, 16.6, 25), pearl, .83, .83)
cylinder('Neck / dark flexible seal', (0, 0, 76), 12, 13, dark, bevel=1.3)
cylinder('Neck / collar support', (0, 0, 74), 18, 5.0, cape_white, bevel=1.0)

# The head is intentionally large and softly squared, matching the reference.
superellipsoid('Head / ceramic helmet', (0, 0, 109), (44.5, 32, 37.5), pearl, .78, .76, 128, 64)
superellipsoid('Face / graphite gasket', (0, -27, 110), (36.5, 10.5, 27.7), dark, .54, .54)
superellipsoid('Face / curved black visor', (0, -29.2, 110), (34.5, 10.4, 25.4), glass, .54, .54)

# Closed-eye chevrons, physically embossed rather than texture-only.
for name, points in [
    ('L', [(-21, -39.25, 117), (-12.0, -39.65, 110), (-21, -39.25, 103)]),
    ('R', [(21, -39.25, 117), (12.0, -39.65, 110), (21, -39.25, 103)])]:
    tube_path('Expression / '+name+' chevron', points, 1.7, cyan)
    for j, pt in enumerate(points):
        ellipsoid('Expression / '+name+' round '+str(j), pt, (1.7, 1.7, 1.7), cyan)

for side, sign in [('L', -1), ('R', 1)]:
    cylinder('Ear '+side+' / body', (sign*43, 0, 110), 14, 10, pearl, 'X', 2)
    cylinder('Ear '+side+' / inset', (sign*48, 0, 110), 10.7, 2.0, dark, 'X', .6)
    torus('Ear '+side+' / teal ring', (sign*49.05, 0, 110), 8.25, 1.25, teal, 'X')
    cylinder('Ear '+side+' / center', (sign*49, 0, 110), 5.8, 1.8, cape_inner, 'X', .7)
    cylinder('Ear '+side+' / core', (sign*50.0, 0, 110), 2.8, .8, cyan, 'X', .35)

# Swept crest: broad connected fins with softened tips.
crest = ellipsoid('Crest / main swept fin', (0, 5, 150.0), (5.2, 11.5, 10.7), teal)
crest.rotation_euler[0] = -.40
crest2 = ellipsoid('Crest / trailing fin', (0, 13, 146.7), (4.4, 9, 6.0), teal)
crest2.rotation_euler[0] = -.30

for side, sign in [('L', -1), ('R', 1)]:
    ellipsoid('Shoulder joint '+side, (sign*21.2, 0, 61), (7.7, 8, 8), dark)
    capsule_between('Arm / upper '+side, (sign*21, -1, 62), (sign*31, -3, 55), 7.5, pearl)
    capsule_between('Arm / mitten '+side, (sign*31, -3, 55), (sign*39, -5, 51), 6.5, pearl)
    cuff = torus('Arm / cuff '+side, (sign*32, -3.1, 54.4), 5.7, .55, silver)
    cuff.rotation_euler = Vector((sign*1, -.20, -.55)).to_track_quat('Z', 'Y').to_euler()

# Closed cape, roughly 2.8 mm thick before final height normalization.
# The inner/outer skins are independently assigned satin / petrol materials.
NTH, NZ = 80, 28
def cape_point(t, theta, inner=False):
    radius_x = 16 + 29*t + 2.2*math.sin(math.pi*t)
    radius_y = 16 + 19*t
    fold = 1.5*(t**1.3)*math.cos(theta*6)
    x = (radius_x+fold)*math.sin(theta)
    y = (radius_y+fold)*math.cos(theta)
    z = 74.7 - 43*t + 5.3*(t**3)*abs(math.sin(theta)) + 1.8*t*t*math.cos(theta*4)
    if inner:
        x -= 2.8*math.sin(theta)
        y -= 2.8*math.cos(theta)
    return (x, y, z)

verts, faces, midx = [], [], []
for inner in [False, True]:
    for j in range(NZ+1):
        for i in range(NTH+1):
            verts.append(cape_point(j/NZ, -1.88+3.76*i/NTH, inner))
layer = (NTH+1)*(NZ+1)
for skin in range(2):
    off = skin*layer
    for j in range(NZ):
        for i in range(NTH):
            a = off+j*(NTH+1)+i
            faces.append((a, a+1, a+NTH+2, a+NTH+1))
            midx.append(skin)
for j in [0, NZ]:
    for i in range(NTH):
        a = j*(NTH+1)+i
        faces.append((a, a+1, a+1+layer, a+layer)); midx.append(0)
for i in [0, NTH]:
    for j in range(NZ):
        a = j*(NTH+1)+i
        faces.append((a, a+NTH+1, a+NTH+1+layer, a+layer)); midx.append(0)
cape = mesh_obj('Cape / closed thick shell', verts, faces, cape_white)
cape.data.materials.append(cape_inner)
for poly, idx in zip(cape.data.polygons, midx):
    poly.material_index = idx
tube_path('Cape / lower teal piping', [cape_point(1, -1.88+3.76*i/80) for i in range(81)], .70, teal)
for theta, label in [(-1.88, 'L'), (1.88, 'R')]:
    tube_path('Cape / edge '+label, [cape_point(j/28, theta) for j in range(29)], .65, teal)

# Two rounded collar leaves, connected to the neck and body.
for side, sign in [('L', -1), ('R', 1)]:
    obj = ellipsoid('Collar / leaf '+side, (sign*9, -12.5, 71), (12.0, 6.0, 4.8), cape_white)
    obj.rotation_euler[1] = sign*-.24
ellipsoid('Collar / clasp', (0, -18, 71.1), (2.5, 1.6, 2.5), teal)
star_outline('Torso / PLEX star', (0, -16.3, 53), 7, teal, .78)
ellipsoid('Torso / star core', (0, -17.0, 53), (1.6, .8, 1.6), cyan)
# Back badge follows the curved cape surface near its middle.
back_star_points = []
for i in range(8):
    ang = math.pi/2+i*math.pi/4
    r = 7.0 if i%2 == 0 else 2.2
    x, z = r*math.cos(ang), 51+r*math.sin(ang)
    t = (74.7-z)/43
    theta = math.asin(x/(16+29*t+2.2*math.sin(math.pi*t)))
    y = cape_point(t, theta)[1]
    back_star_points.append((x, y+.25, z))
tube_path('Cape / back navigation star', back_star_points, .85, teal, cyclic=True)

# Normalize the whole maquette (including plinth) to the declared height.
bpy.context.view_layer.update()
# Rotated bounding boxes overestimate a swept crest. Use actual evaluated vertices.
coords = []
initial_depsgraph = bpy.context.evaluated_depsgraph_get()
for obj in model.objects:
    evaluated = obj.evaluated_get(initial_depsgraph)
    evaluated_mesh = evaluated.to_mesh()
    coords.extend(obj.matrix_world @ vertex.co for vertex in evaluated_mesh.vertices)
    evaluated.to_mesh_clear()
zmin, zmax = min(p.z for p in coords), max(p.z for p in coords)
factor = TARGET_HEIGHT/(zmax-zmin)
for obj in model.objects:
    obj.location.z -= zmin
    obj.location *= factor
    obj.scale *= factor
    obj['prototype_role'] = 'Editable appearance part; overlapping assembly, not individually fitted.'
bpy.context.view_layer.update()
scene['project'] = 'PLEX / Xiao E / display maquette v0.1'
scene['reference'] = 'User-supplied character turnaround, 2026-09-17'
scene['target_height_mm'] = TARGET_HEIGHT
scene['status'] = 'Appearance prototype. No electronics, articulation or fit tolerances validated.'
scene['coordinate_convention'] = 'Millimetres; front is -Y; Z up.'

# Studio: broad softboxes, orthographic cameras and a matte floor.
bpy.ops.mesh.primitive_plane_add(size=20000, location=(0, 0, -.12))
floor = finish(bpy.context.object, 'Studio floor / NOT FOR PRINT', ground_mat, studio)
world = bpy.data.worlds.new('Studio world')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (.16, .21, .24, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = .45
scene.world = world

def area(name, loc, energy, size, color, target=(0, 0, 80)):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = energy
    data.shape = 'DISK'
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    studio.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

area('Key / large softbox', (-160, -210, 270), 950000, 170, (1, .93, .86))
area('Fill / cool softbox', (180, -100, 170), 650000, 140, (.67, .85, 1))
area('Rim / top rear', (30, 150, 240), 1100000, 135, (.67, 1, .94))

def camera(name, loc, target=(0, 0, 80), ortho=202):
    data = bpy.data.cameras.new(name)
    data.type = 'ORTHO'
    data.ortho_scale = ortho
    data.clip_end = 10000
    data.lens = 50
    obj = bpy.data.objects.new(name, data)
    studio.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    return obj

cameras = {
    'hero': camera('Camera / hero', (225, -340, 195), (0, 0, 80), 202),
    'front': camera('Camera / front', (0, -400, 80), (0, 0, 80), 193),
    'side': camera('Camera / right', (400, 0, 80), (0, 0, 80), 193),
    'back': camera('Camera / back', (0, 400, 80), (0, 0, 80), 193),
}
scene.camera = cameras['hero']

# Pack reference image for handoff (no external image path dependency).
refpath = Path('D:/Unity/Temp/codex-clipboard-154a5ec5-9940-4730-ab95-06d8ca17f1df.png')
if refpath.exists():
    ref = bpy.data.images.load(str(refpath))
    ref.name = 'REFERENCE / approved Xiao E concept sheet'
    ref.pack()

# Save editable scene BEFORE mesh fusion so it survives any expensive operation.
for screen in bpy.data.screens:
    for ar in screen.areas:
        if ar.type == 'VIEW_3D':
            ar.spaces.active.clip_end = 10000
            ar.spaces.active.region_3d.view_distance = 265
            ar.spaces.active.region_3d.view_location = (0, 0, 80)
            ar.spaces.active.region_3d.view_rotation = cameras['hero'].rotation_euler.to_quaternion()
            ar.spaces.active.shading.type = 'MATERIAL'
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'XiaoE_v01_editable.blend'))
print('EDITABLE_SAVED', flush=True)

for view in ['hero', 'front', 'side', 'back']:
    scene.camera = cameras[view]
    scene.render.resolution_x = 1400 if view == 'hero' else 1100
    scene.render.resolution_y = 1400 if view == 'hero' else 1100
    scene.render.filepath = str(PREVIEW/(view+'.png'))
    bpy.ops.render.render(write_still=True)
    print('RENDERED', view, flush=True)

# Bake evaluated geometry into a separate, unified single-colour printing study.
depsgraph = bpy.context.evaluated_depsgraph_get()
duplicates = []
for obj in list(model.objects):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = bpy.data.meshes.new_from_object(evaluated, depsgraph=depsgraph)
    dup = bpy.data.objects.new('print_'+obj.name, mesh)
    print_collection.objects.link(dup)
    dup.matrix_world = obj.matrix_world.copy()
    duplicates.append(dup)
bpy.ops.object.select_all(action='DESELECT')
for obj in duplicates:
    obj.select_set(True)
bpy.context.view_layer.objects.active = duplicates[0]
bpy.ops.object.join()
fused = bpy.context.object
fused.name = 'XiaoE / fused 160 mm print study'
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
remesh = fused.modifiers.new('Volume union / 0.30 mm', 'REMESH')
remesh.mode = 'VOXEL'
remesh.voxel_size = VOXEL_MM
remesh.use_smooth_shade = True
bpy.ops.object.modifier_apply(modifier=remesh.name)
print('REMESH_COMPLETE', len(fused.data.vertices), flush=True)

# Connectivity audit. Never silently discard disconnected character parts.
bm = bmesh.new()
bm.from_mesh(fused.data)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
bm.verts.ensure_lookup_table()
unvisited = set(bm.verts)
components = []
while unvisited:
    seed = unvisited.pop()
    stack, part = [seed], [seed]
    while stack:
        v = stack.pop()
        for edge in v.link_edges:
            other = edge.other_vert(v)
            if other in unvisited:
                unvisited.remove(other)
                stack.append(other)
                part.append(other)
    components.append(part)
components_before_cleanup = len(components)
removed_artifacts = []
kept_components = []
for part in components:
    lower = Vector(tuple(min(v.co[i] for v in part) for i in range(3)))
    upper = Vector(tuple(max(v.co[i] for v in part) for i in range(3)))
    # Only discard sub-voxel specks, never a separate modeled feature.
    if len(part) <= 16 and (upper-lower).length < .9:
        removed_artifacts.append({'vertices': len(part), 'bounds_mm': [list(lower), list(upper)],
                                  'reason': 'Tiny isolated voxel remeshing artifact, below 0.9 mm diagonal.'})
        bmesh.ops.delete(bm, geom=part, context='VERTS')
    else:
        kept_components.append(part)
components = kept_components
component_sizes = sorted([len(part) for part in components], reverse=True)
# Place the base exactly on Z=0 and normalize the final export height to 160 mm.
actual_min_z = min(v.co.z for v in bm.verts)
actual_max_z = max(v.co.z for v in bm.verts)
export_scale = TARGET_HEIGHT/(actual_max_z-actual_min_z)
for v in bm.verts:
    v.co.z -= actual_min_z
    v.co *= export_scale
nonmanifold = sum(not edge.is_manifold for edge in bm.edges)
volume = bm.calc_volume(signed=True)
bm.to_mesh(fused.data)
bm.free()
fused.data.materials.clear()
fused.data.materials.append(pearl)
for poly in fused.data.polygons:
    poly.material_index = 0
    poly.use_smooth = True
bpy.context.view_layer.update()

# Binary STL coordinates stay in mm (do not apply scene's metre conversion).
fused.data.calc_loop_triangles()
stl = OUT/'XiaoE_v01_160mm_print-study.stl'
with stl.open('wb') as out:
    out.write(b'PLEX Xiao E v0.1 | mm | display prototype | verify slicing'.ljust(80, b'\0'))
    out.write(struct.pack('<I', len(fused.data.loop_triangles)))
    for tri in fused.data.loop_triangles:
        n = tri.normal
        pts = [fused.matrix_world @ fused.data.vertices[i].co for i in tri.vertices]
        out.write(struct.pack('<12fH', *n, *(c for p in pts for c in p), 0))

report = {
    'artifact': stl.name,
    'units': 'mm',
    'target_height_mm': TARGET_HEIGHT,
    'actual_dimensions_mm': list(fused.dimensions),
    'vertices': len(fused.data.vertices),
    'triangles': len(fused.data.loop_triangles),
    'connected_components': len(components),
    'components_before_cleanup': components_before_cleanup,
    'removed_voxel_artifacts': removed_artifacts,
    'component_vertex_counts': component_sizes,
    'non_manifold_edges': nonmanifold,
    'signed_volume_mm3': volume,
    'voxel_union_mm': VOXEL_MM,
    'status': 'Digital geometry checked; machine/material/support/physical printing NOT validated.',
    'source_parts': len(list(model.objects)),
}
(OUT/'mesh-audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('AUDIT', json.dumps(report), flush=True)

# Standalone print .blend has no cameras or studio in its visible viewport.
model.hide_render = True
model.hide_viewport = True
studio.hide_viewport = True
scene.camera = cameras['hero']
scene.render.resolution_x = scene.render.resolution_y = 1100
scene.render.filepath = str(PREVIEW/'print-study.png')
bpy.ops.render.render(write_still=True)
floor.hide_render = True
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'XiaoE_v01_print-study.blend'))

# Preserve the original editable scene, with the fused print mesh tucked away.
model.hide_render = False
model.hide_viewport = False
studio.hide_viewport = False
floor.hide_render = False
print_collection.hide_render = True
print_collection.hide_viewport = True
scene.camera = cameras['hero']
scene.render.resolution_x = scene.render.resolution_y = 1400
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'XiaoE_v01_editable.blend'))
print('ALL_DONE', flush=True)
