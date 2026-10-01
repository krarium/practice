"""히페리온 - 베이스 6 (사용자 수정) → 베이스 7.

1. 이동포탑 2기 (카인 CA-1N 방식: 보이지 않는 도킹포트 레일 + 서브 잠수함 포탑)
   - 상부: B층 격납고(헐 1673) ↔ 천장 커스텀 해치 ↔ 상단 레일 (A층 위, A층 우측 끝 경사, B층 위)
   - 하부: G층 격납고(헐 1164) ↔ 바닥 커스텀 해치 ↔ 하단 레일 (선체 아래 일직선)
   - 포탑: 이중 코일건 + 레일건 (같은 조준), 무적, 교체 불가
   - 장전기: 히페리온(격납고)에 두고 포탑과 링크 (포탑이 어디 있든 본함 장전기의 탄을 씀)
   - 조작: C층 레일건 사격실 전투 잠망경 (왼쪽=하부, 오른쪽=상부)
       조준=두 무기, 클릭=이중 코일건, W=레일건, A/D=레일 좌우 이동. 전개 완료 상태에서만 동작
   - 메인 항법 단말기 신호 1: 전개/수납 (수납 중 재입력 무시, 주 전원 2초 이상 끊기면 자동 수납)
   - 격납고 해치: 격납고 경로를 지날 때만 열림 (수납 시 레일 접속점에 와서야 열림)
2. 인수인계 결정 반영: D층 조리실 → 엔진실(두 번째 엔진 연결), 우측 중앙 도킹 배선 복구,
   외장 장식 회로 제거, 미연결 전원 전부 연결, 웨이포인트 재생성
"""
import copy
import os
import random
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from subxml import Sub, load_sub, save_sub, get_rect, set_rect  # noqa: E402
from background import Occupancy, Room  # noqa: E402
from bg4 import s_engine  # noqa: E402
from wiring import Wiring, GATE_DEPTH, WIRE_COLORS  # noqa: E402
import waypoints  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'input', '히페리온 - 베이스 6 (사용자 수정).sub')
OUT = os.path.join(ROOT, '히페리온 - 베이스 7.sub')
OUT_XML = os.path.join(ROOT, 'build', '히페리온 - 베이스 7.xml')
REF = sys.argv[1]
random.seed(7)

sub = Sub(load_sub(SRC))
R = sub.root
report = []
log = report.append
IDX = {e.get('ID'): e for e in R if e.get('ID')}


def item(i):
    return IDX[str(i)]


def pins(el):
    p = el.find('ConnectionPanel')
    return list(p) if p is not None else []


def wire_ends():
    ends = {}
    for e in R:
        if e.tag != 'Item':
            continue
        for c in pins(e):
            for l in c.findall('link'):
                ends.setdefault(l.get('w'), []).append((e, c, l))
    return ends


def delete_wire(wid):
    for e, c, l in wire_ends().get(wid, []):
        c.remove(l)
    w = IDX.get(wid)
    if w is not None and w in list(R):
        R.remove(w)


def delete_item(el):
    for c in pins(el):
        for l in c.findall('link'):
            delete_wire(l.get('w'))
    R.remove(el)


def strip(el):
    el.attrib.pop('linked', None)
    for c in pins(el):
        for l in c.findall('link'):
            c.remove(l)
    for ic in el.findall('ItemContainer'):
        ic.set('contained', ',' * (ic.get('contained', '').count(',')))
    return el


def clone(el, x0, x1, y0, y1, **attrs):
    n = strip(copy.deepcopy(el))
    n.set('ID', sub.new_id())
    set_rect(n, x0, x1, y0, y1)
    for k, v in attrs.items():
        n.set(k, str(v))
    R.append(n)
    IDX[n.get('ID')] = n
    return n


def ref(fname, rid):
    root = load_sub(os.path.join(REF, fname))
    e = next(x for x in root if x.get('ID') == str(rid))
    return strip(copy.deepcopy(e))


def place(tmpl, x0, y1, **attrs):
    n = copy.deepcopy(tmpl)
    n.set('ID', sub.new_id())
    a, b, c, d = get_rect(n)
    n.set('rect', f'{int(x0)},{int(y1)},{b - a},{d - c}')
    for k, v in attrs.items():
        n.set(k, str(v))
    R.append(n)
    IDX[n.get('ID')] = n
    return n


def label_text(el, text):
    el.find('ItemLabel').set('Text', text)


# ======================================================================
# 0. 인수인계 결정 반영 (16 외장 회로 제거, 15 우측 중앙 도킹, 14 엔진실, 라벨 위치)
# ======================================================================
for i in (3049, 3050, 3051, 3052):          # NDRST mkII 장식 회로 (무선/지연/NOT x2)
    delete_item(item(i))
for w in ('1823', '1824'):                  # 끊긴 도킹 배선 잔재
    delete_wire(w)
log('외장 장식 회로(무선·지연·NOT 2개, 배선 5개) 삭제, 끊긴 우측 중앙 도킹 배선 잔재 삭제')

ENG2_HULL = item(1139)
ENG2_HULL.set('RoomName', 'roomname.engineroom')
for e in sub.elements('Item', 'label'):
    t = e.find('ItemLabel').get('Text')
    if t == '조리실' and e.get('HiddenInGame') == 'True':
        label_text(e, '엔진실 2')
    if t == '벨러스트 탱크1' and e.get('HiddenInGame') == 'True':
        set_rect(e, -2480, -2368, -680, -615)


