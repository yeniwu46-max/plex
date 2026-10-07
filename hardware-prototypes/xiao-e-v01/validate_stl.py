"""Validate the actual exported binary STL independently of Blender's mesh audit."""
from pathlib import Path
import struct
import json
import numpy as np

root = Path(__file__).resolve().parent
path = root / 'XiaoE_v01_160mm_print-study.stl'
with path.open('rb') as f:
    header = f.read(80)
    count = struct.unpack('<I', f.read(4))[0]
dtype = np.dtype([('normal', '<f4', (3,)), ('vertices', '<f4', (3, 3)), ('attribute', '<u2')])
data = np.fromfile(path, dtype=dtype, offset=84)
assert path.stat().st_size == 84+50*count
assert len(data) == count
points = data['vertices'].reshape(-1, 3)
assert np.isfinite(points).all()
vertices, inverse = np.unique(points, axis=0, return_inverse=True)
faces = inverse.reshape(-1, 3)
edges = np.concatenate((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]))
edges.sort(axis=1)
_, counts = np.unique(edges, axis=0, return_counts=True)
cross = np.cross(data['vertices'][:, 1]-data['vertices'][:, 0],
                 data['vertices'][:, 2]-data['vertices'][:, 0])
zero_area = int(np.sum(np.linalg.norm(cross, axis=1) < 1e-9))
report = {
    'file': path.name,
    'file_bytes': path.stat().st_size,
    'triangle_count': count,
    'unique_vertices': len(vertices),
    'dimensions_mm': (vertices.max(axis=0)-vertices.min(axis=0)).tolist(),
    'z_min_mm': float(vertices[:, 2].min()),
    'edges_not_shared_by_exactly_two_triangles': int(np.sum(counts != 2)),
    'zero_area_triangles': zero_area,
    'finite_coordinates': True,
    'binary_stl_size_valid': True,
}
report['passed'] = bool(np.all(counts == 2) and zero_area == 0 and
                        abs(report['dimensions_mm'][2]-160) < .001 and
                        abs(report['z_min_mm']) < .001)
(root/'stl-export-audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
assert report['passed'], 'Export validation failed'
