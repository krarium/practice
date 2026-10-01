"""히페리온 - 베이스 3 → 베이스 4.

층 표기: 위에서부터 A B C D E F G (밸러스트는 G)
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from subxml import Sub, load_sub, save_sub, get_rect, set_rect  # noqa: E402
from background import Occupancy  # noqa: E402
import bg4  # noqa: E402
from wiring import Wiring  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'input', '히페리온 - 베이스 3.sub')
OUT = os.path.join(ROOT, '히페리온 - 베이스 4.sub')
OUT_XML = os.path.join(ROOT, 'build', '히페리온 - 베이스 4.xml')

sub = Sub(load_sub(SRC))
R = sub.root
report = []
log = report.append


def item(i):
    return sub.by_id(str(i))


def tagged(tag):
    for e in sub.elements('Item'):
        if tag in (e.get('Tags') or '').split(','):
            return e
    raise KeyError(tag)


def items_at(ident, x, y, tol=24):
    out = []
    for e in sub.elements('Item', ident):
        x0, x1, y0, y1 = get_rect(e)
        if abs(x0 - x) <= tol and abs(y1 - y) <= tol:
            out.append(e)
    return out


# ======================================================================
# 1. 헐: 새 버튼문에 맞춰 B층 분할, 방 이름 정리
# ======================================================================
def split_hull(hid, x, left_name, right_name, left_wet=False, right_wet=False):
    h = item(hid)
    x0, x1, y0, y1 = get_rect(h)
    assert x0 < x < x1, (hid, x0, x, x1)
    set_rect(h, x0, x, y0, y1)
    h.set('RoomName', left_name)
    h.set('Oxygen', str((x - x0) * (y1 - y0)))
    h.set('IsWetRoom', str(left_wet))
    h.set('AvoidStaying', str(left_wet))
    n = sub.clone(h, x, x1, y0, y1, RoomName=right_name, Oxygen=(x1 - x) * (y1 - y0),
                  IsWetRoom=str(right_wet), AvoidStaying=str(right_wet))
    return h, n


split_hull('1460', -1780, '복도', '함장 전용실')             # 버튼문 22245
split_hull('1461', -932, '복도', '복도')                     # 버튼문 613
split_hull('1462', 92, 'roomname.airlock', 'roomname.research')   # 버튼문 22101, 왼쪽 = 중앙 상단 도킹실
item('1462').set('IsWetRoom', 'True')
item('1462').set('AvoidStaying', 'True')
split_hull('1463', 956, '복도', '복도')                      # 버튼문 1263
for hid, name in (('1458', '퀘스트용 짐칸'), ('1466', '배터리실'), ('1499', 'roomname.engineroom'),
                  ('1501', '유물 보관소'), ('1477', '공기압식 이송실')):
    item(hid).set('RoomName', name)
log('헐: B층 4곳 분할(새 버튼문), 중앙 상단 도킹실(에어록) 신설, 방 이름 5곳 갱신')

# ======================================================================
# 2. B층 중앙 커스텀 해치 → 상부 외벽 개방 + 도킹 가능
# ======================================================================
HX = -80
shell = None
for e in sub.elements('Structure', 'shella0deg'):
    x0, x1, y0, y1 = get_rect(e)
    if x0 < HX + 64 < x1 and y0 < 713 < y1 + 60:
        shell = e
sx0, sx1, sy0, sy1 = get_rect(shell)
sub.clone(shell, sx0, HX, sy0, sy1)
sub.clone(shell, HX + 128, sx1, sy0, sy1)
sub.remove(shell)
sub.structure('shellaboard90dega', HX - 19, sy0 + 73, w=21, h=73, fx=True, depth=0.09)
sub.structure('shellaboard90dega', HX + 127, sy0 + 73, w=21, h=73, depth=0.09)
htop = get_rect(item(43))[3]
sub.structure('platform', HX, htop - 1, w=128, depth=0.8)
sub.structure('smallhorizontalback', HX, htop - 11, w=128, depth=0.67)
item(50).set('Tags', 'dock,light,중앙상단도킹포트')
log('B층 중앙 커스텀 해치(43) 위 외벽 절개, 도킹 해치(50) 사용 가능')

# ======================================================================
# 3. 배경: 용도가 바뀐 방 다시 꾸미기 + 강조 장식
# ======================================================================
REMOVE_BG = ['1819', '1820', '1821', '1822', '1823',        # 엔진실(옛 휴식실)
             '1635', '1639',                                # 배터리실(옛 복도)
             '1589',                                        # 퀘스트용 짐칸(옛 복도)
             '1828', '1831', '1832', '1833', '1834', '1835', '1836',   # 유물 보관소(옛 창고3)
             '1616']                                        # 중앙 도킹실 자리의 상자
for i in REMOVE_BG:
    sub.remove(item(i))
for i in ('1609', '1610'):                                   # 연구실 배경을 문(92) 오른쪽으로 축소
    e = item(i)
    x0, x1, y0, y1 = get_rect(e)
    set_rect(e, 92, x1, y0, y1)

shells = [get_rect(e) for e in sub.elements('Structure') if e.get('identifier', '').startswith('shell')]
occ = Occupancy(sub)
restyle = [('1499', 'engine'), ('1466', 'battery'), ('1458', 'quest'), ('1501', 'artifact'), ('1462', 'docking')]
for hid, style in restyle:
    key = {'docking': 'X'}.get(style, 'X')
    r = bg4.room_for_hull(sub, occ, item(hid), shells, key)
    if style == 'docking':
        r.key = 'CD'
        bg4.s_airlock(r)
        r.sub.structure('Docking_Wall_BG2', HX + 64 - 35, r.ceil + 24, h=r.h + 24, depth=0.976)
    else:
        bg4.RESTYLE[style](r)
log('배경 재구성: 엔진실, 배터리실, 퀘스트용 짐칸, 유물 보관소, 중앙 상단 도킹실')

n_acc = 0
for h in list(sub.elements('Hull')):
    kind = bg4.ACCENT.get(h.get('RoomName'))
    if not kind or h.get('ID') in dict(restyle):
        continue
    x0, x1, y0, y1 = get_rect(h)
    on_shell = any(a <= (x0 + x1) / 2 <= b and c <= y0 <= d for a, b, c, d in shells)
    bg4.accent(bg4.room_for_hull(sub, occ, h, shells, 'G1' if on_shell else 'X'), kind)
    n_acc += 1
log(f'강조 장식(아이로/말라카이트/아나콘다 방식) {n_acc}개 방')

# ======================================================================
# 4. 원격 쓰레기통 튜브 + 중앙 분해기 + 초대형 캐비닛
# ======================================================================
DECON = item(22130)
CHUTE = item(22137)
cx0, cx1, cy0, cy1 = get_rect(CHUTE)
GROUP = [(e, get_rect(e)) for e in (item(22138), item(22139), item(22140), item(1696))]

# 초대형 캐비닛 (분해 결과물 수령, AI 정리 대상)
huge_t = item(157)
huge = sub.clone(huge_t, 2196, 2196 + 226, 200, 200 + 188)
huge.set('Tags', 'container,locker,allowcleanup')
huge.set('linked', DECON.get('ID'))
ic = huge.find('ItemContainer')
if ic is not None:
    ic.set('contained', '')
occ.add(2196, 2422, 200, 388)
lab = sub.clone(item(1696), 2250, 2250 + 120, 392, 392 + 18)
lab.find('ItemLabel').set('Text', '분해 결과물 수령함')

CHUTE_ROOMS = {  # 헐 ID : 방
    '1490': '식당', '1471': '함장실', '1473': '의료실', '1485': '사격실', '1492': '창고1', '1493': '창고2',
    '1456': '상부 준비공간', '1503': '좌하단 준비실', '1507': '우하단부 준비실', '1498': '무기 보관실',
    '1488': '우측 준비실',
}
chutes = [CHUTE.get('ID'), '22121']
old = item(22144)                                   # 제작실에 있던 미연결 튜브
old.set('linked', DECON.get('ID'))
old.set('Tags', 'container,locker')
chutes.append('22144')
placed_rooms = []
for hid, name in CHUTE_ROOMS.items():
    x0, x1, y0, y1 = get_rect(item(hid))
    floor = y0 + 48 if any(a <= (x0 + x1) / 2 <= b and c <= y0 <= d for a, b, c, d in shells) else y0
    top = floor + (cy1 - get_rect(item(1478))[2])   # 원본 튜브(조리실)와 같은 높이
    for x in list(range(int(x1) - 140, int(x0) + 60, -24)):
        if occ.free(x - 8, x + 80, top - 150, top + 10):
            break
    else:
        log(f'튜브 자리 없음: {name}')
        continue
    dx, dy = x - cx0, top - cy1
    c = sub.clone(CHUTE, cx0 + dx, cx1 + dx, cy0 + dy, cy1 + dy, linked=DECON.get('ID'))
    for e, (a, b, cc, d) in GROUP:
        sub.clone(e, a + dx, b + dx, cc + dy, d + dy)
    occ.add(x - 8, x + 80, top - 150, top + 10)
    chutes.append(c.get('ID'))
    placed_rooms.append(name)
DECON.set('linked', ','.join([huge.get('ID')] + chutes))
DECON.set('DisplaySideBySideWhenLinked', 'True')
log(f'원격 쓰레기통 튜브 {len(chutes)}개 (신규 {len(placed_rooms)}: {", ".join(placed_rooms)}) → 중앙 분해기 연결')

# ======================================================================
# 5. 원자로 문 밖 소화기
# ======================================================================
wr = Wiring(sub, log)          # 템플릿 로드용 (그리드는 배선 단계에서 다시 만든다)
for door_x, side in ((-1776, -1), (-1232, 1)):
    d = items_at('doorwbuttons', door_x, -104, 30)[0]
    x0, x1, y0, y1 = get_rect(d)
    bx = x0 - 60 if side < 0 else x1 + 24
    br = copy.deepcopy(wr.tmpl['extinguisherbracket'])
    br.set('ID', sub.new_id())
    br.set('rect', f'{bx},{-312 + 150},36,102')
    ext = sub.clone(item(617), bx + 2, bx + 34, -312 + 150 - 64 - 16, -312 + 150 - 16)
    br.find('ItemContainer').set('contained', ext.get('ID'))
    R.append(br)
log('원자로 양쪽 문 밖에 소화기 거치대 + 소화기 배치')

# ======================================================================
# 6. 장치 설정
# ======================================================================
MAIN = tagged('main_terminal')
DOCK = tagged('dock_terminal')
MON = item(1235)
for t in (MAIN, DOCK):
    t.set('linked', ','.join(filter(None, [t.get('linked'), MON.get('ID')])))
    t.find('Steering').set('NeutralBallastLevel', '0.5')
MON.set('linked', f'{MAIN.get("ID")},{DOCK.get("ID")}')
DOCK.find('CustomInterface').set('Labels', '좌측 상단 도킹,중앙 상단 도킹,우측 상단 도킹,우측 중앙 도킹,좌측 하단 도킹,우측 하단 도킹')

for did in ('88', '90', '94', '100'):                      # 감옥 문: 손으로 못 열게
    item(did).find('Door').set('ToggleWhenClicked', 'False')

BATTERIES = [e for e in sub.elements('Item', 'battery')]
for b in BATTERIES:
    pc = b.find('PowerContainer')
    pc.set('Charge', pc.get('Capacity'))
    pc.set('RechargeSpeed', pc.get('MaxRechargeSpeed'))
log(f'배터리 {len(BATTERIES)}개 충전량 100%, 충전 속도 최대')

# ======================================================================
# 7. 게이트 + 배선
# ======================================================================
wr = Wiring(sub, log)
C = wr.connect
PWR, SIG, DOCKW, CELL = 'redwire', 'bluewire', 'greenwire', 'orangewire'

# (a0) 기존 게이트도 규칙대로: 내벽 안, 최저 깊이, 게임에서 숨김
for e in list(sub.elements('Item')):
    if e.get('identifier') in ('signalcheckcomponent', 'andcomponent', 'orcomponent', 'notcomponent',
                               'relaycomponent', 'memorycomponent', 'delaycomponent', 'xorcomponent') \
            and e.get('SpriteDepth') != '0.001':
        x0, x1, y0, y1 = get_rect(e)
        gx, gy = wr.gate_spot((x0 + x1) / 2, (y0 + y1) / 2)
        e.set('rect', f'{int(gx - 8)},{int(gy + 8)},16,16')
        e.set('SpriteDepth', '0.001')
        e.set('HiddenInGame', 'True')
        log(f'기존 게이트 {e.get("identifier")}({e.get("ID")}) → 내벽 안으로 이동')

# (a) 기존 배선: 숨김 + 직각 재배선
existing = {}
for e in list(sub.elements('Item')):
    panel = e.find('ConnectionPanel')
    if panel is None:
        continue
    for pin in panel:
        for l in pin.findall('link'):
            existing.setdefault(l.get('w'), [None, None])[int(l.get('i'))] = (e, pin.get('name'))
n_old = 0
for wid, ends in existing.items():
    if None in ends or wid not in wr.items:
        continue
    C(ends[0][0], ends[0][1], ends[1][0], ends[1][1], existing=wr.items[wid])
    n_old += 1
log(f'기존 배선 {n_old}개: 게임에서 숨김 + 벽/문/해치 따라 직각으로 재배선')

# (b) 전력망: 전력관리실 정션박스 18개를 하나의 망으로
JB = {i: item(i) for i in ('69', '70', '71', '72', '73', '74', '76', '77', '109', '110', '111', '112',
                           '113', '114', '115', '116', '117', '118')}
for a, b in (('118', '117'), ('117', '113'), ('113', '114'), ('114', '110'), ('110', '109')):
    C(JB[a], 'power', JB[b], 'power', PWR)

# (c) 항법 단말기 전환: 버튼 → 릴레이(메인) 토글, NOT → 릴레이(도킹) set_state
near_t = ((get_rect(MAIN)[0] + get_rect(DOCK)[1]) / 2, 176)
r_main = wr.gate('relaycomponent', near_t, IsOn='True', MaxPower='2000')
r_dock = wr.gate('relaycomponent', near_t, IsOn='False', MaxPower='2000')
n_t = wr.gate('notcomponent', near_t)
C(tagged('Terminal_change_button'), 'signal_out', r_main, 'toggle', SIG)
C(r_main, 'state_out', n_t, 'signal_in', SIG)
C(n_t, 'signal_out', r_dock, 'set_state', SIG)
C(JB['112'], 'power', r_main, 'power_in', PWR)
C(JB['112'], 'power', r_dock, 'power_in', PWR)
C(r_main, 'power_out', MAIN, 'power_in', PWR)
C(r_dock, 'power_out', DOCK, 'power_in', PWR)
C(JB['111'], 'power', MON, 'power_in', PWR)
C(JB['111'], 'power', item(22117), 'power_in', PWR)
log('항법 단말기 전환: 전환 버튼 → 릴레이(메인, 기본 ON) 토글 → NOT → 릴레이(도킹) — 항상 한쪽만 전원')

# (d) 엔진 / 펌프
ENGINE = item(815)
C(JB['73'], 'power', ENGINE, 'power_in', PWR)
C(MAIN, 'velocity_x_out', ENGINE, 'set_force', SIG)
C(DOCK, 'velocity_x_out', ENGINE, 'set_force', SIG)
PUMPS1 = [item(i) for i in ('1314', '1315', '1316')]
PUMPS2 = [item(i) for i in ('1319', '1320', '1321')]
bus1 = wr.gate('relaycomponent', (near_t[0] + 120, 176), IsOn='True')
bus2 = wr.gate('relaycomponent', (near_t[0] + 120, 176), IsOn='True')
for t in (MAIN, DOCK):
    C(t, 'velocity_y_out', bus1, 'signal_in1', SIG)
    C(t, 'velocity_y_out', bus2, 'signal_in1', SIG)
for bus, pumps, jb in ((bus1, PUMPS1, JB['74']), (bus2, PUMPS2, JB['77'])):
    C(jb, 'power', pumps[0], 'power_in', PWR)
    for a, b in zip(pumps, pumps[1:]):
        C(a, 'power_in', b, 'power_in', PWR)
    for p in pumps:
        C(bus, 'signal_out1', p, 'set_targetlevel', SIG)
log('엔진/펌프: 두 단말기 velocity_x → 엔진, velocity_y → 분배 릴레이 2개 → 펌프 6개, 전원 연결')

# (e) 도킹: 도킹 단말기 신호 1~6 → 도킹포트 toggle, 도킹 상태 → 커스텀 해치 set_state
DOCKS = [(49, 41), (50, 43), (22112, 22103), (53, 47), (52, 39), (51, 45)]
for n, (port, hatch) in enumerate(DOCKS, 1):
    C(DOCK, f'signal_out{n}', item(port), 'toggle', DOCKW)
    C(item(port), 'state_out', item(hatch), 'set_state', DOCKW)
log('도킹: 신호1~6 → 각 도킹포트 toggle(미도킹 시 도킹, 도킹 중 해제), state_out → 커스텀 해치 개폐')

# (f) 감옥: 문 앞 스위치 → 각 감옥 문
for btn, door in (('560', '88'), ('561', '94'), ('562', '100'), ('563', '90')):
    C(item(btn), 'signal_out', item(door), 'toggle', CELL)
log('감옥 1~4: 문 앞 스위치 → 문 toggle (문 직접 클릭 불가)')

# (g) 원자로 비상 정지 레버: 레버 ON(1)일 때만 shutdown
LEVER = tagged('reactor_switch')
chk = wr.gate('signalcheckcomponent', (get_rect(LEVER)[0], 176), TargetSignal='1', Output='1', FalseOutput='')
C(LEVER, 'signal_out', chk, 'signal_in', SIG)
C(chk, 'signal_out', item(108), 'shutdown', SIG)
log('원자로 비상 정지: 레버 → 신호 검사(1일 때만 통과) → 원자로 shutdown')

# (h) 배터리: 평소 출력 차단, Electric 버튼으로 토글
r_bat = wr.gate('relaycomponent', (get_rect(tagged('Electric_button'))[0], 176), IsOn='False')
C(tagged('Electric_button'), 'signal_out', r_bat, 'toggle', SIG)
BATTERIES.sort(key=lambda b: (get_rect(b)[2], get_rect(b)[0]))
nots = [wr.gate('notcomponent', (-3300 + k * 80, 176)) for k in range(3)]
for k, n in enumerate(nots):
    C(r_bat, 'state_out', n, 'signal_in', SIG)
    for b in BATTERIES[k * 4:(k + 1) * 4]:
        C(n, 'signal_out', b, 'disable_output', SIG)
C(JB['109'], 'power', BATTERIES[0], 'power_in', PWR)
C(JB['109'], 'power', BATTERIES[0], 'power_out', PWR)
for a, b in zip(BATTERIES, BATTERIES[1:]):
    C(a, 'power_in', b, 'power_in', PWR)
    C(a, 'power_out', b, 'power_out', PWR)
log('배터리실: 전력망에서 상시 충전, Electric 버튼 → 릴레이 토글 → NOT → disable_output (누르면 방전 허용)')

# (i) 중앙 분해기 전원
C(JB['118'], 'power', DECON, 'power_in', PWR)
log(f'신규 게이트: 릴레이 5, NOT 4, 신호 검사 1 / 배선 총 {wr.n_wires}개 (기존 재배선 포함)')

# ======================================================================
xs, ys = [], []
for e in R:
    if e.tag in ('Structure', 'Hull') and e.get('rect'):
        x0, x1, y0, y1 = get_rect(e)
        xs += [x0, x1]
        ys += [y0, y1]
R.set('dimensions', f'{max(xs) - min(xs)},{max(ys) - min(ys)}')
R.set('name', '히페리온 - 베이스 4')
os.makedirs(os.path.dirname(OUT_XML), exist_ok=True)
save_sub(R, OUT, OUT_XML)
print('\n'.join(report))
