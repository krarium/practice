"""베이스4 배경: 용도가 바뀐 방 재구성 + 아이로/말라카이트/아나콘다식 강조 장식.

참고한 조합(바닐라 부품만)
- 아이로: 엔진실 decocolumn2 + finawingpart65 + CableHolderVertical 2 + labelsiconengine,
          유물 보관소 finadeco02 + ventconnectora5 + opdeco_mountedmonitor2 + opbg_shop3 + opbg_airlock1,
          무기고/창고 opdeco_rollupdoorframe
- 말라카이트: 천장 덕트(ventductlongb2 + ventductbendb1 + ventductb290deg), loosepanel, mountedmonitor3
- 아나콘다: 생활 공간 벽 장식판 finadeco10, FF_Wall_D2/Metal_Wall_6 패널
"""
import random

from background import Room, Occupancy, s_docking, s_cargo, s_airlock
from subxml import get_rect

random.seed(7)


def s_engine(r):
    r.base('FF_Wall_C3')
    r.sub.structure('bwbc', r.x0, r.floor + 96, w=r.x1 - r.x0, h=96 + 48, depth=0.979, color='25,25,25,255')
    r.ceiling_band(color='255,210,210,255')
    r.floor_band()
    for x in (r.cx0 + 8, r.cx1 - 56):
        r.sub.structure('decocolumn2', x, r.floor + 208, depth=0.97)
    for k in range(3):
        r.cable_col(int(r.cx0 + 90 + k * (r.w - 180) / 2), ident='CableHolderVertical 2')
    r.sub.structure('decowire13', r.cx0 + 120, r.ceil - 6, depth=0.96)
    r.sub.structure('ventpipea2', r.cx0, r.ceil - 40, w=r.w, depth=0.96)
    r.icon('labelsiconengine', 'right', dy=46)


def s_battery(r):
    r.base('opbg_generic6')
    r.overlay('bgpanels', depth=0.976, color='100,100,100,50', tex_scale='1.45,2')
    r.cable_row(y_from_ceil=30)
    for k in range(4):
        r.cable_col(int(r.cx0 + 20 + k * (r.w - 40) / 3), ident='CableHolderVertical 2')
    r.sub.structure('decowire11', r.cx1 - 90, r.ceil - 4, depth=0.96)
    r.icon('labelsiconelectricity', 'left', dy=36)


def s_artifact(r):
    r.base('opbg_shop3', color='148,149,163,255')
    r.ceiling_band()
    r.floor_band()
    w, h = r.sub.template_size('structures', 'opbg_airlock1')
    x = int((r.cx0 + r.cx1 - w) / 2)
    if r.occ.free(x, x + w, r.floor, r.floor + h):
        r.sub.structure('opbg_airlock1', x, r.floor + h, depth=0.978)
    r.wall_props([('s', 'finadeco02', dict(depth=0.885)), ('s', 'opdeco_mountedmonitor2', dict(depth=0.97)),
                  ('s', 'finadeco02', dict(depth=0.885))], y_center=r.ceil - 70)
    r.sub.structure('ventconnectora5', r.cx0 + 20, r.ceil - 6, depth=0.92)


def s_quest(r):
    s_cargo(r)


RESTYLE = {'engine': s_engine, 'battery': s_battery, 'artifact': s_artifact, 'docking': s_docking,
           'quest': s_quest}


# ------------------------------------------------------------------ 강조 장식
def accent(r, kind):
    sub = r.sub
    if kind == 'corridor' and r.w > 300:
        # 말라카이트식 천장 덕트
        sub.structure('ventductlongb2', r.cx0 + 40, r.ceil - 6, w=r.w - 80, depth=0.93, color='235,235,200,255')
        sub.structure('ventductbendb1', r.cx1 - 70, r.ceil - 2, depth=0.925, color='235,235,200,255')
        if r.w > 500:
            r.wall_props([('i', 'loosepanel', dict(depth=0.9))], y_center=r.floor + 120)
    elif kind == 'living' and r.w > 260:
        # 아나콘다식 벽 장식판
        r.wall_props([('s', 'finadeco10', dict(depth=0.89)), ('s', 'finadeco10', dict(depth=0.89))],
                     y_center=r.ceil - 50, gap=160)
    elif kind == 'tech' and r.w > 300:
        # 아이로식 핀 패널 + 세로 케이블
        w, h = sub.template_size('structures', 'finawingpart65')
        x = int(r.cx0 + (r.w - w) / 2)
        if r.occ.free(x, x + w, r.floor, r.floor + h):
            sub.structure('finawingpart65', x, r.floor + h, depth=0.982, color='99,111,77,255')
        r.cable_col(r.cx1 - 40, ident='CableHolderVertical 2')
    elif kind == 'cargo' and r.w > 520:
        # 아이로식 롤업 도어 프레임
        w, h = sub.template_size('structures', 'opdeco_rollupdoorframe')
        x = r.cx0 + 40
        if r.occ.free(x, x + w, r.floor, r.floor + h):
            sub.structure('opdeco_rollupdoorframe', x, r.floor + h, depth=0.88, color='77,77,77,255')
            r.occ.add(x, x + w, r.floor, r.floor + h)


ACCENT = {
    '복도': 'corridor', '좌측 수직 통로': 'corridor', '우측 수직 통로': 'corridor',
    '조리실': 'living', '식당': 'living', '함장실': 'living', 'roomname.medbay': 'living',
    'roomname.research': 'living', '식물실': 'living', '감옥 로비': 'living',
    'roomname.reactorroom': 'tech', 'roomname.electrical': 'tech', '제작실': 'tech', '사격실': 'tech',
    '레일건 사격실': 'tech', '우하단부 분해기': 'tech', '공기압식 이송실': 'tech',
    'roomname.cargo': 'cargo', 'roomname.armory': 'cargo',
}


def room_for_hull(sub, occ, hull, shells, key='X'):
    x0, x1, y0, y1 = get_rect(hull)
    return Room(sub, occ, key, x0, x1, y0, y1, shells)
