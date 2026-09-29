"""배경 생성.

깊이(SpriteDepth) 규칙 - 바닐라 잠수함 통계 기준
  0.98~0.99  기본 배경벽 (방 전체)
  0.975      보조 패널 / 반투명 덧칠
  0.97       천장 띠(largehorizontalback), 바닥 띠(support beam), 기둥, 패널
  0.96       장식 배선, 배관
  0.90       사다리 뒤 세로 배경
  0.85~0.94  케이블 거치대, 라벨, 상자/가구 구조물
  0.84~0.90  배경용 아이템 (상호작용 없음 + 손상되지 않음)
캐릭터(약 0.5)·문/사다리(0.51)·벽(0.1)보다 모두 뒤에 그려진다.
"""
from subxml import get_rect
from rooms import floor_of

WALL_T = 48


class Occupancy:
    """기존 아이템(설비/가구/문/사다리) 영역 - 소품이 겹치지 않도록."""

    def __init__(self, sub):
        self.rects = []
        for e in sub.elements('Item'):
            if e.get('HiddenInGame') == 'True':
                continue
            x0, x1, y0, y1 = get_rect(e)
            ident = e.get('identifier', '')
            if ident == 'ladder':
                x0, x1 = x0 - 40, x1 + 40
            if ident.startswith(('door', 'windoweddoor')) or 'door' in ident:
                x0, x1 = x0 - 24, x1 + 24
            self.rects.append((x0, x1, y0, y1))

    def free(self, x0, x1, y0, y1):
        return not any(a < x1 and b > x0 and c < y1 and d > y0 for a, b, c, d in self.rects)

    def add(self, x0, x1, y0, y1):
        self.rects.append((x0, x1, y0, y1))