def is_bg(e):
    if e.get('HiddenInGame') == 'True':
        return False
    ident = e.get('identifier', '')
    if e.tag == 'Structure':
        return 'platform' not in ident.lower() and ident != 'largeverticalback' and \
            float(e.get('SpriteDepth', '0.5')) >= 0.8
    if e.tag == 'Item':
        return e.get('NonInteractable') == 'True' and e.get('InvulnerableToDamage') == 'True' and \
            ident not in ('lightfluorescentl01', 'vent', 'ladder', 'label')
    return False


x0, x1, y0, y1 = get_rect(ENG2_HULL)
n_rm = 0
for e in list(R):
    if is_bg(e):
        a, b, c, d = get_rect(e)
        if x0 <= (a + b) / 2 <= x1 and y0 <= (c + d) / 2 <= y1 and (b - a) < 1200:
            R.remove(e)
            n_rm += 1
shells = [get_rect(e) for e in sub.elements('Structure') if e.get('identifier') in ('shella0deg', 'shella90deg')]
s_engine(Room(sub, Occupancy(sub), 'X', x0, x1, y0, y1, shells))
log(f'D층 조리실(헐 1139) → 엔진실 2: 방 이름·설계 라벨 변경, 조리실 배경 {n_rm}개 삭제 후 엔진실 배경')

# ======================================================================
# 1. 격납고: 해치(외벽 절개), 이름, 장전기, 배수 펌프, 라벨
# ======================================================================
UP_X, LO_X = -344, 680                      # 격납고 경로(포탑 중심) x


def cut_shell(sid, hx0, hx1, board_src, hatch_src, gap_src, by0, by1):
    s = item(sid)
    a, b, c, d = get_rect(s)
    set_rect(s, a, hx0, c, d)
    clone(s, hx1, b, c, d)
    clone(item(board_src), hx0 - 19, hx0 + 2, by0, by1)
    clone(item(board_src), hx1 - 2, hx1 + 19, by0, by1)
    ga, gb, gc, gd = get_rect(item(gap_src))
    g = clone(item(gap_src), hx0, hx1, gc, gd)
    ha, hb, hc, hd = get_rect(item(hatch_src))
    h = clone(item(hatch_src), hx0, hx1, hc, hd, linked=g.get('ID'), Tags='weldable,door')
    return h


HATCH_U = cut_shell(1676, UP_X - 64, UP_X + 64, 1678, 43, 44, 665, 738)
HATCH_L = cut_shell(1107, LO_X - 64, LO_X + 64, 1109, 45, 46, -979, -906)

HANGAR_U, HANGAR_L = item(1673), item(1164)
HANGAR_U.set('RoomName', '상부 이동포탑 격납고')
HANGAR_U.set('IsWetRoom', 'True')
HANGAR_L.set('RoomName', '하부 이동포탑 격납고')
hidden_label = next(e for e in sub.elements('Item', 'label') if e.get('HiddenInGame') == 'True')
vis_label = next(e for e in sub.elements('Item', 'label') if e.get('HiddenInGame') != 'True'
                 and e.find('ItemLabel').get('Text') == '원격 쓰레기통 튜브')
label_text(clone(hidden_label, -700, -588, 520, 585), '상부 이동포탑 격납고')
label_text(clone(hidden_label, 300, 412, -776, -711), '하부 이동포탑 격납고')

T_COIL = ref('133860dd-Submarines/Azimuth.sub', 437)
T_RAILL = ref('133860dd-Submarines/Herja.sub', 164)
T_PUMP = ref('133860dd-Submarines/Azimuth.sub', 489)
LOADERS = {}
for key, fl, cx, rx, px in (('U', 457, -890, -790, -660), ('L', -904, 250, 462, 770)):
    lc = place(T_COIL, cx, fl + 176, AllowSwapping='False', NonInteractable='False', InvulnerableToDamage='False',
               SpriteDepth='0.78')
    lr = place(T_RAILL, rx, fl + 176, AllowSwapping='False', NonInteractable='False', InvulnerableToDamage='False',
               SpriteDepth='0.78')
    pm = place(T_PUMP, px, fl + 44, SpriteDepth='0.82')
    name = '상부' if key == 'U' else '하부'
    label_text(clone(vis_label, cx + 22, cx + 60, fl + 186, fl + 204), f'{name} 코일건 장전기')
    label_text(clone(vis_label, rx + 36, rx + 74, fl + 186, fl + 204), f'{name} 레일건 장전기')
    LOADERS[key] = (lc, lr, pm)
log('격납고 2곳: 외벽에 커스텀 해치 + 마감판, 방 이름(상부/하부 이동포탑 격납고), 코일건·레일건 장전기, '
    '배수 펌프, 장전기 라벨 (장전기·포탑 모두 교체 불가)')

# 레일건 사격실 잠망경 2개 → 전투 잠망경 (왼쪽 861=하부, 오른쪽 867=상부)
PERI = {}
for key, pid in (('L', 861), ('U', 867)):
    p = item(pid)
    p.set('identifier', 'isc_combatperiscope')
    p.set('Tags', 'combatperiscope')
    panel = p.find('ConnectionPanel')
    for c in [c for c in panel if c.tag in ('output', 'input')]:
        panel.remove(c)
    for n in ('position_out', 'trigger_out', 'key_w_out', 'key_a_out', 'key_s_out', 'key_d_out'):
        ET.SubElement(panel, 'output', {'name': n})
    PERI[key] = p
