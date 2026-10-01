"""히페리온 - 베이스 → 베이스2 변환.

1) 밸러스트 탱크 크기 조정(중립 부력) + 6칸 분할 + 펌프
2) 사다리 통로를 해치로 개방, 도킹 해치/포트 개방
3) 헐 재구성(방마다, 빈틈 없이) + 개방 갭
4) 내벽/외벽 마감
5) 배경(background.py)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from subxml import Sub, load_sub, save_sub, get_rect, set_rect
import background

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'input', '히페리온 - 베이스.sub')
OUT = os.path.join(ROOT, '히페리온 - 베이스2.sub')
OUT_XML = os.path.join(ROOT, 'build', '히페리온 - 베이스2.xml')

NEUTRAL = 0.07   # SubmarineBody.NeutralBallastPercentage
LEVEL = 0.5      # Steering.NeutralBallastLevel 기본값

# 밸러스트 탱크 좌측 내벽(대형 내벽 수직) 새 위치 (벽 왼쪽 x)
BT1_LEFT = -4248
BT2_LEFT = -1358
BT1_RIGHT_IN = -3132   # 외벽(도크 좌벽) 안쪽 면
BT2_RIGHT_IN = -204    # 우측 내벽 왼쪽 면
BT1_FLOOR, BT2_FLOOR = -336, -328
BT_TOP_IN = 216        # 천장 내벽(9263) 아래 면
PLATFORM_TOP = 8

HATCH_W = 128

sub = Sub(load_sub(SRC))
R = sub.root
report = []


def log(msg):
    report.append(msg)


# ======================================================================
# 0. 정리: 잠수함 밖에 남아 있던 웨이포인트/갭, 중복 문
# ======================================================================
for wp in list(sub.elements('WayPoint')):
    sub.remove(wp)
for gid in ('5568', '5569'):
    sub.remove(sub.by_id(gid))
# 같은 자리에 겹쳐 있던 버튼문(21133)과 그 갭(21134)
sub.remove(sub.by_id('21133'))
sub.remove(sub.by_id('21134'))
for h in list(sub.elements('Hull')):
    sub.remove(h)
log('잠수함 밖 웨이포인트 전부, 떠 있던 갭 2개, 중복 버튼문 1개(21133) 제거, 기존 헐 제거')

WALL_H = sub.by_id('14')      # 대형 내벽 수평 템플릿 (MaxHealth 150, 그림자 끔)
WALL_V = sub.by_id('20')      # 대형 내벽 수직 템플릿
HATCH_T = sub.by_id('9303')   # 버튼 해치 템플릿
LADDER_T = sub.by_id('9253')


def wall_h(x0, x1, y_top):
    return sub.clone(WALL_H, x0, x1, y_top - 48, y_top, MaxHealth=150, UseDropShadow='False')


def wall_v(x0, y0, y1):
    return sub.clone(WALL_V, x0, x0 + 48, y0, y1, MaxHealth=150, UseDropShadow='False')


def cut(el, a, b, axis='x'):
    """구조물 el 에서 [a,b] 구간을 잘라낸다. 남은 조각 목록 반환."""
    x0, x1, y0, y1 = get_rect(el)
    lo, hi = (x0, x1) if axis == 'x' else (y0, y1)
    assert lo < a and b < hi, (el.get('ID'), lo, hi, a, b)
    pieces = []
    left = sub.clone(el, x0, a, y0, y1) if axis == 'x' else sub.clone(el, x0, x1, y0, a)
    right = sub.clone(el, b, x1, y0, y1) if axis == 'x' else sub.clone(el, x0, x1, b, y1)
    sub.remove(el)
    return [left, right]


def find_wall(ident_prefix, x, y):
    for e in sub.elements('Structure'):
        if not e.get('identifier', '').startswith(ident_prefix):
            continue
        x0, x1, y0, y1 = get_rect(e)
        if x0 < x < x1 and y0 <= y <= y1:
            return e
    raise LookupError((ident_prefix, x, y))


# 내벽 전부 그림자 끔 + 최대 내구도 150
for e in sub.elements('Structure'):
    if e.get('identifier') in ('ff_x_wall', 'ff_y_wall'):
        e.set('UseDropShadow', 'False')
        e.set('MaxHealth', '150')

# ======================================================================
# 1. 밸러스트 탱크
# ======================================================================
w20 = sub.by_id('20')
x0, x1, y0, y1 = get_rect(w20)
set_rect(w20, BT1_LEFT, BT1_LEFT + 48, y0, y1)
w9348 = sub.by_id('9348')
x0, x1, y0, y1 = get_rect(w9348)
set_rect(w9348, BT2_LEFT, BT2_LEFT + 48, y0, y1)

# 좌하단 준비실/창고3 바닥(18)을 새 BT1 좌벽까지 연장
w18 = sub.by_id('18')
x0, x1, y0, y1 = get_rect(w18)
set_rect(w18, x0, BT1_LEFT + 24, y0, y1)

BT_DEF = {
    'BT1': dict(inner=(BT1_LEFT + 48, BT1_RIGHT_IN), floor=BT1_FLOOR, platform='77',
                doors=('73', '75'), hull=(BT1_LEFT + 24, -3084, -384, 264)),
    'BT2': dict(inner=(BT2_LEFT + 48, BT2_RIGHT_IN), floor=BT2_FLOOR, platform='78',
                doors=('79', '81'), hull=(BT2_LEFT + 24, -180, -376, 264)),
}
TANK_HULLS = []
for name, d in BT_DEF.items():
    i0, i1 = d['inner']
    tank = (i1 - i0 - 96) / 3.0
    seps = [int(round(i0 + tank)), int(round(i0 + 2 * tank + 48))]
    d['seps'] = seps
    # 플랫폼 폭 맞춤
    p = sub.by_id(d['platform'])
    px0, px1, py0, py1 = get_rect(p)
    set_rect(p, i0, i1, py0, py1)
    # 칸막이: 아래는 대형 내벽 수직, 위는 기존 버튼문
    for sx, did in zip(seps, d['doors']):
        wall_v(sx, d['floor'] - 8, PLATFORM_TOP)
        door = sub.by_id(did)
        gap = sub.by_id(door.get('linked'))
        dx0, dx1, dy0, dy1 = get_rect(door)
        set_rect(door, sx + 12, sx + 36, dy0, dy1)
        gx0, gx1, gy0, gy1 = get_rect(gap)
        set_rect(gap, sx + 12, sx + 12 + (gx1 - gx0), gy0, gy1)
    hx0, hx1, hy0, hy1 = d['hull']
    bounds = [hx0, seps[0] + 24, seps[1] + 24, hx1]
    for k in range(3):
        TANK_HULLS.append((f'{name}-{k + 1}', bounds[k], bounds[k + 1], hy0, hy1))
    # 펌프 (배선 없음)
    tanks = [(i0, seps[0]), (seps[0] + 48, seps[1]), (seps[1] + 48, i1)]
    for k, (a, b) in enumerate(tanks):
        if name == 'BT1' and k == 0:
            px = b - 216            # 사다리가 왼쪽에 있으므로 오른쪽으로
        elif name == 'BT2' and k == 2:
            px = a + 8              # 사다리가 오른쪽에 있으므로 왼쪽으로
        else:
            px = int((a + b) / 2 - 100)
        small = (name == 'BT2' and k == 2)   # 사다리와 겹치지 않게 약간 작게
        el = sub.deco_item('pump', px, d['floor'] + (77 if small else 96), depth=0.82,
                           scale=0.4 if small else None)
        # 펌프는 실제 설비이므로 상호작용 가능 상태로 되돌린다
        for k2 in ('NonInteractable', 'NonPlayerTeamInteractable', 'InvulnerableToDamage', 'AllowSwapping'):
            el.attrib.pop(k2, None)
        el.set('Tags', 'pump,light,ballast')
        el.set('NonInteractable', 'False')
        el.set('InvulnerableToDamage', 'False')
    log(f'{name}: 내부 {i0}~{i1}, 칸막이 x={seps}, 탱크 폭 약 {tank:.0f}px')

# ======================================================================
# 2. 해치 (사다리 통로) - 내벽
# ======================================================================
HATCHES_INNER = [
    # (hatch_x, wall_top_y, 설명)
    (-5072, 1289, 'L1 좌상단 준비공간↔복도'),
    (-5072, 1033, 'L1'), (-5072, 776, 'L1'), (-5072, 520, 'L1'), (-5072, 264, 'L1'), (-5072, 8, 'L1'),
    (-4480, 1033, 'L2 감옥 로비 (기존 해치)'),
    (-2544, 1033, 'L8'), (-2544, 776, 'L8'), (-2544, 520, 'L8'),
    (-224, 1033, 'L4'), (-224, 776, 'L4'), (-224, 520, 'L4'),
    (-1216, 776, 'L7 레일건 사격실↔사격실'),
    (-1840, 264, 'L9 제작실↔하부 도크 통로'),
    (368, 264, 'L5 우하단'), (368, -8, 'L5 우하단'),
    (BT1_LEFT + 48 + 16, 264, 'L10 벨러스트 탱크1 입구(좌측 상단)'),
    (-432, 264, 'L11 벨러스트 탱크2 입구(우측 상단)'),
]
existing_hatch = {(-4480, 1033): '9303'}
PLATFORM_T = 'platform'
for hx, top, desc in HATCHES_INNER:
    w = find_wall('ff_x_wall', hx + 64, top - 24)
    cut(w, hx, hx + HATCH_W)
    if (hx, top) in existing_hatch:
        h = sub.by_id(existing_hatch[(hx, top)])
    else:
        g = sub.gap(hx, hx + HATCH_W, top - 54, top + 5, horizontal=False)
        h = sub.clone(HATCH_T, hx, hx + HATCH_W, top - 49, top, linked=g.get('ID'), SpriteDepth='0.7')
    sub.structure('platform', hx, top - 1, w=HATCH_W, depth=0.8)
    sub.structure('smallhorizontalback', hx, top - 11, w=HATCH_W, depth=0.67)

# 새 사다리
def ladder(x, top, bottom):
    return sub.clone(LADDER_T, x, x + 11, bottom, top)

ladder(BT1_LEFT + 48 + 16 + 64, 264 + 128, BT1_FLOOR)
ladder(-432 + 64, 264 + 128, BT2_FLOOR)
ladder(-5520, -120, -440)      # 좌하단 도킹 해치
log('사다리 추가: 벨러스트1 좌측 상단, 벨러스트2 우측 상단, 좌하단 도킹 해치')

# ======================================================================
# 3. 외벽 개방 (도킹 해치 4개 + 우측 도킹 포트)
# ======================================================================
# (외벽 ID, 해치 x, 위/아래, 기존 해치 아이템 ID)
SHELL_HATCH = [('2', -5584, 'top', '60'), ('4', 368, 'top', '62'),
               ('10', -5584, 'bottom', '58'), ('11', 368, 'bottom', '64')]
for sid, hx, side, hid in SHELL_HATCH:
    sh = sub.by_id(sid)
    sx0, sx1, sy0, sy1 = get_rect(sh)
    cut(sh, hx, hx + HATCH_W)
    by = sy0 + 73 if side == 'top' else sy1 - 2      # 외벽 안쪽 면에 맞춤
    sub.structure('shellaboard90dega', hx - 19, by, w=21, h=73, fx=True, depth=0.09)
    sub.structure('shellaboard90dega', hx + HATCH_W - 1, by, w=21, h=73, depth=0.09)
    htop = get_rect(sub.by_id(hid))[3]
    sub.structure('platform', hx, htop - 1, w=HATCH_W, depth=0.8)
    sub.structure('smallhorizontalback', hx, htop - 11, w=HATCH_W, depth=0.67)

sh9 = sub.by_id('9')
cut(sh9, 520, 728, axis='y')
sub.structure('shellaboard0dega', 1206, 731, w=73, h=20, depth=0.09)
sub.structure('shellaboard0dega', 1206, 523, w=73, h=20, fy=True, depth=0.09)
log('외벽 개방: 좌상/우상/좌하/우하 도킹 해치, 우측 도킹 포트')

# ======================================================================
# 4. 헐
# ======================================================================
sys.path.insert(0, HERE)
from rooms import ROOMS  # noqa: E402

bt1c, bt2c = BT1_LEFT + 24, BT2_LEFT + 24
hull_els = {}
for r in ROOMS(bt1c, bt2c):
    key, room, x0, x1, y0, y1, wet = r[:7]
    hull_els[key] = sub.hull(x0, x1, y0, y1, room, wet)
for key, x0, x1, y0, y1 in TANK_HULLS:
    hull_els[key] = sub.hull(x0, x1, y0, y1, 'roomname.ballast', True)

# 문 없이 이어진 공간을 나눈 곳 → 개방 갭
OPEN_GAPS = [(-3600, 1033, 1241)]
for gx, gy0, gy1 in OPEN_GAPS:
    sub.gap(gx - 8, gx + 8, gy0, gy1, horizontal=True)

total = ballast = 0
for key, el in hull_els.items():
    x0, x1, y0, y1 = get_rect(el)
    v = (x1 - x0) * (y1 - y0)
    total += v
    if key.startswith('BT'):
        ballast += v
bt1 = sum((b - a) * (d - c) for k, a, b, c, d in TANK_HULLS if k.startswith('BT1'))
bt2 = sum((b - a) * (d - c) for k, a, b, c, d in TANK_HULLS if k.startswith('BT2'))
log(f'헐 {len(hull_els)}개, 전체 부피 {total}, 밸러스트 {ballast} ({ballast / total * 100:.2f}%)')
log(f'BT1 {bt1}, BT2 {bt2}, 최적 밸러스트 수준 {NEUTRAL * total / ballast:.4f}')

# ======================================================================
# 5. 마감 + 6. 배경
# ======================================================================
import caps  # noqa: E402
caps.add_caps(sub, log)
background.build(sub, ROOMS(bt1c, bt2c), TANK_HULLS, log)

# ======================================================================
# 메타데이터
# ======================================================================
xs, ys = [], []
for e in R:
    if e.tag in ('Structure', 'Hull') and e.get('rect'):
        x0, x1, y0, y1 = get_rect(e)
        xs += [x0, x1]
        ys += [y0, y1]
R.set('dimensions', f'{max(xs) - min(xs)},{max(ys) - min(ys)}')
R.set('name', '히페리온 - 베이스2')
os.makedirs(os.path.dirname(OUT_XML), exist_ok=True)
save_sub(R, OUT, OUT_XML)
print('\n'.join(report))
print('saved', OUT)
