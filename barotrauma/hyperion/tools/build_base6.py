"""히페리온 - 베이스 5 → 베이스 6.

테스트 결과 반영
1. 전력: 같은 방향 전원 핀끼리(펌프↔펌프, 조명↔조명, 배터리↔배터리) 이은 배선은 게임에서 무효
   (Powered.ValidPowerConnection: 정션박스가 아니면 입력↔출력만 유효) → 모두 제거 후
   펌프는 정션박스 직결, 조명은 릴레이 분배, 배터리는 충전/출력 릴레이로 재배선
2. 상태 모니터: 두 항법 단말기와 상태 모니터에 '연결된 경우 나란히 표시' 체크
3. 중립 밸러스트: 밸러스트 비율에 맞춰 항법 단말기 NeutralBallastLevel 보정 (물 7% = 중성 부력)
4. 밸러스트 탱크1 좌측 이동, 유물 보관소 제거, 좌하단 준비실 절반, 탱크1과 도크 사이 좌측 도킹 예정 공간
5. B층 연구실: 문 없는 헐 경계 제거(복도와 병합, 배경을 문까지), 연구실 장비/격납 탱크/배경
6. 유물 보관소를 연구실 오른쪽으로: 말라카이트식 거대 유물 보관함(하단은 아랫층 벽/배경 뒤) + 중형 강철 캐비닛 2개
"""
import copy
import glob
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from subxml import Sub, load_sub, save_sub, get_rect, set_rect  # noqa: E402
from background import Occupancy, Room, STYLES, s_ballast  # noqa: E402
from bg4 import accent  # noqa: E402
from caps import add_caps  # noqa: E402
from wiring import Wiring, GATE_DEPTH  # noqa: E402
import waypoints  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, '히페리온 - 베이스 5.sub')
OUT = os.path.join(ROOT, '히페리온 - 베이스 6.sub')
OUT_XML = os.path.join(ROOT, 'build', '히페리온 - 베이스 6.xml')
REF_DIR = sys.argv[1] if len(sys.argv) > 1 else None

sub = Sub(load_sub(SRC))
R = sub.root
report = []
log = report.append
IDX = {e.get('ID'): e for e in R if e.get('ID')}


def item(i):
    return IDX[str(i)]


def move(el, x0, x1, y0, y1):
    set_rect(el, x0, x1, y0, y1)


def shift(el, dx=0, dy=0):
    x0, x1, y0, y1 = get_rect(el)
    set_rect(el, x0 + dx, x1 + dx, y0 + dy, y1 + dy)


def clone(el, x0, x1, y0, y1, **attrs):
    n = copy.deepcopy(el)
    n.set('ID', sub.new_id())
    set_rect(n, x0, x1, y0, y1)
    p = n.find('ConnectionPanel')
    if p is not None:
        for c in p:
            for l in c.findall('link'):
                c.remove(l)
    for k, v in attrs.items():
        n.set(k, str(v))
    R.append(n)
    IDX[n.get('ID')] = n
    return n


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


def delete_wire(wid, ends=None):
    ends = ends if ends is not None else wire_ends()
    for e, c, l in ends.get(wid, []):
        if l in list(c):
            c.remove(l)
    w = IDX.get(wid)
    if w is not None and w in list(R):
        R.remove(w)


def delete_item(el):
    ends = wire_ends()
    for c in pins(el):
        for l in c.findall('link'):
            delete_wire(l.get('w'), ends)
    if el in list(R):
        R.remove(el)
    # 다른 아이템의 linked 목록에서도 제거
    for e in R:
        if e.get('linked'):
            ids = [i for i in e.get('linked').split(',') if i != el.get('ID')]
            if ids:
                e.set('linked', ','.join(ids))
            else:
                e.attrib.pop('linked', None)


# ---------------------------------------------------------------- 참고 잠수함 요소
REF = {}


def ref(ident, prefer=None):
    """참고 잠수함에서 요소 복제용 원본."""
    if not REF:
        for f in sorted(glob.glob(os.path.join(REF_DIR, '*', '*.sub'))):
            try:
                root = load_sub(f)
            except Exception:
                continue
            for e in root:
                i = e.get('identifier')
                if i:
                    REF.setdefault(i, []).append((os.path.basename(f), e))
    cands = REF[ident]
    if prefer:
        for f, e in cands:
            if prefer in f:
                return e
    return cands[0][1]


def ref_place(ident, x0, y1, w, h, prefer=None, **attrs):
    src = ref(ident, prefer)
    n = copy.deepcopy(src)
    n.set('ID', sub.new_id())
    n.set('rect', f'{int(x0)},{int(y1)},{int(w)},{int(h)}')
    n.attrib.pop('linked', None)
    for c in pins(n):
        for l in c.findall('link'):
            c.remove(l)
    for ic in n.findall('ItemContainer'):
        cont = ic.get('contained', '')
        ic.set('contained', ',' * cont.count(','))
    n.set('HiddenInGame', 'False')
    for k, v in attrs.items():
        n.set(k, str(v))
    R.append(n)
    IDX[n.get('ID')] = n
    return n


