"""Create bounded print and editable packages; excludes installed dependencies."""
from pathlib import Path
import json,zipfile,hashlib
root=Path(__file__).resolve().parent
for report in ['file-validation.json','blender-validation.json']:
    assert json.loads((root/report).read_text(encoding='utf-8'))['result']=='PASS',report
audit=json.loads((root/'geometry-audit.json').read_text(encoding='utf-8'))
for key in ['neutral_intersections','reference_hardware_intersections','reference_hardware_pair_intersections','sampled_motion_intersections']:assert not audit[key]
common=['README.md','parts-list.csv','parts.json','geometry-audit.json','file-validation.json']
print_files=[root/p for p in common]
for folder in ['stl','3mf','previews']:print_files+=sorted((root/folder).glob('*'))
editable=print_files+[root/p for p in ['XiaoE_v03_assembly.blend','XiaoE_v03_exploded.blend','build_mechanical.py','build_blender.py','verify_print_files.py','check_blender.py','package_release.py','blender-validation.json','hardware-reference.json']]
for folder in ['assembly_meshes','reference_only_DO_NOT_PRINT']:editable+=sorted((root/folder).glob('*.stl'))
records=[]
for name,files in [('XiaoE_v03_PRINT_PACKAGE.zip',print_files),('XiaoE_v03_EDITABLE_SOURCE.zip',editable)]:
    path=root/name
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as out:
        for file in files:
            assert file.is_file(),file
            out.write(file,file.relative_to(root).as_posix())
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(files)
    records.append({'file':name,'bytes':path.stat().st_size,'entries':len(files),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
(root/'release-manifest.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print(json.dumps(records,indent=2))
