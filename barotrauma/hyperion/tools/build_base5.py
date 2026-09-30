"""히페리온 - 베이스 4 → 베이스 5.

- 방(헐)마다 환풍구(산소 발생기 링크) + 밝은 조명 1개, 산소 발생기 전원
- 밸러스트 탱크 6칸: 걷는 공간(플랫폼 위)에 배수 잠금 레버. 레버 ON → 항법 신호 차단 + 목표 수위 0% 고정
- 밸러스트 입구 2곳 바로 아래 보급함(6칸)
- 웨이포인트 + 부활(스폰) 포인트
"""
import copy
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from subxml import Sub, load_sub, save_sub, get_rect  # noqa: E402
from background import Occupancy  # noqa: E402
from wiring import Wiring  # noqa: E402
import waypoints  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, '히페리온 - 베이스 4.sub')
OUT = os.path.join(ROOT, '히페리온 - 베이스 5.sub')
OUT_XML = os.path.join(ROOT, 'build', '히페리온 - 베이스 5.xml')

sub = Sub(load_sub(SRC))
R = sub.root
report = []
log = report.append


def item(i):
    return sub.by_id(str(i))


shells = [get_rect(e) for e in sub.elements('Structure') if e.get('identifier', '').startswith('shell')]


def floor_of(r):
    x0, x1, y0, y1 = r
    return y0 + 48 if any(a <= (x0 + x1) / 2 <= b and c <= y0 <= d for a, b, c, d in shells) else y0


def strip_links(el):
    p = el.find('ConnectionPanel')
    if p is not None:
        for c in p:
            for l in c.findall('link'):
                c.remove(l)
    el.attrib.pop('linked', None)
    return el


def clone_item(src, x0, y1, **attrs):
    x_0, x_1, y_0, y_1 = get_rect(src)
    n = copy.deepcopy(src)
    strip_links(n)
    n.set('ID', sub.new_id())
    n.set('rect', f'{int(x0)},{int(y1)},{x_1 - x_0},{y_1 - y_0}')
    for k, v in attrs.items():
        n.set(k, str(v))
    ic = n.find('ItemContainer')
    if ic is not None:
        ic.set('contained', '')
    R.append(n)
    return n


wr = Wiring(sub, log)
tmpl_vent = None
occ = Occupancy(sub)
BALLAST = [h for h in sub.elements('Hull') if 'ballast' in h.get('RoomName', '')]
ROOMS = [h for h in sub.elements('Hull') if (get_rect(h)[3] - get_rect(h)[2]) >= 100]


def new_item(ident, x0, y1, attrs, comps):
    """템플릿 JSON 속성 + 지정 컴포넌트 요소로 아이템 생성."""
    t = sub.templates['items'][ident]
    a = dict(t['attrs'])
    el = ET.SubElement(R, 'Item')
    el.set('name', '')
    el.set('identifier', ident)
    el.set('ID', sub.new_id())
    el.set('markedfordeconstruction', 'false')
    el.set('rect', f'{int(x0)},{int(y1)},{t["w"]},{t["h"]}')
    for k in ('NonInteractable', 'NonPlayerTeamInteractable', 'AllowSwapping', 'Rotation', 'Scale', 'SpriteColor',
              'InventoryIconColor', 'ContainerColor', 'InvulnerableToDamage', 'Tags', 'DisplaySideBySideWhenLinked',
              'DisallowedUpgrades', 'SpriteDepth'):
        if k in a:
            el.set(k, a[k])
    for k, v in attrs.items():
        el.set(k, v)
    el.set('HiddenInGame', 'False')
    for tag, cattrs, pins in comps:
        c = ET.SubElement(el, tag, cattrs)
        for kind, name in pins:
            ET.SubElement(c, kind, {'name': name})
    return el


def free_x(x_from, x_to, w, y0, y1, step=16, pad=8):
    """[x_from, x_to] 에서 폭 w 가 비는 x (가운데부터)."""
    mid = (x_from + x_to - w) / 2
    cands = sorted(range(int(x_from), int(x_to - w) + 1, step), key=lambda x: abs(x - mid))
    for x in cands:
        if occ.free(x - pad, x + w + pad, y0, y1):
            return x
    return None


