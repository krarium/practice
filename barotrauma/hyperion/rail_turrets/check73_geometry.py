"""7.2 geometry checks: rail capture, turret-body clearance, hatch seals, periscope focus, lights.
Usage: python3 check73_geometry.py   (reads deliverables/)"""
from pathlib import Path
import sys, json, math
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / 'inspect/히페리온_작업파일/hyperion/tools'))
from subxml import load_sub, get_rect
P = BASE / 'deliverables/Hyperion_RailTurrets'
M = json.loads((BASE / 'deliverables/manifest.json').read_text())
root = load_sub(P / '히페리온 - 베이스 7.3.sub')
ids = {e.get('ID'): e for e in root if e.get('ID')}
out, bad = [], []
def ok(cond, msg):
    (out if cond else bad).append(msg)
def overlap(r, q, m=0):
    return r[0] < q[1] + m and q[0] < r[1] + m and r[2] < q[3] + m and q[2] < r[3] + m
hulls = [(e.get('ID'), get_rect(e), e.get('RoomName')) for e in root if e.tag == 'Hull']
solid = [(e.get('identifier'), e.get('ID'), get_rect(e)) for e in root
         if e.tag == 'Structure' and e.get('DisableCollision') != 'True']
doors = [(e.get('identifier'), e.get('ID'), get_rect(e)) for e in root
         if e.tag == 'Item' and e.find('Door') is not None]
prefab = (P / 'RailPorts.xml').read_text()
TOL = 256 if 'distancetolerance="256,256"' in prefab else None
ok(TOL and 'dockeddistance="0"' in prefab, 'rail prefabs: DistanceTolerance 256,256 and DockedDistance 0')
for rail in M['rails']:
    name = rail['name']
    child = load_sub(P / rail['child'])
    cid = {e.get('ID'): e for e in child if e.get('ID')}
    dock = cid[rail['child_dock']]
    da, db, dc, dd = get_rect(dock); dcx, dcy = (da + db) / 2, (dc + dd) / 2
    ch = [get_rect(e) for e in child if e.tag == 'Hull']
    ok(len(ch) == 1, f'{name}: one carriage hull')
    hr = ch[0]
    # CreateHulls needs a carriage hull overlapping the port vertically; none -> no hangar blockers
    ok(not (hr[2] < dd and dc < hr[3]), f'{name}: carriage hull clear of the port band (no docking blockers)')
    pts = rail['points']; N, H, HOME = rail['rail_end'], rail['junction'], rail['home']
    edges = [(i, i + 1) for i in range(N)] + [(H, N + 1)] + [(i, i + 1) for i in range(N + 1, HOME)]
    worst = max(max(abs(pts[a][0] - pts[b][0]), abs(pts[a][1] - pts[b][1])) for a, b in edges)
    ok(worst <= 80 and worst < TOL, f'{name}: largest step {worst}px (capture tolerance {TOL})')
    # anchors sit on the points
    for i, pid in enumerate(rail['ports']):
        a, b, c, d = get_rect(ids[pid])
        if abs((a + b) / 2 - pts[i][0]) > 1 or abs((c + d) / 2 - pts[i][1]) > 1:
            bad.append(f'{name}: anchor {i} off its point'); break
    else:
        out.append(f'{name}: {len(pts)} anchors on their points')
    # carriage body clearance at every position (body = hull rect relative to the dock)
    hits = set()
    for x, y in pts:
        body = (x + hr[0] - dcx, x + hr[1] - dcx, y + hr[2] - dcy, y + hr[3] - dcy)
        for hid, r, rn in hulls:
            if overlap(body, r, 4): hits.add(f'hull {hid} {rn}')
        for ident, sid, r in solid:
            if overlap(body, r, 4): hits.add(f'{ident} {sid}')
        for ident, did, r in doors:
            if overlap(body, r, 4): hits.add(f'{ident} {did}')
    ok(not hits, f'{name}: carriage body touches nothing of Hyperion at all {len(pts)} positions' + (f' -> {sorted(hits)}' if hits else ''))
    # turret path through the hatch opening
    hx = [get_rect(ids[h]) for h in rail['hatches']]
    x0, x1 = min(r[0] for r in hx), max(r[1] for r in hx)
    ok(all(x0 + 120 <= pts[i][0] <= x1 - 120 for i in range(N + 1, HOME + 1)), f'{name}: hangar path centred in the {x1 - x0}px hatch opening')
    # periscope focus: last aim recipient must be the double coilgun
    guns = {g: cid[g].get('identifier') for g in rail['child_guns']}
    ends = {}
    for e in child:
        for c in e.findall('ConnectionPanel/*'):
            for l in c.findall('link'): ends.setdefault(l.get('w'), []).append((e, c.get('name')))
    aim_rx = [e for e in child if e.get('identifier') == 'wificomponent' and e.find('WifiComponent').get('Channel') == str(rail['channel'] + 3)][0]
    order = []
    for l in next(c for c in aim_rx.find('ConnectionPanel') if c.get('name') == 'signal_out').findall('link'):
        order += [x.get('identifier') for x, p in ends[l.get('w')] if x is not aim_rx]
    ok(order[-1] == 'doublecoilgun', f'{name}: aim wire order {order} -> periscope focuses the double coilgun')
    for g in rail['child_guns']:
        t = cid[g].find('Turret')
        ok(t.get('RotationLimits') == '0,360', f'{name} {guns[g]}: full 360 rotation')
        want = '0' if name == 'upper' else '180'
        ok(t.get('BaseRotation') == want and cid[g].get('Rotation') == want, f'{name} {guns[g]}: base rotation {want}')
    ends_x = (pts[0][0], pts[N][0])
    out.append(f'{name}: rail x {ends_x[0]}..{ends_x[1]}, junction {pts[H]}, home {pts[HOME]}')
