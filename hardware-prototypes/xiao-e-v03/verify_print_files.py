"""Independently reopen delivered STL and 3MF files and reject invalid releases."""
from pathlib import Path
import sys,json,zipfile,xml.etree.ElementTree as ET,hashlib
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'_cad_deps'))
import numpy as np
import trimesh
parts=json.loads((ROOT/'parts.json').read_text(encoding='utf-8'))
audit=json.loads((ROOT/'geometry-audit.json').read_text(encoding='utf-8'))
for key in ['neutral_intersections','reference_hardware_intersections','reference_hardware_pair_intersections','sampled_motion_intersections']:
    assert not audit[key],f'Unresolved collision: {key}'
ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
results=[]
for p in parts:
    path=ROOT/'stl'/(p['id']+'.stl')
    mesh=trimesh.load_mesh(path,process=True)
    assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0,p['id']
    assert len(mesh.split())==1,p['id']
    assert abs(mesh.bounds[0,2])<1e-4,p['id']
    with zipfile.ZipFile(ROOT/'3mf'/(p['id']+'.3mf')) as z:
        assert z.testzip() is None,p['id']
        root=ET.fromstring(z.read('3D/3dmodel.model'))
        assert root.attrib['unit']=='millimeter',p['id']
        vertices=np.array([[float(v.attrib[k]) for k in ('x','y','z')] for v in root.findall('.//m:vertex',ns)])
        faces=np.array([[int(f.attrib[k]) for k in ('v1','v2','v3')] for f in root.findall('.//m:triangle',ns)])
        assert faces.min()>=0 and faces.max()<len(vertices)
        m3=trimesh.Trimesh(vertices=vertices,faces=faces,process=True)
        assert m3.is_watertight and m3.is_winding_consistent and m3.volume>0
        assert len(m3.split())==1
        assert np.allclose(m3.bounds,mesh.bounds,atol=1e-4)
        assert abs(m3.volume-mesh.volume)<max(.01,mesh.volume*1e-5)
    results.append({'id':p['id'],'stl_and_3mf':'PASS','dimensions_mm':mesh.extents.tolist(),
                    'stl_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
report={'result':'PASS','stl_files':len(results),'three_mf_files':len(results),
        'units':'mm; 3MF explicitly declares millimeters, STL requires mm on import',
        'checks':'Reopened: one connected solid, watertight, consistent winding, positive volume, minimum Z zero, XML units and bounds/volume agreement. All modeled collision lists empty.',
        'not_checked':'Printer profile, actual slicing, support removal, real hardware fit, continuous motion, stiffness, durability, electronics or safety certification.',
        'parts':results}
(ROOT/'file-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS:',len(results),'STL and',len(results),'3MF files; all modeled collision lists empty.')
