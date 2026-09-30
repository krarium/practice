"""웨이포인트 자동 생성 - 게임의 WayPoint.GenerateSubWaypoints 규칙을 따라 구현.

- 헐: 바닥 +110 높이, 가장자리 50 안쪽부터 100 간격, 좌우로 연결
- 플랫폼: 윗면 +110, 이미 가까운(100/110) 웨이포인트가 있으면 생략
- 사다리: 바닥 +110 에서 시작해 75 간격, 해치를 지나면 해치 위치에 gap 연결 웨이포인트, 벽/플랫폼 위 +110,
          끝 캡. 각 점은 좌우 가장 가까운 헐 웨이포인트(150/100)와 연결
- 문(가로 흐름 갭): 갭 아래 +110, 좌우 연결 (방-방 150/70, 외부 1000)
- 외벽 해치(세로 갭, 바깥과 연결): 갭 중심, 안쪽 방/사다리와 연결 + 외부 경로와 연결
- 외부: 선체 외곽을 따라 100 간격 순환 경로
"""
import xml.etree.ElementTree as ET

from subxml import get_rect

MIN_DIST, EDGE, HEIGHT = 100, 50, 110
LADDER_STEP = 75


class WP:
    def __init__(self, x, y, kind='Path', gap=None, ladder=None):
        self.x, self.y, self.kind, self.gap, self.ladder = x, y, kind, gap, ladder
        self.links = set()
        self.id = None