log('레일건 사격실 잠망경 2개 → 산업모드 전투 잠망경 (왼쪽=하부 이동포탑, 오른쪽=상부 이동포탑)')

# ======================================================================
# 2. 레일 (숨긴 도킹포트) — 카인과 같은 포트(스케일 0.4)·간격(76)·경사 단차(17)
# ======================================================================
T_PORT = ref('6b5b879c-__/CA-1N.sub', 743)
STEP_X, STEP_Y = 76, 17
TURRET_OFF = 65.5, 54.5                    # 포탑 서브 안: 포탑 중심 - 도킹포트 중심 (카인 SL 기준)


def rail_points(key):
    if key == 'U':
        pts = [(-1560 - STEP_X * k, 1070) for k in range(25, -1, -1)]
        pts += [(-1560 + STEP_X * j, 1070 - STEP_Y * j) for j in range(1, 16)]
        pts += [(-420 + STEP_X * i, 815) for i in range(1, 42)]
        path = [(UP_X, 815 - STEP_Y * k) for k in range(1, 16)]
    else:
        pts = [(LO_X + STEP_X * i, -1075) for i in range(-54, 28)]
        path = [(LO_X, -1075 + STEP_Y * k) for k in range(1, 16)]
    return pts, path


PORTS = {}
for key in ('U', 'L'):
    pts, path = rail_points(key)
    sy = -1 if key == 'U' else 1               # 상부: 포탑이 포트 위 / 하부: 포탑이 포트 아래
    ports = []
    for idx, (tx, ty) in [(i + 1, p) for i, p in enumerate(pts)] + [(101 + k, p) for k, p in enumerate(path)]:
        px, py = tx - TURRET_OFF[0], ty + sy * TURRET_OFF[1]
        n = copy.deepcopy(T_PORT)
        n.set('ID', sub.new_id())
        n.set('rect', f'{int(round(px - 56.5))},{int(round(py + 104.5))},113,209')
        n.set('HiddenInGame', 'True')
        n.set('NonInteractable', 'True')
        n.set('InvulnerableToDamage', 'True')
        n.set('AllowSwapping', 'False')
        n.find('DockingPort').set('ForceDockingDirection', 'Left')
        n.find('DockingPort').set('MainDockingPort', 'False')
        R.append(n)
        IDX[n.get('ID')] = n
        ports.append((idx, n, (tx, ty)))
    J = next(i for i, _, (tx, ty) in ports if i < 100 and tx == (UP_X if key == 'U' else LO_X))
    PORTS[key] = dict(ports=ports, N=len(pts), J=J, S=100 + len(path), stow=path[-1])
    log(f'{"상부" if key == "U" else "하부"} 레일: 도킹포트 {len(pts)}개(1~{len(pts)}) + 격납고 경로 {len(path)}개'
        f'(101~{100 + len(path)}), 접속점 {J}, 수납 위치 {100 + len(path)}')

# ======================================================================
# 3. 이동포탑 서브 잠수함 (카인 'Turret Shuttle hatch system SL' 기반)
# ======================================================================
SL = load_sub(os.path.join(REF, '6b5b879c-__/Turret Shuttle hatch system SL.sub'))
KEEP = {'1': 'port', '5': 'battery', '6': 'supercap', '15': 'coil', '55': 'rail', '53': 'hull'}
PORT_C = (91.5, -46.5)
TUR_C = (157.0, -101.0)
T_WIFI = ref('133860dd-Submarines/Kastrull.sub', 752)
WIRE_T = next(e for e in R if e.tag == 'Item' and e.get('identifier') == 'bluewire' and e.find('Wire') is not None)
CH = {'U': dict(T=3101, C=3102, AIM=3103, COIL=3104, RAIL=3105),
      'L': dict(T=3111, C=3112, AIM=3113, COIL=3114, RAIL=3115), 'WANT': 3121, 'NOTWANT': 3122}