def prop(ident, x0, y1, w, h, prefer=None, **attrs):
    """배경용 아이템: 상호작용 없음 + 손상 없음."""
    return ref_place(ident, x0, y1, w, h, prefer, NonInteractable='True', NonPlayerTeamInteractable='True',
                     InvulnerableToDamage='True', AllowSwapping='False', Tags='', **attrs)


# ---------------------------------------------------------------- 배경 정리
TEMPL_S = sub.templates['structures']
KEEP_BG = ('largeverticalback',)


def is_bg(e):
    if e.get('HiddenInGame') == 'True':
        return False
    ident = e.get('identifier', '')
    if e.tag == 'Structure':
        if 'platform' in ident.lower() or ident in KEEP_BG:
            return False
        return float(e.get('SpriteDepth', '0.5')) >= 0.8
    if e.tag == 'Item':
        if ident in ('lightfluorescentl01', 'vent', 'ladder') or e.find('Wire') is not None:
            return False
        return e.get('NonInteractable') == 'True' and e.get('InvulnerableToDamage') == 'True'
    return False


def clear_bg(regions):
    """regions 안의 배경 삭제. 영역에 걸친 가변 크기 배경은 영역 밖 부분만 남김."""
    removed = clipped = 0
    for e in list(R):
        if not is_bg(e):
            continue
        x0, x1, y0, y1 = get_rect(e)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        hit = [q for q in regions if q[0] < x1 and x0 < q[1] and q[2] < y1 and y0 < q[3]]
        if not hit:
            continue
        if any(q[0] <= cx <= q[1] and q[2] <= cy <= q[3] for q in hit):
            R.remove(e)
            removed += 1
            continue
        t = TEMPL_S.get(e.get('identifier', '')) if e.tag == 'Structure' else None
        if not t:
            continue
        pieces = [(x0, x1, y0, y1)]
        for qx0, qx1, qy0, qy1 in hit:
            nxt = []
            for a, b, c, d in pieces:
                oy = min(d, qy1) - max(c, qy0)
                ox = min(b, qx1) - max(a, qx0)
                if ox <= 0 or oy <= 0:
                    nxt.append((a, b, c, d))
                elif t['resW'] and oy >= 0.5 * (d - c):
                    nxt += [p for p in ((a, qx0, c, d), (qx1, b, c, d)) if p[1] - p[0] > 8]
                elif t['resH'] and ox >= 0.5 * (b - a):
                    nxt += [p for p in ((a, b, c, qy0), (a, b, qy1, d)) if p[3] - p[2] > 8]
                else:
                    nxt.append((a, b, c, d))
            pieces = nxt
        if pieces == [(x0, x1, y0, y1)]:
            continue
        clipped += 1
        R.remove(e)
        for a, b, c, d in pieces:
            n = copy.deepcopy(e)
            n.set('ID', sub.new_id())
            set_rect(n, a, b, c, d)
            R.append(n)
    return removed, clipped


def remove_ladder_back(lad):
    x0, x1, y0, y1 = get_rect(lad)
    cx = (x0 + x1) / 2
    for e in list(sub.elements('Structure', 'largeverticalback')):
        a, b, c, d = get_rect(e)
        if abs((a + b) / 2 - cx) < 20 and c < y1 and d > y0:
            R.remove(e)


def add_ladder_back(lad):
    x0, x1, y0, y1 = get_rect(lad)
    sub.structure('largeverticalback', int((x0 + x1) / 2 - 32), y1, h=y1 - y0, depth=0.9)


# ======================================================================
# A. 좌측: 밸러스트 탱크1 이동 / 유물 보관소 제거 / 좌하단 준비실 절반 / 좌측 도킹 예정 공간
# ======================================================================
WL = -2728                    # 탱크1 좌측 대형 내벽 (해치 1353 오른쪽 끝 -2736 에서 8 떨어짐)
BT_L = WL + 24                # 헐 경계 = 벽 중심 -2704
WR = -1562                    # 탱크1 우측 벽 (도크 우측 공간과 같은 폭으로 좌측 공간 확보)
BT_R = WR + 24                # -1538
DOCK_L = -876                 # 도크 좌측 외벽 중심
third = (BT_R - BT_L) / 3
B1, B2 = int(round(BT_L + third)), int(round(BT_L + 2 * third))   # 칸 경계 -2315, -1927
TOP, BOT = -312, -960

OLD_L = [(-2948, -2644, -568, -312), (-3172, -2016, -960, -568), (-2016, -876, -960, -312)]
NEW_L = [(-2948, BT_L, -568, -312), (-3172, BT_L, -960, -568), (BT_L, DOCK_L, -960, -312)]

# 좌하단 준비실 소독/폐기 슈트는 남는 쪽으로 이동
CHUTE_DX = -2940 - get_rect(item(22357))[0]
for i in (22357, 22358, 22361):
    shift(item(i), CHUTE_DX)

# 옮기거나 지울 사다리 뒤 배경
for i in (1424, 22666, 22667):
    remove_ladder_back(item(i))

rm, cl = clear_bg(OLD_L)
log(f'좌측 재배치 구역 배경 {rm}개 삭제, {cl}개 잘라냄')