def build(sub, log):
    root = sub.root
    for e in list(root):
        if e.tag == 'WayPoint':
            root.remove(e)
    hulls = [(e, get_rect(e)) for e in root if e.tag == 'Hull']
    shells = [get_rect(e) for e in root if e.tag == 'Structure' and e.get('identifier', '').startswith('shell')]
    walls = [get_rect(e) for e in root if e.tag == 'Structure' and
             (e.get('identifier', '').startswith(('ff_', 'shell', 'inwalll90')) and float(e.get('SpriteDepth', '1')) < 0.3)]
    doors = {e.get('ID'): e for e in root if e.tag == 'Item' and e.find('Door') is not None}
    platforms = [get_rect(e) for e in root if e.tag == 'Structure' and 'platform' in e.get('identifier', '').lower()]
    gaps = {e.get('ID'): e for e in root if e.tag == 'Gap'}
    gap_door = {d.get('linked'): d for d in doors.values() if d.get('linked')}

    def hull_at(x, y):
        for e, (a, b, c, d) in hulls:
            if a <= x <= b and c <= y <= d:
                return e
        return None

    def floor_y(x, y):
        """(x,y) 아래의 가장 가까운 바닥(벽/외벽/플랫폼 윗면)."""
        best = None
        for a, b, c, d in walls + platforms:
            if a <= x <= b and d <= y + 2:
                if best is None or d > best:
                    best = d
        return best

    def blocked(p, q, ignore=None):
        (x1, y1), (x2, y2) = p, q
        lo_x, hi_x, lo_y, hi_y = min(x1, x2), max(x1, x2), min(y1, y2), max(y1, y2)
        rects = list(walls)
        for did, d in doors.items():
            if did != ignore:
                rects.append(get_rect(d))
        for a, b, c, d in rects:
            if a < hi_x and b > lo_x and c < hi_y and d > lo_y:
                # 세그먼트는 수평/수직이 대부분 → 사각형 겹침으로 판정
                if (x1 == x2 and a < x1 < b) or (y1 == y2 and c < y1 < d) or (x1 != x2 and y1 != y2):
                    return True
        return False

    pts = []

    def add(*a, **k):
        w = WP(*a, **k)
        pts.append(w)
        return w

    def link(a, b):
        if a is not b:
            a.links.add(b)
            b.links.add(a)

    def closest(w, direction, tol, horizontal=True, ignore_door=None, filt=None):
        best = None
        for o in pts:
            if o is w or (filt and not filt(o)):
                continue
            dx, dy = o.x - w.x, o.y - w.y
            if horizontal:
                if dx * direction <= 0 or abs(dx) > tol[0] or abs(dy) > tol[1]:
                    continue
            else:
                if dy * direction <= 0 or abs(dy) > tol[1] or abs(dx) > tol[0]:
                    continue
            d = dx * dx + dy * dy
            if best is None or d < best[0]:
                if blocked((w.x, w.y), (o.x, o.y), ignore_door) and not (ignore_door and horizontal):
                    continue
                best = (d, o)
        return best[1] if best else None

    # ---- 헐
    for e, (x0, x1, y0, y1) in hulls:
        if y1 - y0 < 100:
            continue
        on_shell = any(a <= (x0 + x1) / 2 <= b and c <= y0 <= d for a, b, c, d in shells)
        floor = y0 + 48 if on_shell else y0
        y = floor + HEIGHT
        if x1 - x0 < EDGE * 3:
            add((x0 + x1) / 2, y)
            continue
        prev = None
        x = x0 + EDGE
        while x <= x1 - EDGE:
            w = add(x, y)
            if prev:
                link(prev, w)
            prev = w
            x += MIN_DIST

    # ---- 플랫폼
    hull_only = list(pts)
    for a, b, c, d in platforms:
        if hull_at((a + b) / 2, d + 20) is None:
            continue
        prev = None
        x = a + EDGE
        while x <= b - EDGE:
            y = d + HEIGHT
            near = any(abs(o.x - x) <= MIN_DIST and abs(o.y - y) <= HEIGHT for o in hull_only)
            if near:
                prev = None
            else:
                w = add(x, y)
                if prev:
                    link(prev, w)
                prev = w
            x += MIN_DIST

    # ---- 사다리
    hull_pts = list(pts)
    for lad in [e for e in root if e.tag == 'Item' and e.get('identifier') == 'ladder']:
        lx0, lx1, ly0, ly1 = get_rect(lad)
        cx = (lx0 + lx1) / 2
        lid = lad.get('ID')
        bottom = add(cx, ly0 + 10, ladder=lid)
        chain = [(bottom, True)]
        g = floor_y(cx, ly0 + 10)
        start_h = (g if g is not None else ly0) + HEIGHT
        prev = bottom
        if abs(bottom.y - start_h) > 40 and hull_at(cx, start_h):
            s = add(cx, start_h, ladder=lid)
            link(s, bottom)
            chain.append((s, True))
            prev = s
        y = prev.y + LADDER_STEP
        while y < ly1 - 1:
            hit_door, hit_surface = None, None
            for did, d in doors.items():
                a, b, c, dd = get_rect(d)
                if (b - a) > (dd - c) and a <= cx <= b and prev.y < (c + dd) / 2 <= y:
                    hit_door = d
            if hit_door is None:
                for a, b, c, dd in walls + platforms:
                    if a <= cx <= b and prev.y < dd <= y and (dd - c) < 120:
                        hit_surface = dd
            if hit_door is not None:
                a, b, c, dd = get_rect(hit_door)
                w = add((a + b) / 2, (c + dd) / 2, gap=hit_door.get('linked'), ladder=lid)
                link(prev, w)
                chain.append((w, True))
                prev = w
                y = max((c + dd) / 2, y)
            elif hit_surface is not None:
                w = add(cx, hit_surface + HEIGHT, ladder=lid)
                link(prev, w)
                chain.append((w, True))
                prev = w
                y = max(w.y, y)
            else:
                w = add(cx, y, ladder=lid)
                link(prev, w)
                chain.append((w, False))
                prev = w
            y += LADDER_STEP
        if prev.y < ly1 - 40:
            w = add(cx, ly1 - 1, ladder=lid)
            link(prev, w)
            chain.append((w, True))
        lad_pts = {w for w, _ in chain}
        for w, conn in chain:
            if not conn:
                continue
            for direction in (-1, 1):
                o = closest(w, direction, (150, 100), filt=lambda o: o not in lad_pts and o.ladder is None)
                if o:
                    link(w, o)

    # ---- 문/개방 갭 (가로 흐름)
    def gap_hulls(g):
        x0, x1, y0, y1 = get_rect(g)
        if g.get('horizontal') == 'true':
            p = [(x0 - 1, (y0 + y1) / 2), (x1 + 1, (y0 + y1) / 2)]
        else:
            p = [((x0 + x1) / 2, y1 + 1), ((x0 + x1) / 2, y0 - 1)]
        return [hull_at(*q) for q in p]

    outside_links = []
    for gid, g in gaps.items():
        x0, x1, y0, y1 = get_rect(g)
        hs = gap_hulls(g)
        n = sum(h is not None for h in hs)
        if n == 0:
            continue
        door = gap_door.get(gid)
        if g.get('horizontal') == 'true':
            if y1 - y0 < 100:
                continue
            w = add((x0 + x1) / 2, y0 + HEIGHT, gap=gid)
            tol = (150, 70) if n == 2 else (1000, 1000)
            for direction in (-1, 1):
                o = closest(w, direction, tol, ignore_door=door.get('ID') if door is not None else None,
                            filt=lambda o: o.gap is None)
                if o:
                    link(w, o)
            if n == 1:
                outside_links.append(w)
        else:
            if n == 2 or x1 - x0 < 50:
                continue
            if any(p.gap == gid for p in pts):
                w = next(p for p in pts if p.gap == gid)
            else:
                w = add((x0 + x1) / 2, (y0 + y1) / 2, gap=gid)
                inside = next(h for h in hs if h is not None)
                direction = 1 if get_rect(inside)[3] > y1 else -1
                o = closest(w, direction, (50, 150), horizontal=False)
                if o:
                    link(w, o)
            outside_links.append(w)

    # ---- 외부 순환 경로
    xs = [v for r in shells for v in r[:2]]
    left, right = min(xs) - 120, max(xs) + 120
    ring_top, ring_bot = [], []
    x = left
    while x <= right:
        tops = [d for a, b, c, d in shells if a - 60 <= x <= b + 60]
        bots = [c for a, b, c, d in shells if a - 60 <= x <= b + 60]
        ring_top.append((x, (max(tops) if tops else max(r[3] for r in shells)) + 120))
        ring_bot.append((x, (min(bots) if bots else min(r[2] for r in shells)) - 120))
        x += MIN_DIST
    ring = [add(px, py) for px, py in ring_top] + [add(px, py) for px, py in reversed(ring_bot)]
    for a, b in zip(ring, ring[1:] + ring[:1]):
        link(a, b)
    ring_set = set(ring)
    for w in outside_links:
        o = min(ring, key=lambda r: (r.x - w.x) ** 2 + (r.y - w.y) ** 2)
        link(w, o)

    # ---- 고아 제거 + 저장
    pts = [p for p in pts if p.links]
    for p in pts:
        p.id = sub.new_id()
    for p in pts:
        el = ET.SubElement(root, 'WayPoint')
        el.set('ID', p.id)
        el.set('x', str(int(round(p.x))))
        el.set('y', str(int(round(p.y))))
        el.set('spawn', p.kind)
        el.set('Layer', '')
        if p.gap:
            el.set('gap', p.gap)
        if p.ladder:
            el.set('ladders', p.ladder)
        for k, o in enumerate(sorted(p.links, key=lambda o: o.id)):
            el.set(f'linkedto{k}', o.id)
    log(f'웨이포인트 {len(pts)}개 생성 (외부 순환 {len(ring_set)}개 포함)')
    return pts


def spawnpoint(sub, x, y, job=None, idtag=None, kind='Human'):
    el = ET.SubElement(sub.root, 'WayPoint')
    el.set('ID', sub.new_id())
    el.set('x', str(int(x)))
    el.set('y', str(int(y)))
    el.set('spawn', kind)
    el.set('Layer', '')
    if idtag:
        el.set('idcardtags', idtag)
    if job:
        el.set('job', job)
    return el