CEIL = []   # 천장 근처 장애물: 사다리 제외(천장 설비는 사다리 뒤로 겹쳐도 무방)
for e in sub.elements('Item'):
    if e.get('HiddenInGame') == 'True' or e.get('identifier') == 'ladder':
        continue
    CEIL.append(get_rect(e))


DOORS = [get_rect(e) for e in sub.elements('Item') if e.find('Door') is not None]


def free_ceiling(x_from, x_to, w, y0, y1, pad=6, only_doors=False):
    mid = (x_from + x_to - w) / 2
    rects = DOORS if only_doors else CEIL
    for x in sorted(range(int(x_from), int(x_to - w) + 1, 8), key=lambda x: abs(x - mid)):
        if not any(a < x + w + pad and b > x - pad and c < y1 and d > y0 for a, b, c, d in rects):
            return x
    return None


# ======================================================================
# 1. 환풍구 + 조명 (방마다)
# ======================================================================
O2 = item(1253)
vents, lights, skipped = [], [], []
PANEL_LIGHT = [('input', 'power'), ('input', 'toggle'), ('input', 'set_state'), ('input', 'set_color')]
for h in ROOMS:
    x0, x1, y0, y1 = get_rect(h)
    fl, ceil = floor_of((x0, x1, y0, y1)), y1 - 48
    cx0 = x0 + (48 if any(a - 1 <= x0 <= b + 1 for a, b, c, d in shells if c <= ceil <= d) else 20)
    cx1 = x1 - (48 if any(a - 1 <= x1 <= b + 1 for a, b, c, d in shells if c <= ceil <= d) else 20)
    wet = 'ballast' in h.get('RoomName', '')
    # 조명: 천장 가운데
    lx = free_ceiling(cx0, cx1, 120, ceil - 12, ceil - 2, pad=2)
    if lx is None:   # 마지막 대안: 문/해치만 피함
        lx = free_ceiling(cx0, cx1, 120, ceil - 12, ceil - 2, pad=2, only_doors=True)
    if lx is None:   # 좁은 방: 문 가장자리까지 사용
        lx = free_ceiling(x0 + 12, x1 - 12, 120, ceil - 12, ceil - 2, pad=0, only_doors=True)
    if lx is not None:
        L = new_item('lightfluorescentl01', lx, ceil, {'Tags': 'light,largeitem'},
                     [('LightComponent', {'Range': '700', 'CastShadows': 'False', 'DrawBehindSubs': 'False',
                                          'IsOn': 'True', 'Flicker': '0', 'FlickerSpeed': '1', 'PulseFrequency': '0',
                                          'PulseAmount': '0', 'BlinkFrequency': '0', 'LightColor': '255,245,230,255',
                                          'IsActive': 'True', 'MinVoltage': '0.5', 'PowerConsumption': '5',
                                          'VulnerableToEMP': 'True'}, []),
                      ('ConnectionPanel', {'Locked': 'False'}, PANEL_LIGHT)])
        occ.add(lx - 8, lx + 128, ceil - 40, ceil)
        CEIL.append((lx, lx + 120, ceil - 36, ceil))
        lights.append((fl, lx, L))
    else:
        skipped.append(('조명', h.get('RoomName')))
    if wet and 'ballast' in h.get('RoomName', ''):
        continue                                  # 밸러스트 탱크엔 환풍구 없음(바닐라와 동일)
    vy = ceil - 8
    vx = free_ceiling(cx0, cx1, 51, ceil - 60, ceil - 8, pad=4)
    for band in (fl + 150, fl + 100):            # 천장이 막혀 있으면 벽 중간 높이
        if vx is not None:
            break
        vx = free_ceiling(cx0, cx1, 51, band - 51, band, pad=4)
        vy = band
    if vx is None:   # 마지막 대안: 가구 뒤라도 천장에 (문/해치만 피함)
        vx = free_ceiling(cx0, cx1, 51, ceil - 60, ceil - 8, pad=4, only_doors=True)
        vy = ceil - 8
    if vx is None:
        skipped.append(('환풍구', h.get('RoomName')))
        continue
    V = new_item('vent', vx, vy, {'Tags': 'vent', 'SpriteColor': '180,180,180,255', 'linked': O2.get('ID')},
                 [('Vent', {}, [])])
    occ.add(vx - 8, vx + 59, ceil - 70, ceil - 6)
    CEIL.append((vx, vx + 51, vy - 51, vy))
    vents.append(V)