# 유물 보관소 헐/문 제거
for i in ('1501',):
    R.remove(item(i))
delete_item(item(147))
R.remove(item(148))
for e in list(R):   # 유물 보관소·준비실 오른쪽에 있던 조명/환풍구
    if e.get('identifier') in ('lightfluorescentl01', 'vent'):
        x0, x1, y0, y1 = get_rect(e)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if any(a <= cx <= b and c <= cy <= d for a, b, c, d in OLD_L[1:] + [OLD_L[0]]) and cx > -2948:
            delete_item(e)

# 헐
move(item(1500), -2948, BT_L, -568, -312)
move(item(1503), -3172, BT_L, -960, -568)
tanks = [item(1509), item(1510), item(1511)]
for h, (a, b) in zip(tanks, ((BT_L, B1), (B1, B2), (B2, BT_R))):
    move(h, a, b, BOT, TOP)
lsp = sub.hull(BT_R, DOCK_L, BOT, TOP, 'roomname.airlock', True)
IDX[lsp.get('ID')] = lsp
for h in tanks + [item(1500), item(1503), lsp]:
    x0, x1, y0, y1 = get_rect(h)
    h.set('Oxygen', str((x1 - x0) * (y1 - y0)))

# 벽
move(item(10), WL, WL + 48, -920, -360)                     # 탱크1 좌측 벽
clone(item(10), WR, WR + 48, -920, -360)                     # 탱크1 우측 벽 = 좌측 도킹 공간 왼쪽 벽
move(item(1312), B1 - 24, B1 + 24, -920, -568)               # 칸막이
move(item(1313), B2 - 24, B2 + 24, -920, -568)
move(item(58), WL + 48, WR, -619, -568)                      # 통로 플랫폼
move(item(1351), -2736, BT_L, -616, -568)                    # 준비실 천장: 해치~새 벽
HX1 = -2624                                                  # 탱크1 입구 해치 (좌상단)
HX2 = -1140                                                  # 좌측 도킹 공간 해치
move(item(1412), -2736, HX1, -360, -312)
move(item(1413), HX1 + 128, HX2, -360, -312)
clone(item(1413), HX2 + 128, 368, -360, -312)
for i in (1414, 1415, 1416):                                 # 탱크1 입구 해치/갭/발판
    x0, x1, y0, y1 = get_rect(item(i))
    move(item(i), HX1, HX1 + 128, y0, y1)
g_new = clone(item(1397), HX2, HX2 + 128, *get_rect(item(1397))[2:])
h_new = clone(item(1398), HX2, HX2 + 128, *get_rect(item(1398))[2:], linked=g_new.get('ID'))
clone(item(1399), HX2, HX2 + 128, *get_rect(item(1399))[2:])
# 도크 좌측 외벽을 줄이고 도크로 나가는 문 (우측 공간과 대칭)
move(item(7), -924, -828, -704, -344)
g_d = clone(item(33), -896, -872, -912, -704)
d_d = clone(item(32), -896, -872, -912, -704, linked=g_d.get('ID'))
log(f'탱크1 이동: 헐 {BT_L}~{BT_R} (칸 {B1}, {B2}), 좌측 도킹 예정 공간 {BT_R}~{DOCK_L} 신설')

# 문(칸 사이 버튼문), 펌프, 사다리, 레버/라벨, 보급함
for door, gap, xb in ((54, 55, B1), (56, 57, B2)):
    for i in (door, gap):
        x0, x1, y0, y1 = get_rect(item(i))
        move(item(i), xb - 12, xb + 12, y0, y1)
lad_x = [HX1 + 58, B1 + 44, B2 + 44]
for lad_id, lx in zip((1424, 22666, 22667), lad_x):
    x0, x1, y0, y1 = get_rect(item(lad_id))
    move(item(lad_id), lx, lx + 11, y0, y1)
    add_ladder_back(item(lad_id))
pump_x = [HX1 + 84, B1 + 76, B2 + 76]
for pid, px in zip((1314, 1315, 1316), pump_x):
    x0, x1, y0, y1 = get_rect(item(pid))
    move(item(pid), px, px + (x1 - x0), y0, y1)
lx0, lx1 = get_rect(item(1424))[:2]
x0, x1, y0, y1 = get_rect(item(22670))
move(item(22670), lx1 + 16, lx1 + 16 + (x1 - x0), y0, y1)
lev_x = [lx1 + 110, B1 + 150, B2 + 150]
for (lev, lab), lx in zip(((22600, 22601), (22611, 22612), (22622, 22623)), lev_x):
    x0, x1, y0, y1 = get_rect(item(lev))
    dx = lx - x0
    shift(item(lev), dx)
    shift(item(lab), dx)

# 새 좌측 공간 사다리 (우측 1309 대칭)
lad2 = clone(item(1309), HX2 + 58, HX2 + 69, -912, -200)
add_ladder_back(lad2)

