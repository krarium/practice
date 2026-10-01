"""배선/게이트 배치.

규칙
- 게이트: 대형 내벽(ff_x_wall/ff_y_wall) 안에만 배치, SpriteDepth 최저(가장 앞), 게임에서 숨김.
- 배선: 내벽·외벽·문·해치 위로만 직각 이동, 게임에서 숨김.
  장치 쪽 끝은 장치 중심에서 가장 가까운 벽까지 수직(또는 수평) 한 번으로 내려온다.
"""
import copy
import heapq
import os
import xml.etree.ElementTree as ET

from subxml import get_rect

HERE = os.path.dirname(os.path.abspath(__file__))
G = 16
GATE_DEPTH = '0.001'
WIRE_COLORS = {
    'redwire': '254,23,17,255',
    'bluewire': '51,121,173,255',
    'greenwire': '56,143,111,255',
    'orangewire': '255,140,13,255',
}
ROUTE_STRUCTS = ('ff_x_wall', 'ff_y_wall', 'shella', 'inwalll90cables', 'y_wallwpipes')
ROUTE_ITEMS = ('doorwbuttons', 'windoweddoor', 'door', 'hatch', 'hatchwbuttons')


class Wiring:
    def __init__(self, sub, log):
        self.sub, self.log = sub, log
        self.tmpl = {e.get('identifier'): e for e in ET.parse(os.path.join(HERE, 'component_templates.xml')).getroot()}
        self.wire_tmpl = None
        for e in sub.elements('Item'):
            if e.get('identifier') in ('redwire', 'wire', 'bluewire') and e.find('Wire') is not None:
                self.wire_tmpl = e
                break
        self.items = {e.get('ID'): e for e in sub.elements('Item')}
        self.gate_cells = set()
        self.n_wires = 0
        self._build_grid()

    # ------------------------------------------------------------------ grid
    def _build_grid(self):
        xs, ys = [], []
        for e in self.sub.elements('Structure'):
            if e.get('identifier', '').startswith('shell'):
                x0, x1, y0, y1 = get_rect(e)
                xs += [x0, x1]
                ys += [y0, y1]
        self.X0 = (min(xs) // G - 2) * G
        self.Y0 = (min(ys) // G - 2) * G
        self.W = int((max(xs) - self.X0) // G + 3)
        self.H = int((max(ys) - self.Y0) // G + 3)
        self.route = bytearray(self.W * self.H)
        self.inner = bytearray(self.W * self.H)

        def mark(r, arr, val=1, shrink=0):
            x0, x1, y0, y1 = r
            x0, x1, y0, y1 = x0 + shrink, x1 - shrink, y0 + shrink, y1 - shrink
            i0 = max(0, int((x0 - self.X0 - G / 2) // G) + 1)
            i1 = min(self.W - 1, int((x1 - self.X0 - G / 2) // G))
            j0 = max(0, int((y0 - self.Y0 - G / 2) // G) + 1)
            j1 = min(self.H - 1, int((y1 - self.Y0 - G / 2) // G))
            for j in range(j0, j1 + 1):
                for i in range(i0, i1 + 1):
                    arr[j * self.W + i] = val

        for e in self.sub.elements('Structure'):
            ident = e.get('identifier', '')
            if not ident.startswith(ROUTE_STRUCTS) or e.get('DisableCollision') == 'True':
                continue
            if float(e.get('SpriteDepth', '0.5')) > 0.3:
                continue
            r = get_rect(e)
            mark(r, self.route)
            if ident in ('ff_x_wall', 'ff_y_wall'):
                mark(r, self.inner, shrink=8)
        for e in self.sub.elements('Item'):
            if e.get('identifier') in ROUTE_ITEMS:
                mark(get_rect(e), self.route)
        self._keep_main_component()

    def _keep_main_component(self):
        """벽과 이어지지 않은 외딴 칸(외벽 밖 해치 등)은 배선 경로에서 뺀다."""
        W, H, route = self.W, self.H, self.route
        comp = [-1] * (W * H)
        sizes = []
        for s in range(W * H):
            if not route[s] or comp[s] >= 0:
                continue
            k, st, n = len(sizes), [s], 0
            comp[s] = k
            while st:
                x = st.pop()
                n += 1
                i, j = x % W, x // W
                for ni, nj in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                    if 0 <= ni < W and 0 <= nj < H:
                        y = nj * W + ni
                        if route[y] and comp[y] < 0:
                            comp[y] = k
                            st.append(y)
            sizes.append(n)
        if len(sizes) > 1:
            big = max(range(len(sizes)), key=sizes.__getitem__)
            for s in range(W * H):
                if comp[s] >= 0 and comp[s] != big:
                    route[s] = 0

    def cell(self, x, y):
        return int((x - self.X0) // G), int((y - self.Y0) // G)

    def center(self, i, j):
        return self.X0 + i * G + G / 2, self.Y0 + j * G + G / 2

    def ok(self, i, j):
        return 0 <= i < self.W and 0 <= j < self.H and self.route[j * self.W + i]

    # ------------------------------------------------------------------ endpoints
    @staticmethod
    def pos(el):
        x0, x1, y0, y1 = get_rect(el)
        return (x0 + x1) / 2, (y0 + y1) / 2

    def stub(self, x, y):
        """장치 중심 → 가장 가까운 배선 가능 칸. (칸, [노드들])"""
        i, j = self.cell(x, y)
        if self.ok(i, j):
            cx, cy = self.center(i, j)
            return (i, j), [(cx, y)] if abs(cy - y) > 1 else [(cx, cy)]
        best = None
        for di, dj, pref in ((0, -1, 0), (0, 1, 1), (-1, 0, 3), (1, 0, 3)):
            for k in range(1, 60):
                if self.ok(i + di * k, j + dj * k):
                    cost = k + pref
                    if best is None or cost < best[0]:
                        best = (cost, (i + di * k, j + dj * k), di, dj)
                    break
        if best is None:
            raise RuntimeError(f'벽을 찾지 못함: {x},{y}')
        _, (ti, tj), di, dj = best
        cx, cy = self.center(ti, tj)
        if di == 0:
            return (ti, tj), [(cx, y), (cx, cy)]
        return (ti, tj), [(x, cy), (cx, cy)]

    def astar(self, a, b):
        W = self.W
        dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))
        start = (a[0], a[1], -1)
        dist = {start: 0}
        prev = {}
        pq = [(abs(a[0] - b[0]) + abs(a[1] - b[1]), 0, start)]
        while pq:
            f, g, s = heapq.heappop(pq)
            i, j, d = s
            if (i, j) == b:
                path = [(i, j)]
                while s in prev:
                    s = prev[s]
                    path.append((s[0], s[1]))
                return path[::-1]
            if g > dist.get(s, 1e18):
                continue
            for k, (di, dj) in enumerate(dirs):
                ni, nj = i + di, j + dj
                if not (0 <= ni < W and 0 <= nj < self.H) or not self.route[nj * W + ni]:
                    continue
                ng = g + 1 + (12 if d not in (-1, k) else 0)
                ns = (ni, nj, k)
                if ng < dist.get(ns, 1e18):
                    dist[ns] = ng
                    prev[ns] = s
                    heapq.heappush(pq, (ng + abs(ni - b[0]) + abs(nj - b[1]), ng, ns))
        raise RuntimeError(f'경로 없음 {a}->{b}')

    def path_nodes(self, p0, p1):
        c0, s0 = self.stub(*p0)
        c1, s1 = self.stub(*p1)
        cells = self.astar(c0, c1)
        pts = [self.center(*c) for c in cells]
        nodes = [s0[0]] + s0[1:] + pts + s1[::-1][1:] + [s1[0]]
        # 직선 구간 합치기
        out = []
        for p in nodes:
            p = (round(p[0], 1), round(p[1], 1))
            if out and p == out[-1]:
                continue
            if len(out) >= 2 and ((out[-2][0] == out[-1][0] == p[0]) or (out[-2][1] == out[-1][1] == p[1])):
                out[-1] = p
            else:
                out.append(p)
        return out

    # ------------------------------------------------------------------ wires
    def _pin(self, item, name):
        panel = item.find('ConnectionPanel')
        if panel is None:
            raise KeyError(f'{item.get("identifier")} {item.get("ID")} 연결 패널 없음')
        for c in panel:
            if c.get('name') == name:
                return c
        raise KeyError(f'{item.get("identifier")} {item.get("ID")} 핀 없음: {name}')

    def connect(self, a, pa, b, pb, color='bluewire', existing=None):
        """a.pa → b.pb 배선. existing 이 주어지면 그 배선 아이템의 노드만 다시 깐다."""
        a = self.items[a] if isinstance(a, str) else a
        b = self.items[b] if isinstance(b, str) else b
        nodes = self.path_nodes(self.pos(a), self.pos(b))
        if existing is not None:
            w = existing
        else:
            w = copy.deepcopy(self.wire_tmpl)
            w.set('identifier', color)
            w.set('ID', self.sub.new_id())
            w.set('SpriteColor', WIRE_COLORS[color])
            w.set('InventoryIconColor', WIRE_COLORS[color])
            w.attrib.pop('linked', None)
            self.sub.root.append(w)
            self.items[w.get('ID')] = w
            ET.SubElement(self._pin(a, pa), 'link', {'w': w.get('ID'), 'i': '0'})
            ET.SubElement(self._pin(b, pb), 'link', {'w': w.get('ID'), 'i': '1'})
        w.set('HiddenInGame', 'True')
        x, y = nodes[0]
        w.set('rect', f'{int(x)},{int(y)},42,16')
        w.find('Wire').set('nodes', ';'.join(f'{px:g};{py:g}' for px, py in nodes))
        self.n_wires += 1
        return w

    # ------------------------------------------------------------------ gates
    def gate_spot(self, x, y):
        """(x,y) 에서 가장 가까운 대형 내벽 칸 (다른 게이트와 겹치지 않게)."""
        ci, cj = self.cell(x, y)
        best = None
        for r in range(0, 80):
            for i in range(ci - r, ci + r + 1):
                for j in (cj - r, cj + r) if r else (cj,):
                    if not (0 <= i < self.W and 0 <= j < self.H):
                        continue
                    if not self.inner[j * self.W + i] or (i, j) in self.gate_cells:
                        continue
                    # 벽 가장자리 칸은 피해서 벽 한가운데에
                    if not all(self.inner[(j + dj) * self.W + i] for dj in (-1, 1)) and \
                       not all(self.inner[j * self.W + i + di] for di in (-1, 1)):
                        continue
                    d = abs(i - ci) + abs(j - cj)
                    if best is None or d < best[0]:
                        best = (d, i, j)
                for j in range(cj - r + 1, cj + r):
                    for i in (ci - r, ci + r):
                        if 0 <= i < self.W and 0 <= j < self.H and self.inner[j * self.W + i] \
                                and (i, j) not in self.gate_cells:
                            d = abs(i - ci) + abs(j - cj)
                            if best is None or d < best[0]:
                                best = (d, i, j)
            if best:
                break
        _, i, j = best
        for di in (-1, 0, 1):
            self.gate_cells.add((i + di, j))
        return self.center(i, j)

    def gate(self, ident, near, **component_attrs):
        t = copy.deepcopy(self.tmpl[ident])
        cx, cy = self.gate_spot(*near)
        t.set('ID', self.sub.new_id())
        t.set('rect', f'{int(cx - 8)},{int(cy + 8)},16,16')
        t.set('SpriteDepth', GATE_DEPTH)
        t.set('HiddenInGame', 'True')
        h = t.find('Holdable')
        if h is not None:
            h.set('Attached', 'True')
        comp = t[0]
        for k, v in component_attrs.items():
            comp.set(k, str(v))
        self.sub.root.append(t)
        self.items[t.get('ID')] = t
        return t