O2.set('linked', ','.join(filter(None, [O2.get('linked')] + [v.get('ID') for v in vents])))
log(f'환풍구 {len(vents)}개 → 산소 발생기 링크, 조명 {len(lights)}개 (밸러스트 탱크는 환풍구 제외)')
if skipped:
    log('자리 부족으로 생략: ' + ', '.join(f'{a}({b})' for a, b in skipped))

# ======================================================================
# 2. 밸러스트 레버 + 보급함
# ======================================================================
LEVER_T = item(814)
BUS = {'BT1': item(22396), 'BT2': item(22397)}
PUMPS = {p.get('ID'): p for p in sub.elements('Item', 'pump')}

# 분배 릴레이 → 펌프 직결 배선 제거 (탱크별 레버 회로로 교체)
wires_by_id = {e.get('ID'): e for e in sub.elements('Item') if e.find('Wire') is not None}
removed = 0
for bus in BUS.values():
    pin = wr._pin(bus, 'signal_out1')
    for l in list(pin.findall('link')):
        wid = l.get('w')
        w = wires_by_id.get(wid)
        other = None
        for e in list(PUMPS.values()):
            for c in e.find('ConnectionPanel'):
                for l2 in c.findall('link'):
                    if l2.get('w') == wid:
                        c.remove(l2)
                        other = e
        if other is not None:
            pin.remove(l)
            R.remove(w)
            removed += 1
log(f'분배 릴레이→펌프 직결 배선 {removed}개 제거 (레버 회로로 교체)')

wr = Wiring(sub, log)   # 새 아이템/조명 반영해 그리드 재구성
PLATFORM_TOP = {'BT1': -568, 'BT2': -568}
for n, h in enumerate(sorted(BALLAST, key=lambda h: get_rect(h)[0]), 1):
    x0, x1, y0, y1 = get_rect(h)
    grp = 'BT1' if x1 < 0 else 'BT2'
    pump = next(p for p in PUMPS.values() if x0 <= (get_rect(p)[0] + get_rect(p)[1]) / 2 <= x1)
    top = PLATFORM_TOP[grp]
    lx = free_x(x0 + 40, x1 - 40, 31, top + 60, top + 150, step=8)
    lever = clone_item(LEVER_T, lx, top + 140, Tags=f'switch,smallitem,ballast_lock{n}')
    lever.find('Controller').set('State', 'False')
    occ.add(lx - 8, lx + 40, top + 60, top + 150)
    lab = clone_item(item(1696), lx - 30, top + 162, SpriteColor='135,135,135,255')
    lab.find('ItemLabel').set('Text', f'탱크 {n} 배수 잠금')
    near = ((x0 + x1) / 2, -336)
    tr = wr.gate('relaycomponent', near, IsOn='True')
    nt = wr.gate('notcomponent', near)
    ck = wr.gate('signalcheckcomponent', near, TargetSignal='1', Output='-100', FalseOutput='')
    wr.connect(BUS[grp], 'signal_out1', tr, 'signal_in1', 'bluewire')
    wr.connect(tr, 'signal_out1', pump, 'set_targetlevel', 'bluewire')
    wr.connect(lever, 'signal_out', nt, 'signal_in', 'bluewire')
    wr.connect(nt, 'signal_out', tr, 'set_state', 'bluewire')
    wr.connect(lever, 'signal_out', ck, 'signal_in', 'bluewire')
    wr.connect(ck, 'signal_out', pump, 'set_targetlevel', 'bluewire')
log('밸러스트 탱크 6칸: 배수 잠금 레버 + 릴레이/NOT/신호검사(-100) 회로')

