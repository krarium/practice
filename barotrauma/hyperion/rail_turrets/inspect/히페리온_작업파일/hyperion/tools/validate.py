"""베이스2 검증: 헐 겹침, 갭-헐 연결(Gap.FindHulls 와 같은 탐색점), 문-갭 링크, ID 중복."""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from subxml import load_sub, get_rect  # noqa: E402

path = sys.argv[1]
root = load_sub(path)
hulls = [(e.get('ID'), get_rect(e), e.get('RoomName')) for e in root if e.tag == 'Hull']
gaps = {e.get('ID'): (get_rect(e), e.get('horizontal') == 'true') for e in root if e.tag == 'Gap'}
problems = []

ids = Counter(e.get('ID') for e in root if e.get('ID'))
dup = [i for i, n in ids.items() if n > 1]
if dup:
    problems.append(f'ID 중복: {dup}')

for i, (a, ra, _) in enumerate(hulls):
    for b, rb, _ in hulls[i + 1:]:
        if ra[0] < rb[1] and rb[0] < ra[1] and ra[2] < rb[3] and rb[2] < ra[3]:
            problems.append(f'헐 겹침 {a} {ra} / {b} {rb}')


def hull_at(x, y):
    for hid, (x0, x1, y0, y1), room in hulls:
        if x0 <= x <= x1 and y0 <= y <= y1:
            return hid, room
    return None


linked_gaps = {}
for e in root:
    if e.tag == 'Item' and e.get('linked'):
        for gid in e.get('linked').split(','):
            if gid in gaps:
                linked_gaps[gid] = e.get('identifier')
    if e.tag == 'Item' and e.get('identifier', '') in ('doorwbuttons', 'windoweddoor', 'door', 'hatch', 'hatchwbuttons'):
        if not e.get('linked') or e.get('linked') not in gaps:
            problems.append(f'문/해치에 갭 링크 없음: {e.get("ID")} {e.get("identifier")}')

outside_ok = 0
for gid, ((x0, x1, y0, y1), horiz) in gaps.items():
    if horiz:
        pts = [(x0 - 1, (y0 + y1) / 2), (x1 + 1, (y0 + y1) / 2)]
    else:
        pts = [((x0 + x1) / 2, y1 + 1), ((x0 + x1) / 2, y0 - 1)]
    hs = [hull_at(*p) for p in pts]
    n = sum(h is not None for h in hs)
    owner = linked_gaps.get(gid, '개방 갭')
    if n == 0:
        if not (-3140 < x0 < -1990 and y1 < -300):   # 하부 도크 바닥 해치는 원래 바다와 바다 사이
            problems.append(f'갭 {gid}({owner}) 어떤 헐에도 안 이어짐 {x0, x1, y0, y1}')
    elif n == 1:
        outside_ok += 1
    elif hs[0][0] == hs[1][0]:
        problems.append(f'갭 {gid}({owner}) 양쪽이 같은 헐 {hs[0]}')

print(f'헐 {len(hulls)}개, 갭 {len(gaps)}개 (바깥과 연결된 외부 출입 갭 {outside_ok}개)')
print('문제 없음' if not problems else '\n'.join(problems))