# 산소 발생기: 새 해치/사다리 자리에서 비켜 오른쪽으로
o2 = item(1253)
ox0, ox1, oy0, oy1 = get_rect(o2)
move(o2, HX2 + 150, HX2 + 150 + (ox1 - ox0), oy0, oy1)
lt = item(22554)   # 창고2 조명과 겹치지 않게
if get_rect(lt)[0] < HX2 + 150 + (ox1 - ox0) + 8:
    shift(lt, HX2 + 150 + (ox1 - ox0) + 16 - get_rect(lt)[0])
# 새 해치 위 소품 제거
for e in list(R):
    if is_bg(e) and e.tag in ('Structure', 'Item'):
        x0, x1, y0, y1 = get_rect(e)
        for hx in (HX1, HX2):
            if x0 < hx + 128 and x1 > hx and y0 < -150 and y1 > -312 and e.get('identifier') != 'opdeco_rollupdoorframe' \
                    and float(e.get('SpriteDepth', '1')) < 0.95:
                if e in list(R):
                    R.remove(e)
    ox0, ox1, oy0, oy1 = get_rect(o2)
    if is_bg(e) and e in list(R) and float(e.get('SpriteDepth', '1')) < 0.95:
        x0, x1, y0, y1 = get_rect(e)
        if x0 < ox1 and x1 > ox0 and y0 < oy1 and y1 > oy0:
            R.remove(e)

# 설계 메모(숨김 라벨)
lab_prep = item(1292)
move(lab_prep, -3040, -2928, -776, -711)
note = clone(lab_prep, BT_R + 40, BT_R + 152, -776, -711)
note.find('ItemLabel').set('Text', '좌측 도킹 예정 공간')

# ======================================================================
# B. B층: 연구실 병합(문까지) / 유물 보관소 신설 / 복도
# ======================================================================
RES = item(22250)
ART_X0, ART_X1 = 956, 1784
move(RES, 92, ART_X0, 457, 713)
RES.set('Oxygen', str((ART_X0 - 92) * 256))
R.remove(item(1463))
cor = item(22251)
move(cor, ART_X1, 2172, 457, 713)
cor.set('Oxygen', str((2172 - ART_X1) * 256))
art = sub.hull(ART_X0, ART_X1, 457, 713, '유물 보관소', False)
IDX[art.get('ID')] = art
g_a = clone(item(1264), ART_X1 - 12, ART_X1 + 12, 456, 664)
d_a = clone(item(1263), ART_X1 - 12, ART_X1 + 12, 456, 664, linked=g_a.get('ID'))
B_REG = [(92, ART_X0, 457, 713), (ART_X0, ART_X1, 457, 713), (ART_X1, 2172, 457, 713)]
rm, cl = clear_bg(B_REG)
for e in list(R):
    if e.get('identifier') in ('lightfluorescentl01', 'vent'):
        x0, x1, y0, y1 = get_rect(e)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if any(a <= cx <= b and c <= cy <= d for a, b, c, d in B_REG):
            delete_item(e)
move(item(1269), 1000, 1112, 520, 585)       # 설계 메모 '유물 보관소'
log(f'B층: 연구실 92~{ART_X0} (복도 1463 병합), 유물 보관소 {ART_X0}~{ART_X1} + 버튼문, 복도 {ART_X1}~2172 '
    f'(배경 {rm}개 삭제, {cl}개 잘라냄)')

# ======================================================================
# C. 배경 재구성
# ======================================================================
shells = [get_rect(e) for e in sub.elements('Structure') if e.get('identifier') in ('shella0deg', 'shella90deg')]
occ = Occupancy(sub)

HOLDER_W, HOLDER_H = 260, 425
HOLDER_X = 1360                       # 아랫층 식물실(1347~1932) 안에 하단이 오도록
HOLDER_TOP = 665 + 47                 # 말라카이트와 같은 비율: 윗부분은 외벽 뒤, 아래 138px 은 아랫층 뒤
occ.add(HOLDER_X, HOLDER_X + HOLDER_W, 456, 713)
CAB_W = 87
CAB_X = (HOLDER_X - 12 - CAB_W, HOLDER_X + HOLDER_W + 12)
for cx in CAB_X:
    occ.add(cx, cx + CAB_W, 456, 643)


def room(key, x0, x1, y0, y1):
    return Room(sub, occ, key, x0, x1, y0, y1, shells)


# 좌측
STYLES['shaft'](room('E2a', -2948, BT_L, -568, -312))
STYLES['prep'](room('G2', -3172, BT_L, -960, -568))
for k, h in enumerate(tanks, 1):
    x0, x1, y0, y1 = get_rect(h)
    s_ballast(room(f'BT1-{k}', x0, x1, y0, y1), k == 3)
STYLES['airlock'](room('S2', BT_R, DOCK_L, BOT, TOP))
accent(room('S2', BT_R, DOCK_L, BOT, TOP), 'tech')