def build_turret_sub(key, loader_coil, loader_rail):
    upper = key == 'U'
    els, named = [], {}
    for e in SL:
        if e.tag == 'Structure' or e.get('ID') in KEEP:
            n = copy.deepcopy(e)
            if n.tag == 'Item':
                strip(n)
            els.append(n)
            if e.get('ID') in KEEP:
                named[KEEP[e.get('ID')]] = n

    def mirror(n):
        a, b, c, d = get_rect(n)
        set_rect(n, a, b, 2 * PORT_C[1] - d, 2 * PORT_C[1] - c)
        rot = round(float(n.get('Rotation', '0') or 0)) % 180
        flag = 'flippedx' if rot == 90 else 'flippedy'
        if n.get(flag) == 'true':
            n.attrib.pop(flag)
        else:
            n.set(flag, 'true')

    if upper:
        for n in els:
            if n.tag == 'Structure' or n is named['battery'] or n is named['supercap']:
                mirror(n)
    tcx, tcy = TUR_C[0], (2 * PORT_C[1] - TUR_C[1]) if upper else TUR_C[1]
    # 헐은 포탑 바깥쪽 끝(상부=위, 하부=아래)에 둔다: 수납 시 본함 외벽 안에 묻혀 승무원이 들어갈 일 없음
    hy = tcy + 110 if upper else tcy - 110
    set_rect(named['hull'], tcx - 8, tcx + 8, hy - 8, hy + 8)
    for t, link in (('coil', loader_coil), ('rail', loader_rail)):
        n = named[t]
        n.set('linked', link.get('ID'))                # 본함 장전기 (IdRemap 으로 부모 잠수함에서 찾음)
        n.set('AllowSwapping', 'False')
        n.set('InvulnerableToDamage', 'True')
        n.set('NonInteractable', 'True')
        if upper:
            a, b, c, d = get_rect(n)
            set_rect(n, a, b, 2 * PORT_C[1] - d, 2 * PORT_C[1] - c)      # 포트 위로 위치만 반전
            n.attrib.pop('flippedx', None)
            n.attrib.pop('flippedy', None)
            n.set('Rotation', '0')
            n.find('Turret').set('BaseRotation', '0')
    for t in ('port', 'battery', 'supercap'):
        named[t].set('InvulnerableToDamage', 'True')
        named[t].set('NonInteractable', 'True')
        named[t].set('AllowSwapping', 'False')
    named['port'].find('DockingPort').set('ForceDockingDirection', 'None')
    # 무선 수신기 3개 (조준 / 코일건 발사 / 레일건 발사)
    rx = {}
    for k, (nm, dy) in enumerate((('AIM', 0), ('COIL', 18), ('RAIL', 36))):
        w = copy.deepcopy(T_WIFI)
        w.set('rect', f'{int(PORT_C[0] - 8)},{int(PORT_C[1] + 30 - dy)},14,13')
        w.set('HiddenInGame', 'True')
        w.set('NonInteractable', 'True')
        w.set('InvulnerableToDamage', 'True')
        w.set('SpriteDepth', GATE_DEPTH)
        w.find('WifiComponent').set('Channel', str(CH[key][nm]))
        w.find('WifiComponent').set('AllowCrossTeamCommunication', 'False')
        h = w.find('Holdable')
        if h is not None:
            h.set('Attached', 'True')
        els.append(w)
        rx[nm] = w
    # ID 다시 매기기 (1부터) — 본함 ID 와 겹쳐도 무방(하위 잠수함 ID 공간), 단 장전기 ID 와는 겹치면 안 됨
    for i, n in enumerate(els, 1):
        n.set('ID', str(i))
    assert all(int(l.get('ID')) > len(els) + 20 for l in (loader_coil, loader_rail))
    nid = [len(els)]

    def pin(n, name):
        return next(c for c in n.find('ConnectionPanel') if c.get('name') == name)

    def wire(a, pa, b, pb, color):
        nid[0] += 1
        w = copy.deepcopy(WIRE_T)
        w.set('ID', str(nid[0]))
        w.set('identifier', color)
        w.set('SpriteColor', WIRE_COLORS[color])
        w.set('InventoryIconColor', WIRE_COLORS[color])
        w.set('HiddenInGame', 'True')
        ax0, ax1, ay0, ay1 = get_rect(a)
        bx0, bx1, by0, by1 = get_rect(b)
        p0 = ((ax0 + ax1) / 2, (ay0 + ay1) / 2)
        p1 = ((bx0 + bx1) / 2, (by0 + by1) / 2)
        nodes = [p0, (p1[0], p0[1]), p1]
        w.set('rect', f'{int(p0[0])},{int(p0[1])},42,16')
        w.find('Wire').set('nodes', ';'.join(f'{x:g};{y:g}' for x, y in nodes))
        ET.SubElement(pin(a, pa), 'link', {'w': w.get('ID'), 'i': '0'})
        ET.SubElement(pin(b, pb), 'link', {'w': w.get('ID'), 'i': '1'})
        els.append(w)

    wire(named['port'], 'power', named['battery'], 'power_in', 'redwire')
    wire(named['battery'], 'power_out', named['supercap'], 'power_in', 'redwire')
    wire(named['supercap'], 'power_out', named['coil'], 'power_in', 'redwire')
    wire(named['supercap'], 'power_out', named['rail'], 'power_in', 'redwire')
    wire(rx['AIM'], 'signal_out', named['coil'], 'position_in', 'bluewire')
    wire(rx['AIM'], 'signal_out', named['rail'], 'position_in', 'bluewire')
    wire(rx['COIL'], 'signal_out', named['coil'], 'trigger_in', 'bluewire')
    wire(rx['RAIL'], 'signal_out', named['rail'], 'trigger_in', 'bluewire')

    info = PORTS[key]
    stow_port = next(n for i, n, _ in info['ports'] if i == info['S'])
    xs = [v for n in els if n.get('rect') for v in get_rect(n)[:2]]
    ys = [v for n in els if n.get('rect') for v in get_rect(n)[2:]]
    ls = ET.Element('LinkedSubmarine', {
        'description': '', 'checkval': str(random.randint(10 ** 8, 2 * 10 ** 9)), 'price': '1000', 'tier': '1',
        'initialsuppliesspawned': 'true', 'noitems': 'false', 'lowfuel': 'true', 'type': 'Player',
        'ismanuallyoutfitted': 'true', 'class': 'Undefined', 'tags': '0', 'outposttags': '',
        'gameversion': R.get('gameversion'), 'dimensions': f'{int(max(xs) - min(xs))},{int(max(ys) - min(ys))}',
        'cargocapacity': '0', 'recommendedcrewsizemin': '1', 'recommendedcrewsizemax': '1',
        'recommendedcrewexperience': 'CrewExperienceLow', 'requiredcontentpackages': '',
        'name': '상부 이동포탑' if upper else '하부 이동포탑',
        'pos': f'{info["stow"][0]},{info["stow"][1]}', 'linkedto': stow_port.get('ID'),
        'originallinkedto': '0', 'originalmyport': '0'})
    for n in els:
        ls.append(n)
    R.append(ls)
    return ls


