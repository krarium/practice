"""7.2 패키지 ZIP 생성: python3 package_hyperion72.py (빌드·검사 후 실행)"""
from pathlib import Path
import zipfile
BASE = Path(__file__).resolve().parent
D = BASE / 'deliverables'
out = D / '히페리온_베이스7.2.zip'
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    for f in sorted((D / 'Hyperion_RailTurrets').iterdir()):
        z.write(f, f'LocalMods/Hyperion_RailTurrets/{f.name}')
    z.write(BASE / '히페리온_베이스7.2_사용법.md', '히페리온_베이스7.2_사용법.md')
    for n in ['static_check.txt', 'geometry_check.txt', 'verification.json', 'roundtrip_check.json', 'build.log', 'manifest.json']:
        z.write(D / n, f'검사결과/{n}')
    for f in ['build_hyperion72.py', 'verify_hyperion72.py', 'verify_hyperion_roundtrip.py', 'check72_geometry.py', 'package_hyperion72.py']:
        z.write(BASE / f, f'제작자료/{f}')
    for f in sorted((BASE / 'inspect').rglob('*')):
        if f.is_file() and '__pycache__' not in f.parts:
            z.write(f, '제작자료/' + str(f.relative_to(BASE)))
print(out, out.stat().st_size)