# 연구실 -------------------------------------------------------------
def s_research_lab(r):
    sub.structure('opbg_researchlab2', r.x0, r.y1, w=r.x1 - r.x0, h=r.y1 - r.y0, depth=0.985,
                  tex_scale='0.5,0.5')
    r.ceiling_band(depth=0.97, color='200,210,215,255')
    r.floor_band()
    fl, ce = r.floor, r.ceil
    x = r.cx0 + 20
    # 격납 탱크 2개 (왼쪽), 연구 단말기(가운데), 대형 격납 탱크(오른쪽)
    for k in range(2):
        prop('op_researchcontainmenttank3', x, fl + 182, 110, 182, prefer='Malachite', SpriteDepth='0.885')
        occ.add(x, x + 110, fl, fl + 182)
        x += 122
    x += 8
    term = ref_place('op_researchterminal', x, fl + 148, 247, 148, prefer='Winterhalter', SpriteDepth='0.79')
    occ.add(x, x + 247, fl, fl + 148)
    tx = x
    x += 247 + 16
    prop('op_researchcontainmenttank1', x, fl + 148, 207, 148, prefer='CA-1N', SpriteDepth='0.86',
         SpriteColor='103,103,103,255', Scale='0.5')
    occ.add(x, x + 207, fl, fl + 148)
    x2 = x + 207 + 10
    if x2 + 100 <= r.cx1 - 26:
        prop('op_researchcontainmenttank2', x2, fl + 140, 100, 140, prefer='Malachite', SpriteDepth='0.87')
        occ.add(x2, x2 + 100, fl, fl + 140)
    # 전초기지 연구 배경 띠 (인터셉터/광부 방식)
    trim = ref('opbg_researchlab1', prefer='Miner')
    for yy, hh in ((ce - 10, 16), (fl + 190, 16)):
        n = copy.deepcopy(trim)
        n.set('ID', sub.new_id())
        n.set('rect', f'{r.cx0},{int(yy)},{r.w},{hh}')
        n.set('SpriteDepth', '0.975')
        R.append(n)
    for vx in (r.cx0 + 250, tx - 10, tx + 257, r.cx1 - 16):
        n = copy.deepcopy(trim)
        n.set('ID', sub.new_id())
        n.set('rect', f'{int(vx)},{int(ce - 10)},16,{int(ce - 10 - fl)}')
        n.set('TextureScale', '0.5,0.5')
        n.set('SpriteColor', '48,48,48,255')
        n.set('SpriteDepth', '0.974')
        R.append(n)
    # 단말기 위 모니터 두 대
    for k, mx in enumerate((tx + 60, tx + 140)):
        sub.structure('opdeco_monitor01', mx, fl + 148 + 44, depth=0.975)
    r.cable_col(r.cx1 - 12, ident='CableHolderVertical 2')
    return term


RES_TERM = s_research_lab(room('B4', 92, ART_X0, 457, 713))


# 유물 보관소 -----------------------------------------------------------
def s_artifact_room(r):
    # 보관함(깊이 0.99)보다 뒤: 기본 배경 0.995, 천장/바닥 띠 0.993/0.992
    sub.structure('opbg_shop3', r.x0, r.y1, w=r.x1 - r.x0, h=r.y1 - r.y0, depth=0.995, color='148,149,163,255')
    r.ceiling_band(depth=0.993)
    r.floor_band(depth=0.992)
    fl, ce = r.floor, r.ceil
    holder = ref_place('artifactholder', HOLDER_X, HOLDER_TOP, HOLDER_W, HOLDER_H, prefer='Malachite',
                       SpriteDepth='0.990', NonInteractable='False', Scale='1')
    for cx in CAB_X:
        c = clone(item(616), cx, cx + CAB_W, fl - 3, fl + 184, Tags='container,locker')
        c.find('ItemContainer').set('contained', '')
    # 왼쪽 벽: 아이로식 핀 장식 + 모니터, 벽 장식판
    r.wall_props([('s', 'finadeco02', dict(depth=0.885)), ('s', 'opdeco_mountedmonitor2', dict(depth=0.97)),
                  ('s', 'finadeco02', dict(depth=0.885))], y_center=ce - 70)
    r.floor_props([('s', 'opdeco_box3', dict(depth=0.9))], start=r.cx0 + 24)
    sub.structure('ventconnectora5', r.cx0 + 20, ce - 6, depth=0.92)
    for x in (HOLDER_X - 8, HOLDER_X + HOLDER_W - 32):   # 보관함 양옆 세로 기둥(보관함 앞)
        sub.structure('opdeco_supportbeam_vertical', x, ce + 8, h=ce - fl + 16, depth=0.974)
    r.icon('labelsiconcargo', 'left', dy=46)
    return holder


HOLDER = s_artifact_room(room('X', ART_X0, ART_X1, 457, 713))
STYLES['corridor'](room('B5', ART_X1, 2172, 457, 713))
log('연구실: 연구 배경(opbg_researchlab2/1), 격납 탱크 3·3·1·2, 유전자 연구 단말기(전원) / '
    '유물 보관소: 거대 유물 보관함(말라카이트식 깊이 배치) + 중형 강철 캐비닛 2개')

# 사다리 새 배치에 맞춰 마감(캡) 다시
existing_caps = {(e.get('identifier'), e.get('rect'), e.get('flippedx'), e.get('flippedy'))
                 for e in sub.elements('Structure') if e.get('identifier', '').startswith('inwalllcap')}