TSUB = {k: build_turret_sub(k, LOADERS[k][0], LOADERS[k][1]) for k in ('U', 'L')}
log('이동포탑 서브 2척(카인 포탑 서브 기반): 도킹포트·배터리·슈퍼커패시터·이중 코일건·레일건 + 무선 수신기 3개. '
    '전부 무적, 포탑은 교체 불가·본함 장전기 링크. 상부는 상하 반전(포탑이 위)')

# ======================================================================
# 4. 배선과 게이트
# ======================================================================
wr = Wiring(sub, log)
for g in [e for e in sub.elements('Item') if e.get('SpriteDepth') == GATE_DEPTH and e.get('HiddenInGame') == 'True']:
    i, j = wr.cell(*wr.pos(g))
    for di in (-1, 0, 1):
        wr.gate_cells.add((i + di, j))
TPL = {
    'addercomponent': ref('133860dd-Submarines/Azimuth.sub', 951),
    'subtractcomponent': ref('2f459000-____/Anaconda HE-SP.sub', 465),
    'oscillator': ref('133860dd-Submarines/R-29.sub', 1171),
    'wificomponent': T_WIFI,
}
for k in ('relaycomponent', 'notcomponent', 'signalcheckcomponent', 'memorycomponent', 'delaycomponent'):
    TPL[k] = wr.tmpl[k]
COMP = {'relaycomponent': 'RelayComponent', 'notcomponent': 'NotComponent',
        'signalcheckcomponent': 'SignalCheckComponent', 'memorycomponent': 'MemoryComponent',
        'delaycomponent': 'DelayComponent', 'addercomponent': 'AdderComponent',
        'subtractcomponent': 'SubtractComponent', 'oscillator': 'OscillatorComponent',
        'wificomponent': 'WifiComponent'}
n_gates = [0]


def G(ident, near, **attrs):
    t = copy.deepcopy(TPL[ident])
    cx, cy = wr.gate_spot(*near)
    a, b, c, d = get_rect(t)
    t.set('ID', sub.new_id())
    t.set('rect', f'{int(cx - (b - a) / 2)},{int(cy + (d - c) / 2)},{b - a},{d - c}')
    t.set('SpriteDepth', GATE_DEPTH)
    t.set('HiddenInGame', 'True')
    t.set('AllowSwapping', 'False')
    h = t.find('Holdable')
    if h is not None:
        h.set('Attached', 'True')
    comp = t.find(COMP[ident])
    for k, v in attrs.items():
        comp.set(k, str(v))
    R.append(t)
    IDX[t.get('ID')] = t
    wr.items[t.get('ID')] = t
    n_gates[0] += 1
    return t


def W(a, pa, b, pb, color='bluewire'):
    wr.items.setdefault(a.get('ID'), a)
    wr.items.setdefault(b.get('ID'), b)
    return wr.connect(a, pa, b, pb, color)


def SC(near, target, out, false=''):
    return G('signalcheckcomponent', near, TargetSignal=target, Output=out, FalseOutput=false)


def ARITH(kind, near, lo, hi):
    return G(kind, near, ClampMin=lo, ClampMax=hi, TimeFrame='0')


def WIFI(near, ch):
    return G('wificomponent', near, Channel=ch, Range='40000', AllowCrossTeamCommunication='False')


def MEM(near, value):
    return G('memorycomponent', near, Value=value, Writeable='False')


# ---------------------------------------------------------------- 공용 (전개 상태, 박자, 상수, 전원 감시)
SH = (1050, 330)
WANT = G('relaycomponent', SH, IsOn='False')                 # 전개 상태 (켜짐=전개)
NOTW = G('notcomponent', SH)
TX_WANT, TX_NOTW = WIFI(SH, CH['WANT']), WIFI(SH, CH['NOTWANT'])
W(WANT, 'state_out', TX_WANT, 'signal_in')
W(WANT, 'state_out', NOTW, 'signal_in')
W(NOTW, 'signal_out', TX_NOTW, 'signal_in')
OSC = G('oscillator', SH, OutputType='Pulse', Frequency='3')    # 이동 박자 (초당 3칸 목표)
DLY = G('delaycomponent', SH, Delay='0.04', ResetWhenSignalReceived='False', ResetWhenDifferentSignalReceived='False')
SC0 = SC(SH, '1', '0')
W(OSC, 'signal_out', DLY, 'signal_in')
W(DLY, 'signal_out', SC0, 'signal_in')
K100 = MEM(SH, '100')
KPUMP = MEM(SH, '-100')
for k in ('U', 'L'):
    W(KPUMP, 'signal_out', LOADERS[k][2], 'set_speed')
