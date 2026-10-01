"""내벽 마감(대형 내벽 마감) 자동 배치 - 바닐라 배치 통계 기반.

- 수평벽 자유 끝:           inwalllcaph1 (27x48)  왼쪽 끝 / 오른쪽 끝은 flippedx
- 수평벽 끝 + 수직벽 L자:    inwalllcaph3 (49x57)  수직벽이 아래면 윗면 정렬, 위면 flippedy
- T자/십자 교차:            inwalllcaph2 (52x48)  수직벽 x 에 정렬
- 수직벽 자유 끝:           inwalllcapy2 (48x28)  아래 끝은 flippedy
- 외벽과 닿는 끝은 외벽이 덮으므로 생략
"""
from subxml import get_rect

H_IDS = ('ff_x_wall',)
V_IDS = ('ff_y_wall',)
TOL = 3


def _inside(px, py, r, tol=0):
    x0, x1, y0, y1 = r
    return x0 - tol <= px <= x1 + tol and y0 - tol <= py <= y1 + tol


def add_caps(sub, log):
    H, V, S = [], [], []
    for e in sub.elements('Structure'):
        i = e.get('identifier', '')
        if i in H_IDS:
            H.append((e, get_rect(e)))
        elif i in V_IDS:
            V.append((e, get_rect(e)))
        elif i in ('shella0deg', 'shella90deg'):
            S.append((e, get_rect(e)))

    placed = set()
    count = {'caph1': 0, 'caph2': 0, 'caph3': 0, 'capy2': 0}

    def put(ident, x, ytop, color, fx=False, fy=False):
        key = (ident, int(x), int(ytop), fx, fy)
        if key in placed:
            return
        placed.add(key)
        el = sub.structure(ident, x, ytop, fx=fx, fy=fy, depth=0.03, color=color)
        el.set('NoAITarget', 'True')
        count[ident.replace('inwalll', '')] += 1

    def touches_shell(px, py):
        return any(_inside(px, py, r, 1) for _, r in S)

    # ---------------------------------------------------------- 수평벽
    for e, (x0, x1, y0, y1) in H:
        col = e.get('SpriteColor')
        ym = (y0 + y1) / 2
        for side, ex in (('L', x0), ('R', x1)):
            probe = ex - 2 if side == 'L' else ex + 2
            if touches_shell(probe, ym):
                continue
            v = None
            for ve, (vx0, vx1, vy0, vy1) in V:
                if vx0 - TOL <= ex <= vx1 + TOL and vy0 - TOL <= y1 and vy1 + TOL >= y0:
                    v = (vx0, vx1, vy0, vy1)
                    break
            if v is None:
                if side == 'L':
                    put('inwalllcaph1', ex, y1, col)
                else:
                    put('inwalllcaph1', ex - 25, y1, col, fx=True)
                continue
            vx0, vx1, vy0, vy1 = v
            up = vy1 > y1 + TOL
            down = vy0 < y0 - TOL
            if up and down:
                put('inwalllcaph2', vx0, y1, col)
            elif down:
                put('inwalllcaph3', vx0, y1, col, fx=(side == 'R'))
            elif up:
                put('inwalllcaph3', vx0, y0 + 57, col, fx=(side == 'R'), fy=True)
        # 수평벽 중간에 붙는 수직벽 (T자)
        for ve, (vx0, vx1, vy0, vy1) in V:
            if not (x0 + TOL < vx0 and vx1 < x1 - TOL):
                continue
            if abs(vy1 - y0) <= TOL + 16 or abs(vy0 - y1) <= TOL or (vy0 < y1 and vy1 > y0):
                put('inwalllcaph2', vx0, y1, col)

    # ---------------------------------------------------------- 수직벽
    for e, (x0, x1, y0, y1) in V:
        col = e.get('SpriteColor')
        xm = (x0 + x1) / 2
        for side, ey in (('T', y1), ('B', y0)):
            probe = ey + 2 if side == 'T' else ey - 2
            if touches_shell(xm, probe):
                continue
            if any(_inside(xm, probe, r, TOL) or _inside(xm, ey, r, 0) for _, r in H):
                continue
            if side == 'T':
                put('inwalllcapy2', x0, y1, col)
            else:
                put('inwalllcapy2', x0, y0 + 28, col, fy=True)
    log('내벽 마감: ' + ', '.join(f'{k} {v}개' for k, v in count.items()))