CAP_REG = [(-2760, -1480, -1000, -300), (-1200, -990, -380, -290)]
for e in list(sub.elements('Structure')):
    if e.get('identifier', '').startswith('inwalllcap'):
        x0, x1, y0, y1 = get_rect(e)
        if any(a <= (x0 + x1) / 2 <= b and c <= (y0 + y1) / 2 <= d for a, b, c, d in CAP_REG):
            R.remove(e)
            existing_caps.discard((e.get('identifier'), e.get('rect'), e.get('flippedx'), e.get('flippedy')))
before = set(id(e) for e in R)
add_caps(sub, lambda s: None)
n_caps = 0
for e in list(R):
    if id(e) in before:
        continue
    key = (e.get('identifier'), e.get('rect'), e.get('flippedx'), e.get('flippedy'))
    x0, x1, y0, y1 = get_rect(e)
    inside = any(a <= (x0 + x1) / 2 <= b and c <= (y0 + y1) / 2 <= d for a, b, c, d in CAP_REG)
    if key in existing_caps or not inside:
        R.remove(e)
    else:
        n_caps += 1
log(f'바뀐 벽 끝/교차부 마감 {n_caps}개 다시 배치')

# ======================================================================
# D. 조명 + 환풍구 (바뀐 방)
# ======================================================================
IDX = {e.get('ID'): e for e in R if e.get('ID')}
O2 = item(1253)


def floor_of(r):
    x0, x1, y0, y1 = r
    return y0 + 48 if any(a <= (x0 + x1) / 2 <= b and c <= y0 <= d for a, b, c, d in shells) else y0


CEIL = [get_rect(e) for e in sub.elements('Item') if e.get('HiddenInGame') != 'True' and e.get('identifier') != 'ladder']
CEIL.append((HOLDER_X, HOLDER_X + HOLDER_W, 456, 713))
DOORS = [get_rect(e) for e in sub.elements('Item') if e.find('Door') is not None]


def free_ceiling(x_from, x_to, w, y0, y1, pad=6, only_doors=False):
    mid = (x_from + x_to - w) / 2
    rects = DOORS if only_doors else CEIL
    for x in sorted(range(int(x_from), int(x_to - w) + 1, 8), key=lambda x: abs(x - mid)):
        if not any(a < x + w + pad and b > x - pad and c < y1 and d > y0 for a, b, c, d in rects):
            return x
    return None


def new_item(ident, x0, y1, attrs, comps):
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
    for tag, cattrs, pl in comps:
        c = ET.SubElement(el, tag, cattrs)
        for kind, name in pl:
            ET.SubElement(c, kind, {'name': name})
    IDX[el.get('ID')] = el
    return el


PANEL_LIGHT = [('input', 'power'), ('input', 'toggle'), ('input', 'set_state'), ('input', 'set_color')]
LIGHT_C = {'Range': '700', 'CastShadows': 'False', 'DrawBehindSubs': 'False', 'IsOn': 'True', 'Flicker': '0',
           'FlickerSpeed': '1', 'PulseFrequency': '0', 'PulseAmount': '0', 'BlinkFrequency': '0',
           'LightColor': '255,245,230,255', 'IsActive': 'True', 'MinVoltage': '0.5', 'PowerConsumption': '5',
           'VulnerableToEMP': 'True'}
new_vents = []
changed_hulls = tanks + [item(1500), item(1503), lsp, RES, art, cor]
for h in changed_hulls:
    x0, x1, y0, y1 = get_rect(h)
    for e in list(sub.elements('Item')):
        if e.get('identifier') in ('lightfluorescentl01', 'vent'):
            a, b, c, d = get_rect(e)
            if x0 <= (a + b) / 2 <= x1 and y0 <= (c + d) / 2 <= y1:
                delete_item(e)
                CEIL[:] = [q for q in CEIL if q != (a, b, c, d)]
for h in changed_hulls:
    x0, x1, y0, y1 = get_rect(h)
    fl, ceil = floor_of((x0, x1, y0, y1)), y1 - 48
    cx0 = x0 + (48 if any(a - 1 <= x0 <= b + 1 for a, b, c, d in shells if c <= ceil <= d) else 20)
    cx1 = x1 - (48 if any(a - 1 <= x1 <= b + 1 for a, b, c, d in shells if c <= ceil <= d) else 20)
    lx = free_ceiling(cx0, cx1, 120, ceil - 12, ceil - 2, pad=2)
    if lx is None:
        lx = free_ceiling(cx0, cx1, 120, ceil - 12, ceil - 2, pad=2, only_doors=True)
    new_item('lightfluorescentl01', lx, ceil, {'Tags': 'light,largeitem'},
             [('LightComponent', LIGHT_C, []), ('ConnectionPanel', {'Locked': 'False'}, PANEL_LIGHT)])
    CEIL.append((lx, lx + 120, ceil - 36, ceil))
    if 'ballast' in h.get('RoomName', ''):
        continue
    vy = ceil - 8
    vx = free_ceiling(cx0, cx1, 51, ceil - 60, ceil - 8, pad=4)
    for band in (fl + 150, fl + 100):
        if vx is not None:
            break
        vx = free_ceiling(cx0, cx1, 51, band - 51, band, pad=4)
        vy = band
    if vx is None:
        vx = free_ceiling(cx0, cx1, 51, ceil - 60, ceil - 8, pad=4, only_doors=True)
        vy = ceil - 8
    V = new_item('vent', vx, vy, {'Tags': 'vent', 'SpriteColor': '180,180,180,255', 'linked': O2.get('ID')},
                 [('Vent', {}, [])])
    CEIL.append((vx, vx + 51, vy - 51, vy))
    new_vents.append(V)