# hatch seals (Gap.FindHulls: 1px above / below the gap, local rects, inclusive)
def hull_at(x, y):
    for hid, (a, b, c, d), rn in hulls:
        if a <= x <= b and c <= y <= d: return hid, rn
    return None
for rail in M['rails']:
    for h in rail['hatches']:
        g = ids[ids[h].get('linked')]
        a, b, c, d = get_rect(g); cx = (a + b) / 2
        top, bot = hull_at(cx, d + 1), hull_at(cx, c - 1)
        ok(top and bot, f'hatch {h}: gap joins {top} / {bot} (no open side to the sea)')
for i, (ha, ra, _) in enumerate(hulls):
    for hb, rb, _ in hulls[i + 1:]:
        if overlap(ra, rb): bad.append(f'hull overlap {ha}/{hb}')
# lights
lc = [(e.get('identifier'), l) for e in root if e.tag == 'Item' for l in e.findall('LightComponent')]
tubes = [l for i, l in lc if i == 'lightfluorescentl01']
ok(all(l.get('Range') == '420' and l.get('LightColor').endswith(',115') for l in tubes), f'{len(tubes)} ceiling tubes at range 420, alpha 115')
shadow = sum(1 for i, l in lc if l.get('CastShadows') == 'True')
ok(shadow <= 100, f'shadow-casting lights {shadow} (editor limit 100)')
lad = [get_rect(e) for e in root if e.get('identifier') == 'ladder' and get_rect(e)[2] == -904 and get_rect(e)[3] == -200]
low = M['rails'][1]; lx = low['points'][low['home']][0]
lchild = load_sub(P / low['child']); lart = [get_rect(e) for e in lchild if e.tag in ('Structure',) or e.get('identifier') in ('doublecoilgun', 'railgun')]
span = (lx + min(r[0] for r in lart) - 18, lx + max(r[1] for r in lart) + 18)
ok(lad and lad[0][0] > span[1], f'lower hangar ladder x {lad[0][0]}..{lad[0][1]} clear of the lower turret path + guide rails {span[0]:.0f}..{span[1]:.0f}')
hatch = [get_rect(e) for e in root if e.get('identifier') == 'hatchwbuttons' and get_rect(e)[2] == -361 and get_rect(e)[0] <= lad[0][0] <= get_rect(e)[1]]
ok(hatch and hatch[0][0] <= lad[0][0] and lad[0][1] <= hatch[0][1], f'ladder passes its ceiling hatch {hatch[0][:2]}')
# visual rails
vr = [ids[i] for i in M['visual_rails']]
ok(vr and all(e.get('DisableCollision') == 'True' and e.get('Indestructible') == 'True' and e.get('NoAITarget') == 'True'
              and float(e.get('SpriteDepth')) == 0.0015 for e in vr), f'{len(vr)} visual rail beams: no collision, indestructible, depth 0.0015')
def rbox(e):
    a, b, c, d = get_rect(e); t = math.radians(float(e.get('Rotation', '0') or 0))
    cx, cy, w, h = (a + b) / 2, (c + d) / 2, (b - a) / 2, (d - c) / 2
    ex, ey = abs(w * math.cos(t)) + abs(h * math.sin(t)), abs(w * math.sin(t)) + abs(h * math.cos(t))
    return cx - ex, cx + ex, cy - ey, cy + ey
hatch_ids = {h for r in M['rails'] for h in r['hatches']}
front = [e for e in root if e.tag in ('Structure', 'Item') and e.get('rect') and e.get('HiddenInGame') != 'True'
         and e.get('ID') not in M['visual_rails'] and e.get('ID') not in hatch_ids and float(e.get('SpriteDepth', '1')) <= 0.0015]
cover = sorted({f"{e.get('identifier')}#{e.get('ID')}" for e in front for v in vr if overlap(get_rect(e), rbox(v))})
ok(not cover, f'nothing visible is drawn in front of the rails except the hangar hatches' + (f' -> {cover}' if cover else ''))
ok(all(ids[h].get('SpriteDepth') == '0.001' for r in M['rails'] for h in r['hatches']), 'hangar hatches depth 0.001 (in front of the rails)')
for rail in M['rails']:
    child = load_sub(P / rail['child']); cid = {e.get('ID'): e for e in child if e.get('ID')}
    gun = cid[rail['child_guns'][0]]
    ok(any(c.get('name') == 'set_light' and c.findall('link') for c in gun.find('ConnectionPanel')), f"{rail['name']}: turret light wired (set_light)")
    ok(any(e.get('identifier') == 'lightleds01' for e in child), f"{rail['name']}: carriage LED present")
    ok(not any(e.get('identifier') == 'ff_x_wall' for e in child), f"{rail['name']}: no hidden backplate wall")
    flips = [e.get('identifier') for e in child if e.tag == 'Structure' and (e.get('flippedy') == 'true')]
    out.append(f"{rail['name']}: {rail['rail_end'] + 1} rail anchors, branch {rail['home'] - rail['rail_end']}, flipped-y art pieces {len(flips)}")
print('\n'.join('OK   ' + m for m in out)); print('\n'.join('FAIL ' + m for m in bad))
sys.exit(1 if bad else 0)