# 주 전원 감시: 원자로 쪽 정션박스 전력값이 2초 동안 계속 0 이면 수납
JB69 = item(69)
DPL = G('delaycomponent', (-1100, 30), Delay='2', ResetWhenSignalReceived='False',
        ResetWhenDifferentSignalReceived='True')
SCPL = SC((-1100, 30), '0', '0')
W(JB69, 'power_value_out', DPL, 'signal_in')
W(DPL, 'signal_out', SCPL, 'signal_in')
W(SCPL, 'signal_out', WANT, 'set_state')
# 메인 항법 단말기 신호 1 = 전개/수납 (수납되는 중에는 무시: 전개 상태이거나 둘 다 수납 완료일 때만 통과)
MAIN = item(897)
ci = MAIN.find('CustomInterface')
labels = ci.get('Labels').split(',')
labels[0] = '이동포탑 전개/수납'
ci.set('Labels', ','.join(labels))
RBTN = G('relaycomponent', (-1100, 330), IsOn='False')
BTNOK = ARITH('addercomponent', (-1100, 330), '0', '1')
RX_WS = WIFI(SH, CH['WANT'])
W(MAIN, 'signal_out1', RBTN, 'signal_in1')
W(RBTN, 'signal_out1', WANT, 'toggle')
W(BTNOK, 'signal_out', RBTN, 'set_state')
W(RX_WS, 'signal_out', BTNOK, 'signal_in1')
BOTHS = ARITH('subtractcomponent', SH, '0', '1')     # 둘 다 수납 = eqS_U - (NOT eqS_L)
W(BOTHS, 'signal_out', BTNOK, 'signal_in2')