O2.set('linked', ','.join([i for i in (O2.get('linked') or '').split(',') if i in IDX and i]
                          + [v.get('ID') for v in new_vents]))
log(f'바뀐 방 {len(changed_hulls)}곳 조명/환풍구 다시 배치 (환풍구 {len(new_vents)}개 → 산소 발생기 링크)')

# ======================================================================
# E. 전력 재배선
# ======================================================================
POWER = ('power_in', 'power', 'power_out')


def is_jb(e):
    t = e.get('Tags') or ''
    return 'junctionbox' in t or 'dock' in t


ends = wire_ends()
bad = 0
LIGHT_IDS = {e.get('ID') for e in sub.elements('Item', 'lightfluorescentl01')}
BAT_IDS = {e.get('ID') for e in sub.elements('Item', 'battery')}
for wid, ee in list(ends.items()):
    if len(ee) != 2:
        continue
    (a, ca, _), (b, cb, _) = ee
    if ca.get('name') not in POWER or cb.get('name') not in POWER:
        continue
    invalid = not (is_jb(a) or is_jb(b)) and ca.tag == cb.tag
    redo = a.get('ID') in LIGHT_IDS | BAT_IDS or b.get('ID') in LIGHT_IDS | BAT_IDS
    if invalid or redo:
        delete_wire(wid, ends)
        bad += invalid
log(f'무효 전원 배선 {bad}개 제거 (펌프↔펌프, 조명↔조명, 배터리↔배터리) + 조명/배터리 전원 배선 재구성')

wr = Wiring(sub, log)
# 기존 게이트 칸 등록 + 벽 밖으로 나간 게이트 재배치
GATES = [e for e in sub.elements('Item') if e.get('SpriteDepth') == GATE_DEPTH and e.get('HiddenInGame') == 'True'
         and e.get('identifier') in wr.tmpl]
moved_g = 0
for g in GATES:
    x, y = wr.pos(g)
    i, j = wr.cell(x, y)
    ok = all(0 <= i + di < wr.W and wr.inner[j * wr.W + i + di] for di in (-1, 0, 1)) and (i, j) not in wr.gate_cells
    if ok:
        for di in (-1, 0, 1):
            wr.gate_cells.add((i + di, j))
for g in GATES:
    x, y = wr.pos(g)
    i, j = wr.cell(x, y)
    if all(0 <= i + di < wr.W and wr.inner[j * wr.W + i + di] for di in (-1, 0, 1)):
        continue
    cx, cy = wr.gate_spot(x, y)
    g.set('rect', f'{int(cx - 8)},{int(cy + 8)},16,16')
    moved_g += 1
log(f'벽이 바뀌어 벽 밖에 놓인 게이트 {moved_g}개를 가까운 대형 내벽 안으로 이동')

JBS = list(sub.elements('Item', 'junctionbox'))


def jb_links(j):
    return len(wr._pin(j, 'power').findall('link'))


def jb_near(el):
    x, y = wr.pos(el)
    free = [j for j in JBS if jb_links(j) < 5]
    return min(free, key=lambda j: abs(wr.pos(j)[0] - x) + abs(wr.pos(j)[1] - y))


def powered_in(el, pin):
    return bool(wr._pin(el, pin).findall('link'))


n_relay = 0
# 펌프: 정션박스 직결
for p in sub.elements('Item', 'pump'):
    if not powered_in(p, 'power_in'):
        wr.connect(jb_near(p), 'power', p, 'power_in', 'redwire')

# 배터리: 4개씩 충전 릴레이(정션박스→배터리 입력) + 출력 릴레이(배터리 출력→정션박스)
bats = sorted(sub.elements('Item', 'battery'), key=lambda b: (get_rect(b)[0], get_rect(b)[2]))
for k in range(0, len(bats), 4):
    grp = bats[k:k + 4]
    near = (sum(wr.pos(b)[0] for b in grp) / len(grp), sum(wr.pos(b)[1] for b in grp) / len(grp))
    rc = wr.gate('relaycomponent', near, IsOn='True', MaxPower='4000')
    ro = wr.gate('relaycomponent', near, IsOn='True', MaxPower='4000')
    wr.connect(jb_near(rc), 'power', rc, 'power_in', 'redwire')
    wr.connect(ro, 'power_out', jb_near(ro), 'power', 'redwire')
    for b in grp:
        wr.connect(rc, 'power_out', b, 'power_in', 'redwire')
        wr.connect(b, 'power_out', ro, 'power_in', 'redwire')
    n_relay += 2