# 사다리 없는 탱크: 통로(플랫폼) ↔ 바닥 사다리 (AI가 펌프까지 내려가 수리할 수 있게)
LADDER_T = item('1424')
lad_x = [((get_rect(e)[0] + get_rect(e)[1]) / 2, get_rect(e)[2]) for e in sub.elements('Item', 'ladder')]
n_lad = 0
for h in BALLAST:
    x0, x1, y0, y1 = get_rect(h)
    if any(x0 < lx < x1 and ly0 < y1 - 48 for lx, ly0 in lad_x):
        continue
    fl = floor_of((x0, x1, y0, y1))
    lx = x0 + 44
    n = copy.deepcopy(LADDER_T)
    n.set('ID', sub.new_id())
    n.set('rect', f'{int(lx)},{-568 + 128},11,{-568 + 128 - fl}')
    R.append(n)
    n_lad += 1
log(f'사다리 없는 밸러스트 탱크 {n_lad}칸에 통로↔바닥 사다리 추가')

SUP = item(564)
for lad_id, side in (('1424', 1), ('1425', -1)):
    lx0, lx1, ly0, ly1 = get_rect(item(lad_id))
    x = lx1 + 16 if side > 0 else lx0 - 16 - 60
    clone_item(SUP, x, -372, Tags='suppliescontainer,container')
log('밸러스트 탱크 1/2 입구 바로 아래 보급함(6칸) 배치')

# ======================================================================
# 3. 전원: 산소 발생기, 조명
# ======================================================================
JBS = [e for e in sub.elements('Item', 'junctionbox')]


def jb_free():
    return min(JBS, key=lambda j: len(wr._pin(j, 'power').findall('link')))


wr.connect(jb_free(), 'power', O2, 'power_in', 'redwire')
rows = {}
for fl, lx, L in lights:
    rows.setdefault(fl, []).append((lx, L))
for fl, ls in sorted(rows.items()):
    ls.sort(key=lambda t: t[0])
    wr.connect(jb_free(), 'power', ls[0][1], 'power', 'redwire')
    for (_, a), (_, b) in zip(ls, ls[1:]):
        wr.connect(a, 'power', b, 'power', 'redwire')
log(f'산소 발생기 전원 + 조명 {len(rows)}개 층 줄 단위로 연결')

# ======================================================================
# 4. 웨이포인트 + 부활 포인트
# ======================================================================
waypoints.build(sub, log)
SPAWN = [('함장실', 'captain', 'id_captain', 1), ('roomname.electrical', 'engineer', 'id_engineer', 1),
         ('roomname.engineroom', 'engineer', 'id_engineer', 1), ('제작실', 'mechanic', 'id_mechanic', 2),
         ('roomname.medbay', 'medicaldoctor', 'id_medic', 2), ('감옥 로비', 'securityofficer', 'id_security', 1),
         ('roomname.armory', 'securityofficer', 'id_security', 1), ('식당', 'assistant', 'id_assistant', 2),
         ('조리실', None, None, 2), ('사격실', None, None, 2)]
n_sp = 0
for room, job, tag, cnt in SPAWN:
    h = next((h for h in sub.elements('Hull') if h.get('RoomName') == room), None)
    if h is None:
        log(f'스폰 방 없음: {room}')
        continue
    x0, x1, y0, y1 = get_rect(h)
    for k in range(cnt):
        x = x0 + (x1 - x0) * (k + 1) / (cnt + 1)
        waypoints.spawnpoint(sub, x, floor_of((x0, x1, y0, y1)) + 110, job, tag)
        n_sp += 1
cargo = [h for h in sub.elements('Hull') if h.get('RoomName') == 'roomname.cargo'][:2]
for h in cargo:
    x0, x1, y0, y1 = get_rect(h)
    waypoints.spawnpoint(sub, (x0 + x1) / 2, floor_of((x0, x1, y0, y1)) + 110, kind='Cargo')
log(f'부활(스폰) 포인트 {n_sp}개 (직업별) + 화물 스폰 {len(cargo)}개')
log(f'이번 단계 신규 게이트 18개 / 배선 {wr.n_wires}개')

R.set('name', '히페리온 - 베이스 5')
os.makedirs(os.path.dirname(OUT_XML), exist_ok=True)
save_sub(R, OUT, OUT_XML)
print('\n'.join(report))