# ---------------------------------------------------------------- 포탑별 제어기
CTRL = {}
for key in ('U', 'L'):
    info = PORTS[key]
    N, J, S = info['N'], info['J'], info['S']
    pr = PERI[key]
    near = wr.pos(pr)
    c = {}
    rxC = [WIFI(near, CH[key]['C']) for _ in range(2)]
    rxW, rxNW = WIFI(near, CH['WANT']), WIFI(near, CH['NOTWANT'])
    cons_C = []
    isPath = ARITH('subtractcomponent', near, '0', '1'); cons_C.append((isPath, 'signal_in1'))
    W(K100, 'signal_out', isPath, 'signal_in2')
    isRail = G('notcomponent', near)
    W(isPath, 'signal_out', isRail, 'signal_in')
    eqJ = SC(near, str(J), '1', '0'); cons_C.append((eqJ, 'signal_in'))
    eqP0 = SC(near, '101', '1', '0'); cons_C.append((eqP0, 'signal_in'))
    eqS = SC(near, str(S), '1', '0'); cons_C.append((eqS, 'signal_in'))
    nS = SC(near, str(S), '0', '1'); cons_C.append((nS, 'signal_in'))
    adR = ARITH('addercomponent', near, '1', str(N)); cons_C.append((adR, 'signal_in1'))
    adP = ARITH('addercomponent', near, '101', str(S)); cons_C.append((adP, 'signal_in1'))
    sgn = ARITH('subtractcomponent', near, '-1', '1'); cons_C.append((sgn, 'signal_in2'))
    outV = SC(near, '101', str(J)); cons_C.append((outV, 'signal_in'))
    inV = SC(near, str(J), '101'); cons_C.append((inV, 'signal_in'))
    for k2, (g, p) in enumerate(cons_C):
        W(rxC[k2 // 5], 'signal_out', g, p)
    KJ = MEM(near, str(J))
    W(KJ, 'signal_out', sgn, 'signal_in1')
    retJ = ARITH('subtractcomponent', near, '0', '1')           # (C==J) - want
    outJ = ARITH('subtractcomponent', near, '0', '1')           # (C==101) - notwant
    railEn = ARITH('subtractcomponent', near, '0', '1')         # isRail - retJ
    pathEn = ARITH('subtractcomponent', near, '0', '1')         # isPath - outJ
    ctrlEn = ARITH('subtractcomponent', near, '0', '1')         # isRail - notwant
    t1 = ARITH('addercomponent', near, '0', '1')                # want OR (C!=S)
    nt1 = G('notcomponent', near)
    pathOpen = ARITH('subtractcomponent', near, '0', '1')       # isPath - NOT t1
    hatchOpen = ARITH('addercomponent', near, '0', '1')         # retJ OR pathOpen
    W(eqJ, 'signal_out', retJ, 'signal_in1'); W(rxW, 'signal_out', retJ, 'signal_in2')
    W(eqP0, 'signal_out', outJ, 'signal_in1'); W(rxNW, 'signal_out', outJ, 'signal_in2')
    W(isRail, 'signal_out', railEn, 'signal_in1'); W(retJ, 'signal_out', railEn, 'signal_in2')
    W(isPath, 'signal_out', pathEn, 'signal_in1'); W(outJ, 'signal_out', pathEn, 'signal_in2')
    W(isRail, 'signal_out', ctrlEn, 'signal_in1'); W(rxNW, 'signal_out', ctrlEn, 'signal_in2')
    W(rxW, 'signal_out', t1, 'signal_in1'); W(nS, 'signal_out', t1, 'signal_in2')
    W(t1, 'signal_out', nt1, 'signal_in')
    W(isPath, 'signal_out', pathOpen, 'signal_in1'); W(nt1, 'signal_out', pathOpen, 'signal_in2')
    W(retJ, 'signal_out', hatchOpen, 'signal_in1'); W(pathOpen, 'signal_out', hatchOpen, 'signal_in2')
    W(hatchOpen, 'signal_out', HATCH_U if key == 'U' else HATCH_L, 'set_state', 'greenwire')
    # 다음 목표 칸
    dirDA = ARITH('subtractcomponent', near, '-1', '1')         # D - A
    W(pr, 'key_d_out', dirDA, 'signal_in1'); W(pr, 'key_a_out', dirDA, 'signal_in2')
    relDA = G('relaycomponent', near, IsOn='False')
    relS = G('relaycomponent', near, IsOn='False')
    W(dirDA, 'signal_out', relDA, 'signal_in1'); W(rxW, 'signal_out', relDA, 'set_state')
    W(sgn, 'signal_out', relS, 'signal_in1'); W(rxNW, 'signal_out', relS, 'set_state')
    W(relDA, 'signal_out1', adR, 'signal_in2'); W(relS, 'signal_out1', adR, 'signal_in2')
    dirP = SC(near, '1', '-1', '1')                              # 전개 중엔 -1(밖으로), 수납 중엔 +1(안으로)
    W(rxW, 'signal_out', dirP, 'signal_in'); W(dirP, 'signal_out', adP, 'signal_in2')
    relR = G('relaycomponent', near, IsOn='False')
    relP = G('relaycomponent', near, IsOn='False')
    relO = G('relaycomponent', near, IsOn='False')
    relI = G('relaycomponent', near, IsOn='False')
    W(adR, 'signal_out', relR, 'signal_in1'); W(railEn, 'signal_out', relR, 'set_state')
    W(adP, 'signal_out', relP, 'signal_in1'); W(pathEn, 'signal_out', relP, 'set_state')
    W(outV, 'signal_out', relO, 'signal_in1'); W(rxW, 'signal_out', relO, 'set_state')
    W(inV, 'signal_out', relI, 'signal_in1'); W(rxNW, 'signal_out', relI, 'set_state')
    TM = MEM(near, str(S))
    for rl in (relR, relP, relO, relI):
        W(rl, 'signal_out1', TM, 'signal_in')
    W(OSC, 'signal_out', TM, 'lock_state'); W(SC0, 'signal_out', TM, 'lock_state')
    txT = WIFI(near, CH[key]['T'])
    W(TM, 'signal_out', txT, 'signal_in')
    # 잠망경 → 포탑 (전개 완료일 때만)
    for pin_name, ch in (('position_out', 'AIM'), ('trigger_out', 'COIL'), ('key_w_out', 'RAIL')):
        rl = G('relaycomponent', near, IsOn='False')
        tx = WIFI(near, CH[key][ch])
        W(pr, pin_name, rl, 'signal_in1'); W(ctrlEn, 'signal_out', rl, 'set_state')
        W(rl, 'signal_out1', tx, 'signal_in')
    CTRL[key] = dict(eqS=eqS, nS=nS)
W(CTRL['U']['eqS'], 'signal_out', BOTHS, 'signal_in1')
W(CTRL['L']['nS'], 'signal_out', BOTHS, 'signal_in2')
log(f'제어 회로: 공용(전개 릴레이, 박자 발진기, 상수, 주 전원 감시, 버튼 잠금) + 포탑별 상태 판단·목표 칸 계산·'
    f'해치 개폐·잠망경 차단')

# ---------------------------------------------------------------- 레일 포트별 (목표 칸이면 도킹, 도킹되면 자기 번호 송신)
for key in ('U', 'L'):
    ports = PORTS[key]['ports']
    for k in range(0, len(ports), 5):
        grp = ports[k:k + 5]
        cx = sum(get_rect(n)[0] + 56 for _, n, _ in grp) / len(grp)
        cy = sum(get_rect(n)[3] - 104 for _, n, _ in grp) / len(grp)
        rx = WIFI((cx, cy), CH[key]['T'])
        tx = WIFI((cx, cy), CH[key]['C'])
        for idx, port, _ in grp:
            pc = wr.pos(port)
            sc = SC(pc, str(idx), '1', '0')
            rc = SC(pc, '1', str(idx))
            W(rx, 'signal_out', sc, 'signal_in')
            W(sc, 'signal_out', port, 'set_state', 'greenwire')
            W(port, 'state_out', rc, 'signal_in', 'greenwire')
            W(rc, 'signal_out', tx, 'signal_in')
    stow = next(n for i, n, _ in ports if i == PORTS[key]['S'])
    CTRL[key]['stow_port'] = stow
log('레일 포트마다 신호 검사 2개(목표 칸 → 도킹 / 도킹 상태 → 자기 번호) + 5개마다 무선 송수신기')

# ======================================================================
# 5. 전원 (15 우측 중앙 도킹 복구 포함, 18 미연결 전원)
# ======================================================================
DOCKT = item(1554)
W(DOCKT, 'signal_out4', item(2980), 'toggle', 'greenwire')
W(item(2980), 'state_out', item(47), 'set_state', 'greenwire')
log('우측 중앙 도킹 복구: 도킹 단말기 신호 4 → 새 도킹포트 toggle, 포트 state_out → 문 47')

ENG2 = item(1332)
W(item(897), 'velocity_x_out', ENG2, 'set_force')
W(DOCKT, 'velocity_x_out', ENG2, 'set_force')

JBS = list(sub.elements('Item', 'junctionbox'))


def jb_free_near(el):
    x, y = wr.pos(el)
    free = [j for j in JBS if len(wr._pin(j, 'power').findall('link')) < 5]
    return min(free, key=lambda j: abs(wr.pos(j)[0] - x) + abs(wr.pos(j)[1] - y)) if free else None


EXCLUDE = {'coilgun', 'searchlight', 'camera', 'dockingport', 'dockinghatch'}
targets = []
for e in sub.elements('Item'):
    if e.get('HiddenInGame') == 'True' or e.get('NonInteractable') == 'True':
        continue
    if e.get('identifier') in EXCLUDE or 'junctionbox' in (e.get('Tags') or ''):
        continue
    ps = [c for c in pins(e) if c.tag == 'input' and c.get('name') in ('power_in', 'power')]
    if ps and not any(c.findall('link') for c in ps):
        targets.append((e, ps[0].get('name')))
targets += [(CTRL[k]['stow_port'], 'power') for k in ('U', 'L')]
relays = []                                     # (relay, 남은 출력 칸)
n_direct = n_relay = 0
targets.sort(key=lambda t: (round(wr.pos(t[0])[1] / 256), wr.pos(t[0])[0]))
for e, pname in targets:
    big = e.get('identifier') in ('largeengine',)
    j = jb_free_near(e)
    if big and j is not None:
        W(j, 'power', e, pname, 'redwire')
        n_direct += 1
        continue
    x, y = wr.pos(e)
    rl = next((r for r in relays if r[1] > 0 and abs(wr.pos(r[0])[0] - x) < 700 and abs(wr.pos(r[0])[1] - y) < 300),
              None)
    if rl is None:
        r = G('relaycomponent', (x, y), IsOn='True', MaxPower='20000')
        j = jb_free_near(r)
        if j is not None:
            W(j, 'power', r, 'power_in', 'redwire')
        else:                                   # 정션박스 칸이 없으면 기존 릴레이에서 이어 받음
            up = min((q for q in relays if q[1] > 0), key=lambda q: abs(wr.pos(q[0])[0] - x))
            W(up[0], 'power_out', r, 'power_in', 'redwire')
            up[1] -= 1
        rl = [r, 4]
        relays.append(rl)
        n_relay += 1
    W(rl[0], 'power_out', e, pname, 'redwire')
    rl[1] -= 1
from collections import Counter  # noqa: E402
log(f'미연결 전원 {len(targets)}개 연결 (정션박스 직결 {n_direct}, 분배 릴레이 {n_relay}개 경유): ' +
    ', '.join(f'{k} {v}' for k, v in Counter(e.get('identifier') for e, _ in targets).most_common()))
log('엔진 2(조리실 자리) 두 항법 단말기 velocity_x_out → set_force 연결')

# ======================================================================
# 6. 기존 배선 다시 깔기 (외벽 절개 등 반영, 연구 단말기 대각선 해소) + 웨이포인트
# ======================================================================
new_wires = {w.get('ID') for w in R if w.tag == 'Item' and w.find('Wire') is not None}
ends = wire_ends()
n_re = 0
for wid, ee in ends.items():
    w = IDX.get(wid)
    if w is None or w.find('Wire') is None or len(ee) != 2 or w not in list(R):
        continue
    a = next((e for e, c, l in ee if l.get('i') == '0'), ee[0][0])
    b = next((e for e, c, l in ee if l.get('i') == '1'), ee[1][0])
    wr.items.setdefault(a.get('ID'), a)
    wr.items.setdefault(b.get('ID'), b)
    wr.connect(a, None, b, None, existing=w)
    n_re += 1

waypoints.build(sub, log)
SPAWN = [('함장실', 'captain', 'id_captain', 1), ('roomname.electrical', 'engineer', 'id_engineer', 1),
         ('roomname.engineroom', 'engineer', 'id_engineer', 1), ('제작실', 'mechanic', 'id_mechanic', 2),
         ('roomname.medbay', 'medicaldoctor', 'id_medic', 2), ('감옥 로비', 'securityofficer', 'id_security', 1),
         ('roomname.armory', 'securityofficer', 'id_security', 1), ('식당', 'assistant', 'id_assistant', 2),
         ('식물실', None, None, 2), ('사격실', None, None, 2)]
for rname, job, tag, cnt in SPAWN:
    h = next(h for h in sub.elements('Hull') if h.get('RoomName') == rname)
    x0, x1, y0, y1 = get_rect(h)
    fl = y0 + 48 if y0 <= -900 else y0
    for k in range(cnt):
        waypoints.spawnpoint(sub, x0 + (x1 - x0) * (k + 1) / (cnt + 1), fl + 110, job, tag)
for h in [h for h in sub.elements('Hull') if h.get('RoomName') == 'roomname.cargo'][:2]:
    x0, x1, y0, y1 = get_rect(h)
    waypoints.spawnpoint(sub, (x0 + x1) / 2, y0 + 110, kind='Cargo')
log(f'게이트 {n_gates[0]}개 새로 배치, 기존 배선 {n_re}개 다시 깔기, 이번 단계 배선 작업 {wr.n_wires}회')

R.set('name', '히페리온 - 베이스 7')
save_sub(R, OUT, OUT_XML)
print('\n'.join(report))