# 조명: 층별 4개씩 분배 릴레이
lights = [e for e in sub.elements('Item', 'lightfluorescentl01') if not powered_in(e, 'power')]
rows = {}
for L in lights:
    rows.setdefault(get_rect(L)[3], []).append(L)
for y, ls in sorted(rows.items()):
    ls.sort(key=lambda e: get_rect(e)[0])
    for k in range(0, len(ls), 4):
        grp = ls[k:k + 4]
        near = (sum(wr.pos(L)[0] for L in grp) / len(grp), y)
        rl = wr.gate('relaycomponent', near, IsOn='True')
        wr.connect(jb_near(rl), 'power', rl, 'power_in', 'redwire')
        for L in grp:
            wr.connect(rl, 'power_out', L, 'power', 'redwire')
        n_relay += 1
# 연구 단말기
wr.connect(jb_near(RES_TERM), 'power', RES_TERM, 'power_in', 'redwire')
log(f'전력: 펌프 6대 정션박스 직결, 배터리 12개 충전/출력 릴레이 6개, 조명 {len(lights)}개 분배 릴레이 '
    f'{n_relay - 6}개, 유전자 연구 단말기 전원')

# 전원 없는 장치 목록 (보고용)
unpowered = []
for e in sub.elements('Item'):
    if e.get('HiddenInGame') == 'True' or is_jb(e) or e.get('NonInteractable') == 'True':
        continue
    ps = [c for c in pins(e) if c.get('name') in ('power_in', 'power') and c.tag == 'input']
    if ps and not any(c.findall('link') for c in ps):
        unpowered.append(e.get('identifier'))

# 모든 배선 다시 깔기 (벽 구조가 바뀜)
ends = wire_ends()
n_re = 0
for wid, ee in ends.items():
    w = IDX.get(wid)
    if w is None or w.find('Wire') is None or len(ee) != 2:
        continue
    a = next((e for e, c, l in ee if l.get('i') == '0'), ee[0][0])
    b = next((e for e, c, l in ee if l.get('i') == '1'), ee[1][0])
    wr.connect(a, None, b, None, existing=w)
    n_re += 1
log(f'전체 배선 {n_re}개 새 벽 구조 기준으로 다시 깔기 (숨김, 직각)')

# ======================================================================
# F. 상태 모니터 나란히 표시 + 중립 밸러스트
# ======================================================================
for i in (1234, 22115, 1235):
    item(i).set('DisplaySideBySideWhenLinked', 'True')
V = B = 0
for h in sub.elements('Hull'):
    x0, x1, y0, y1 = get_rect(h)
    V += (x1 - x0) * (y1 - y0)
    if 'ballast' in h.get('RoomName', ''):
        B += (x1 - x0) * (y1 - y0)
nbl = min(0.95, 0.07 / (B / V))
for s in sub.elements('Item'):
    st = s.find('Steering')
    if st is not None:
        st.set('NeutralBallastLevel', f'{nbl:.3f}')
log(f'상태 모니터/항법 단말기 3개 "연결된 경우 나란히 표시" 체크')
log(f'밸러스트 {B / V * 100:.2f}% → 항법 단말기 중립 수위 {nbl * 100:.1f}% (물 7.0% = 중성 부력)')

# ======================================================================
# G. 웨이포인트 + 스폰
# ======================================================================
waypoints.build(sub, log)
SPAWN = [('함장실', 'captain', 'id_captain', 1), ('roomname.electrical', 'engineer', 'id_engineer', 1),
         ('roomname.engineroom', 'engineer', 'id_engineer', 1), ('제작실', 'mechanic', 'id_mechanic', 2),
         ('roomname.medbay', 'medicaldoctor', 'id_medic', 2), ('감옥 로비', 'securityofficer', 'id_security', 1),
         ('roomname.armory', 'securityofficer', 'id_security', 1), ('식당', 'assistant', 'id_assistant', 2),
         ('조리실', None, None, 2), ('사격실', None, None, 2)]
n_sp = 0
for rname, job, tag, cnt in SPAWN:
    h = next(h for h in sub.elements('Hull') if h.get('RoomName') == rname)
    x0, x1, y0, y1 = get_rect(h)
    for k in range(cnt):
        waypoints.spawnpoint(sub, x0 + (x1 - x0) * (k + 1) / (cnt + 1), floor_of((x0, x1, y0, y1)) + 110, job, tag)
        n_sp += 1
for h in [h for h in sub.elements('Hull') if h.get('RoomName') == 'roomname.cargo'][:2]:
    x0, x1, y0, y1 = get_rect(h)
    waypoints.spawnpoint(sub, (x0 + x1) / 2, floor_of((x0, x1, y0, y1)) + 110, kind='Cargo')
log(f'부활(스폰) 포인트 {n_sp}개 + 화물 스폰 2개')
log(f'이번 단계 배선 {wr.n_wires}개 (다시 깐 것 포함)')
if unpowered:
    from collections import Counter
    log('전원 미연결(기존과 동일): ' + ', '.join(f'{k} {v}' for k, v in Counter(unpowered).items()))

R.set('name', '히페리온 - 베이스 6')
save_sub(R, OUT, OUT_XML)
print('\n'.join(report))