class Room:
    def __init__(self, sub, occ, key, x0, x1, y0, y1, shells):
        self.sub, self.occ, self.key = sub, occ, key
        self.x0, self.x1, self.y0, self.y1 = x0, x1, y0, y1
        self.floor = floor_of(key, y0)
        self.ceil = y1 - WALL_T
        ym = (self.floor + self.ceil) / 2
        left_shell = any(a - 1 <= x0 <= b + 1 and c <= ym <= d for a, b, c, d in shells)
        right_shell = any(a - 1 <= x1 <= b + 1 and c <= ym <= d for a, b, c, d in shells)
        self.cx0 = x0 + (48 if left_shell else 12)
        self.cx1 = x1 - (48 if right_shell else 12)
        self.h = self.ceil - self.floor
        self.w = self.cx1 - self.cx0

    # ---------------------------------------------------------------- layers
    def base(self, ident, depth=0.985, **kw):
        return self.sub.structure(ident, self.x0, self.y1, w=self.x1 - self.x0, h=self.y1 - self.y0,
                                  depth=depth, **kw)

    def overlay(self, ident, depth=0.975, **kw):
        return self.sub.structure(ident, self.cx0, self.ceil, w=self.w, h=self.h, depth=depth, **kw)

    def ceiling_band(self, ident='largehorizontalback', depth=0.97, **kw):
        return self.sub.structure(ident, self.x0, self.ceil + 20, w=self.x1 - self.x0, fy=True,
                                  depth=depth, **kw)

    def floor_band(self, ident='opdeco_supportbeam_horizontal', depth=0.972, **kw):
        return self.sub.structure(ident, self.x0, self.floor + 18, w=self.x1 - self.x0, depth=depth, **kw)

    def panel_top(self, ident='decopanel4', depth=0.97, **kw):
        return self.sub.structure(ident, self.cx0, self.ceil, w=self.w, depth=depth, **kw)

    def columns(self, ident='opdeco_supportbeam_vertical', every=416, depth=0.974, width=40):
        n = max(1, int(self.w // every))
        step = self.w / (n + 1)
        for k in range(1, n + 1):
            cx = int(self.cx0 + step * k - width / 2)
            if self.occ.free(cx - 8, cx + width + 8, self.floor, self.ceil):
                self.sub.structure(ident, cx, self.ceil + 8, h=self.h + 16, depth=depth)

    def cable_row(self, y_from_ceil=34, depth=0.85):
        self.sub.structure('CableHolderHorizontal2', self.cx0, self.ceil - y_from_ceil, w=self.w, depth=depth)

    def cable_col(self, x, depth=0.85, ident='CableHolderVertical'):
        self.sub.structure(ident, x, self.ceil, h=self.h, depth=depth)

    def icon(self, ident, where='left', dy=40):
        w, h = self.sub.template_size('structures', ident)
        x = self.cx0 + 24 if where == 'left' else (self.cx1 - 24 - w if where == 'right' else
                                                  int((self.cx0 + self.cx1 - w) / 2))
        y = self.ceil - dy
        if self.occ.free(x, x + w, y - h, y):
            self.sub.structure(ident, x, y, depth=0.85)
            self.occ.add(x, x + w, y - h, y)

    # ---------------------------------------------------------------- props
    def floor_props(self, props, gap=24, start=None, lift=0):
        """props: [(kind, ident, kwargs)], kind='s' 구조물 / 'i' 아이템. 바닥에 왼쪽부터 배치."""
        x = self.cx0 + 24 if start is None else start
        placed = 0
        for kind, ident, kw in props:
            kw = dict(kw)
            scale = kw.get('scale')
            w, h = self.sub.template_size('structures' if kind == 's' else 'items', ident, scale)
            y_top = self.floor + h + lift + kw.pop('dy', 0)
            while x + w <= self.cx1 - 24:
                if self.occ.free(x, x + w, self.floor, y_top):
                    if kind == 's':
                        self.sub.structure(ident, x, y_top, **kw)
                    else:
                        self.sub.deco_item(ident, x, y_top, **kw)
                    self.occ.add(x, x + w, self.floor, y_top)
                    placed += 1
                    x += w + gap
                    break
                x += 32
        return placed

    def wall_props(self, props, y_center=None, gap=48):
        """벽걸이 소품(포스터, 선반, 모니터). 방 가운데부터 좌우로."""
        yc = y_center if y_center is not None else self.floor + self.h * 0.62
        slots = []
        mid = (self.cx0 + self.cx1) / 2
        for k in range(0, int(self.w // 32)):
            slots += [mid + k * 32, mid - k * 32]
        for kind, ident, kw in props:
            kw = dict(kw)
            scale = kw.get('scale')
            w, h = self.sub.template_size('structures' if kind == 's' else 'items', ident, scale)
            yt = int(yc + h / 2 + kw.pop('dy', 0))
            for sx in slots:
                x0 = int(sx - w / 2)
                if x0 < self.cx0 + 16 or x0 + w > self.cx1 - 16:
                    continue
                if self.occ.free(x0 - gap / 2, x0 + w + gap / 2, yt - h, yt):
                    if kind == 's':
                        self.sub.structure(ident, x0, yt, **kw)
                    else:
                        self.sub.deco_item(ident, x0, yt, **kw)
                    self.occ.add(x0 - gap / 2, x0 + w + gap / 2, yt - h, yt)
                    break


# ====================================================================== 스타일
def s_corridor(r):
    r.base('FF_Wall_C1')
    r.ceiling_band()
    r.floor_band()
    r.columns(every=448)
    r.cable_row()


def s_shaft(r):
    r.base('FF_Wall_C2')
    r.ceiling_band()
    r.floor_band()
    r.cable_row()


def s_airlock(r):
    r.base('FF_Wall_H1', tex_scale='0.5,0.57')
    r.ceiling_band()
    w, h = r.sub.template_size('structures', 'opbg_airlock1')
    cx = int((r.cx0 + r.cx1 - w) / 2)
    if r.w >= w + 32:
        r.sub.structure('opbg_airlock1', cx, r.floor + h, depth=0.978)
    r.cable_col(r.cx0 + 8)
    r.cable_col(r.cx1 - 24)
    r.icon('labelsiconairlock', 'left')


def s_docking(r):
    s_airlock(r)
    # 도킹 해치 위/아래 세로 에어록 벽
    hatch_x = {'A1': -5584, 'B7': 368, 'G1': -5584, 'G4': 368}.get(r.key)
    if hatch_x is not None:
        r.sub.structure('Docking_Wall_BG2', hatch_x + 64 - 35, r.ceil + 24, h=r.h + 24, depth=0.976)


def s_prep(r):
    r.base('FF_Wall_E', tex_scale='0.6,0.5')
    r.panel_top()
    r.floor_band()
    r.icon('labelsicondiving', 'left', dy=48)
    r.cable_row(y_from_ceil=40)


def s_brig(r):
    r.base('roughbgwall', color='200,190,185,255')
    r.ceiling_band(depth=0.97)
    r.floor_band()
    if r.w > 140:
        r.wall_props([('s', 'crackedwall2', dict(depth=0.97))], y_center=r.floor + 150)


def s_brig_lobby(r):
    r.base('FF_Wall_G3')
    r.ceiling_band()
    r.floor_band()
    r.icon('labelsiconsecurity', 'center', dy=40)
    r.sub.structure('opdeco_construction_barriertape', r.cx0 + 16, 776 + 40, w=r.w - 32, depth=0.88)


def s_captain(r):
    r.base('opbg_manageroffice2')
    r.ceiling_band(depth=0.97)
    r.floor_band()
    r.wall_props([('s', 'opdeco_hrsign2', dict(depth=0.975)),
                  ('s', 'opdeco_hrcalendar', dict(depth=0.974)),
                  ('s', 'opdeco_propagandaposter1', dict(depth=0.973))])
    r.floor_props([('i', 'op_smallcouch', dict(depth=0.9)),
                   ('s', 'opdeco_hrheater', dict(depth=0.972))])


def s_reactor(r):
    r.base('opbg_generic6')
    r.overlay('bgpanels', depth=0.976, color='100,100,100,50', tex_scale='1.45,2')
    r.ceiling_band(depth=0.97, color='255,190,190,255')
    r.floor_band()
    for k in range(4):
        x = int(r.cx0 + 40 + k * (r.w - 96) / 3)
        r.cable_col(x)
    for k, x in enumerate((r.cx0 + 60, r.cx1 - 200)):
        r.sub.structure('decowire11', x, r.ceil - 20, depth=0.96)
    r.wall_props([('s', 'opdeco_nuclearsign', dict(depth=0.84)),
                  ('s', 'opdeco_nuclearsign', dict(depth=0.84))], y_center=r.ceil - 160)
    r.icon('labelsiconreactor', 'left', dy=60)
    r.sub.structure('decocolumn2', r.cx0 + 4, r.floor + 208, depth=0.97)
    r.sub.structure('decocolumn2', r.cx1 - 52, r.floor + 208, depth=0.97)


def s_electrical(r):
    r.base('opbg_generic6')
    r.overlay('bgpanels', depth=0.976, color='100,100,100,50', tex_scale='1.45,2')
    r.ceiling_band()
    r.floor_band()
    r.cable_row()
    for k in range(6):
        r.cable_col(int(r.cx0 + 30 + k * (r.w - 60) / 5))
    r.sub.structure('decowire15', r.cx1 - 180, r.ceil - 8, depth=0.96)
    r.icon('labelsiconelectricity', 'right', dy=50)


def s_medbay(r):
    r.base('opbg_manageroffice3', color='239,196,170,255')
    r.panel_top(depth=0.97)
    r.floor_band()
    r.icon('labelsiconmedical', 'right', dy=50)
    r.wall_props([('i', 'op_huskposter1', dict(depth=0.9)),
                  ('i', 'opdeco_medcompartment3', dict(depth=0.88)),
                  ('i', 'opdeco_medcompartment3', dict(depth=0.88))], y_center=r.floor + 150)


def s_research(r):
    r.base('opbg_services1', color='150,150,150,255')
    r.panel_top()
    r.floor_band()
    r.wall_props([('s', 'opdeco_monitor01', dict(depth=0.975)),
                  ('i', 'opdeco_mountedmonitor1', dict(depth=0.88)),
                  ('i', 'opdeco_medcompartment1', dict(depth=0.88)),
                  ('s', 'opdeco_monitor01', dict(depth=0.975))])
    r.floor_props([('s', 'opdeco_box3', dict(depth=0.9)), ('i', 'opdeco_trashcan', dict(depth=0.9))])
    r.columns(every=460)


def s_greenhouse(r):
    r.base('opbg_services2')
    r.ceiling_band()
    r.floor_band()
    r.wall_props([('s', 'opdeco_storageseedshelf', dict(depth=0.9)),
                  ('s', 'opdeco_storageseedshelf', dict(depth=0.9)),
                  ('s', 'opdeco_storageseedshelf', dict(depth=0.9))], y_center=r.floor + 150)
    r.floor_props([('i', 'op_gardenbags2', dict(depth=0.9)),
                   ('i', 'op_gardenbags2', dict(depth=0.9)),
                   ('s', 'opdeco_hrheater', dict(depth=0.972))], gap=40)


def s_gunnery(r):
    r.base('FF_Wall_C3')
    r.panel_top()
    r.floor_band()
    r.columns(every=400)
    r.cable_row(y_from_ceil=44)
    r.icon('labelsiconweapons', 'left', dy=50)


def s_cargo(r):
    r.base('FF_Wall_G3')
    r.ceiling_band()
    r.floor_band()
    w, h = r.sub.template_size('structures', 'opdeco_StorageDoor')
    x = r.cx1 - w - 40
    if r.w > 420 and r.occ.free(x, x + w, r.floor, r.floor + h):
        r.sub.structure('opdeco_StorageDoor', x, r.floor + h, depth=0.99, color='122,122,122,255')
    r.floor_props([('s', 'opdeco_boxes1', dict(depth=0.88)),
                   ('s', 'metal_box3', dict(depth=0.87)),
                   ('s', 'opdeco_box3', dict(depth=0.88)),
                   ('s', 'opdeco_shelfsmall', dict(depth=0.89))], gap=16)
    r.icon('labelsarrowhorizontalb', 'left', dy=60)


def s_fabrication(r):
    r.base('FF_Wall_E2', tex_scale='0.5,0.4')
    r.overlay('bgpanels', depth=0.976, color='100,100,100,50', tex_scale='1.45,2')
    r.ceiling_band()
    r.floor_band()
    r.cable_row()
    r.icon('labelsiconengineering', 'right', dy=50)
    r.floor_props([('s', 'opdeco_ladder', dict(depth=0.88)), ('s', 'opdeco_boxes2', dict(depth=0.88))],
                  start=r.cx1 - 260)


def s_armory(r):
    r.base('opbg_generic6')
    r.ceiling_band()
    r.floor_band()
    r.icon('labelsiconweapons', 'left', dy=50)
    r.wall_props([('i', 'weaponholder', dict(depth=0.86)), ('i', 'weaponholder', dict(depth=0.86)),
                  ('i', 'weaponholder', dict(depth=0.86))], y_center=r.floor + 140, gap=24)
    r.floor_props([('s', 'opdeco_boxes1', dict(depth=0.88)), ('s', 'opdeco_box2', dict(depth=0.88))])


def s_galley(r):
    r.base('FF_Wall_G2', color='215,190,185,255')
    r.sub.structure('opbg_messhall1', r.cx0, r.ceil - 10, w=r.w, h=64, depth=0.975, color='77,77,77,255')
    r.floor_band()
    r.floor_props([('s', 'opdeco_SmallTable', dict(depth=0.9)),
                   ('i', 'opdeco_trashcan', dict(depth=0.9)),
                   ('s', 'opdeco_hrheater', dict(depth=0.972))], gap=40)


def s_mess(r):
    r.base('opbg_barracks2', color='220,185,170,255')
    r.ceiling_band()
    r.floor_band()
    r.floor_props([('i', 'op_cafeteriachair', dict(depth=0.9)),
                   ('s', 'opdeco_diningtable', dict(depth=0.94)),
                   ('s', 'opdeco_diningtable', dict(depth=0.94)),
                   ('i', 'op_cafeteriachair', dict(depth=0.9, fx=True))], gap=0, start=r.cx0 + 60)
    r.wall_props([('s', 'opdeco_propagandaposter3', dict(depth=0.97))], y_center=r.ceil - 70)


def s_lounge(r):
    r.base('opbg_barracks2', color='220,185,170,255')
    r.overlay('opbg_dorm1', depth=0.976, color='255,255,255,66')
    r.ceiling_band()
    r.floor_props([('i', 'opdeco_bunkbeds', dict(depth=0.85)),
                   ('i', 'opdeco_cabinetsdorm', dict(depth=0.84))], gap=16)
    r.wall_props([('s', 'opdeco_propagandaposter2', dict(depth=0.97))], y_center=r.ceil - 70)


STYLES = {
    'corridor': s_corridor, 'shaft': s_shaft, 'airlock': s_airlock, 'docking': s_docking,
    'prep': s_prep, 'brig': s_brig, 'brig_lobby': s_brig_lobby, 'captain': s_captain,
    'reactor': s_reactor, 'electrical': s_electrical, 'medbay': s_medbay, 'research': s_research,
    'greenhouse': s_greenhouse, 'gunnery': s_gunnery, 'cargo': s_cargo, 'fabrication': s_fabrication,
    'armory': s_armory, 'galley': s_galley, 'mess': s_mess, 'lounge': s_lounge,
}


def s_ballast(r, first):
    r.base('FF_Wall_BP', color='90,90,90,255')
    r.sub.structure('bwbc', r.x0, r.floor + 120, w=r.x1 - r.x0, h=120 + 48, depth=0.979,
                    color='25,25,25,255')
    r.ceiling_band(depth=0.97)
    r.sub.structure('ventpipea2', r.cx0, r.floor + 260, w=r.w, depth=0.96)
    r.cable_col(r.cx0 + 12, ident='CableHolderVertical 2')
    if first:
        r.icon('labelsiconballast', 'right', dy=40)


def s_dock(sub, occ):
    """하부 잠수정 도크(헐 없음) - 어두운 밸러스트 벽 + 지지대."""
    x0, x1, y0, y1 = -3084, -1996, -384, 264
    sub.structure('bwbc', x0, y1, w=x1 - x0, h=y1 - y0, depth=0.99, color='25,25,25,255')
    sub.structure('FF_Wall_BP', -3036, 216, w=992, h=48 + 8, depth=0.985, color='90,90,90,255')
    for x in (-3020, -2560, -2100):
        sub.structure('opdeco_supportbeam_vertical', x, 216, h=216 + 328, depth=0.97)
    sub.structure('opdeco_construction_barriertape', -3030, -250, w=980, depth=0.9)


def ladder_backs(sub):
    """모든 사다리 뒤에 세로 배경 띠."""
    n = 0
    for e in list(sub.elements('Item', 'ladder')):
        x0, x1, y0, y1 = get_rect(e)
        cx = (x0 + x1) / 2
        sub.structure('largeverticalback', int(cx - 32), y1, h=y1 - y0, depth=0.9)
        n += 1
    return n


def build(sub, rooms, tank_hulls, log):
    shells = [get_rect(e) for e in sub.elements('Structure')
              if e.get('identifier') in ('shella0deg', 'shella90deg')]
    occ = Occupancy(sub)
    missing = set()
    tmpl = sub.templates['structures']
    tmpl_i = sub.templates['items']

    # 템플릿 누락 방지: 없으면 해당 호출만 건너뜀
    orig_struct, orig_item = sub.structure, sub.deco_item

    def safe_struct(ident, *a, **k):
        if ident not in tmpl:
            missing.add(ident)
            return None
        return orig_struct(ident, *a, **k)

    def safe_item(ident, *a, **k):
        if ident not in tmpl_i:
            missing.add(ident)
            return None
        return orig_item(ident, *a, **k)

    sub.structure, sub.deco_item = safe_struct, safe_item
    try:
        styles_used = {}
        for key, room, x0, x1, y0, y1, wet, style, label in rooms:
            r = Room(sub, occ, key, x0, x1, y0, y1, shells)
            STYLES[style](r)
            styles_used[style] = styles_used.get(style, 0) + 1
        for k, (key, x0, x1, y0, y1) in enumerate(tank_hulls):
            r = Room(sub, occ, key, x0, x1, y0, y1, shells)
            s_ballast(r, key.endswith('-3'))
        s_dock(sub, occ)
        n = ladder_backs(sub)
    finally:
        sub.structure, sub.deco_item = orig_struct, orig_item
    log('배경 스타일 적용: ' + ', '.join(f'{k} {v}' for k, v in sorted(styles_used.items())))
    log(f'사다리 뒤 배경 {n}개')
    if missing:
        log('템플릿 없음(건너뜀): ' + ', '.join(sorted(missing)))
