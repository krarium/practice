"""히페리온 규칙/무결성 검사. 사용법: python3 tools/check_rules.py <파일.sub>

검사 항목
- ID 중복, 헐 겹침, 갭-헐 연결(Gap.FindHulls 와 같은 1px 바깥 탐색점), 문/해치-갭 링크
- 전원 배선 유효성(Powered.ValidPowerConnection: 정션박스/도킹포트가 아니면 출력↔입력만 유효)
- 배선 규칙: 게임에서 숨김, 직각(대각선 구간 없음), 양 끝 연결, 핀당 5개 이하
- 게이트 규칙: 게임에서 숨김, SpriteDepth 0.001, 대형 내벽(ff_x_wall/ff_y_wall) 안
- 웨이포인트 연결 덩어리 수
- 밸러스트 비율과 항법 단말기 NeutralBallastLevel(물 7% = 중성 부력)
- 엔드게임 크기 경고(가로 80m / 세로 32m 초과)
- 전원 입력이 비어 있는 장치
"""
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from subxml import Sub, load_sub, get_rect  # noqa: E402
from wiring import Wiring  # noqa: E402

GATES = ('relaycomponent', 'notcomponent', 'andcomponent', 'orcomponent', 'xorcomponent', 'signalcheckcomponent',
         'memorycomponent', 'delaycomponent', 'regexcomponent', 'addercomponent', 'subtractcomponent',
         'multiplycomponent', 'dividecomponent', 'greatercomponent', 'equalscomponent', 'colorcomponent',
         'oscillator', 'wificomponent', 'smallitem_switch', 'concatcomponent', 'trigonometriccomponent',
         'exponentiationcomponent', 'modulocomponent', 'roundcomponent', 'squarerootcomponent', 'funccomponent')
WIRE_IDS = ('wire', 'redwire', 'bluewire', 'greenwire', 'orangewire', 'blackwire', 'whitewire', 'yellowwire',
            'brownwire')
POWER = ('power_in', 'power', 'power_out')


def main(path):
    root = load_sub(path)
    sub = Sub(root)
    out = []

    def say(level, msg):
        out.append(f'[{level}] {msg}')

    # ---------------------------------------------------------------- 기본
    ids = Counter(e.get('ID') for e in root if e.get('ID'))
    dup = [i for i, n in ids.items() if n > 1]
    if dup:
        say('오류', f'ID 중복: {dup[:20]}')
    hulls = [(e.get('ID'), get_rect(e), e.get('RoomName')) for e in root if e.tag == 'Hull']
    for i, (a, ra, _) in enumerate(hulls):
        for b, rb, _ in hulls[i + 1:]:
            if ra[0] < rb[1] and rb[0] < ra[1] and ra[2] < rb[3] and rb[2] < ra[3]:
                say('오류', f'헐 겹침 {a} {ra} / {b} {rb}')

    def hull_at(x, y):
        for hid, (x0, x1, y0, y1), room in hulls:
            if x0 <= x <= x1 and y0 <= y <= y1:
                return hid
        return None

    gaps = {e.get('ID'): e for e in root if e.tag == 'Gap'}
    linked = {}
    for e in root:
        if e.tag == 'Item' and e.get('linked'):
            for g in e.get('linked').split(','):
                if g in gaps:
                    linked[g] = e.get('identifier')
        if e.tag == 'Item' and e.get('identifier', '') in ('doorwbuttons', 'windoweddoor', 'windoweddoorwbuttons',
                                                           'door', 'hatch', 'hatchwbuttons'):
            if not e.get('linked') or e.get('linked').split(',')[0] not in gaps:
                say('오류', f'문/해치에 갭 링크 없음: {e.get("identifier")}#{e.get("ID")}')
    for gid, g in gaps.items():
        x0, x1, y0, y1 = get_rect(g)
        if g.get('horizontal') == 'true':
            pts = [(x0 - 1, (y0 + y1) / 2), (x1 + 1, (y0 + y1) / 2)]
        else:
            pts = [((x0 + x1) / 2, y1 + 1), ((x0 + x1) / 2, y0 - 1)]
        hs = [hull_at(*p) for p in pts]
        n = sum(h is not None for h in hs)
        if n == 0:
            say('참고', f'갭 {gid}({linked.get(gid, "개방 갭")}) 양쪽 모두 헐 없음 {x0, x1, y0, y1} '
                       f'- 하부 도크 바닥 커스텀 해치라면 정상(도크는 항상 물)')
        elif n == 2 and hs[0] == hs[1]:
            say('오류', f'갭 {gid} 양쪽이 같은 헐 {hs[0]}')

    # ---------------------------------------------------------------- 배선
    ends = defaultdict(list)
    for e in root:
        p = e.find('ConnectionPanel') if e.tag == 'Item' else None
        if p is None:
            continue
        for c in p:
            n = len(c.findall('link'))
            if n > 5:
                say('오류', f'{e.get("identifier")}#{e.get("ID")}.{c.get("name")} 배선 {n}개 (최대 5)')
            for l in c.findall('link'):
                ends[l.get('w')].append((e, c))
    n_w = diag = unhidden = dangling = bad_power = 0
    for e in root:
        if e.tag != 'Item' or e.get('identifier') not in WIRE_IDS or e.find('Wire') is None:
            continue
        n_w += 1
        nodes = e.find('Wire').get('nodes') or ''
        v = [float(x) for x in nodes.split(';') if x]
        pts = list(zip(v[::2], v[1::2]))
        d = sum(1 for a, b in zip(pts, pts[1:]) if a[0] != b[0] and a[1] != b[1])
        ee = ends.get(e.get('ID'), [])
        desc = ' ↔ '.join(f'{x.get("identifier")}#{x.get("ID")}.{c.get("name")}' for x, c in ee) or '(연결 없음)'
        if d:
            diag += 1
            say('규칙', f'배선 {e.get("identifier")}#{e.get("ID")} 대각선 구간 {d}개: {desc}')
        if e.get('HiddenInGame') != 'True':
            unhidden += 1
            say('규칙', f'배선 {e.get("identifier")}#{e.get("ID")} 게임에서 보임: {desc}')
        if len(ee) != 2:
            dangling += 1
            say('오류', f'배선 {e.get("identifier")}#{e.get("ID")} 한쪽 끝이 끊김: {desc}')
        if len(ee) == 2:
            (a, ca), (b, cb) = ee
            pa, pb = ca.get('name') in POWER, cb.get('name') in POWER
            special = any(t in (x.get('Tags') or '') for x in (a, b) for t in ('junctionbox', 'dock'))
            if pa and pb and not special and ca.tag == cb.tag:
                bad_power += 1
                say('오류', f'무효 전원 배선(같은 방향 핀끼리) {desc}')
            elif pa != pb:
                say('경고', f'전원 핀과 신호 핀을 이은 배선 {desc}')
    say('요약', f'배선 {n_w}개: 대각선 {diag}, 보임 {unhidden}, 끊김 {dangling}, 무효 전원 {bad_power}')

    # ---------------------------------------------------------------- 게이트
    wr = Wiring(sub, lambda s: None)
    n_g = 0
    for e in root:
        if e.tag != 'Item' or e.get('identifier') not in GATES:
            continue
        n_g += 1
        x, y = wr.pos(e)
        i, j = wr.cell(x, y)
        inside = 0 <= i < wr.W and 0 <= j < wr.H and wr.inner[j * wr.W + i]
        probs = []
        if e.get('HiddenInGame') != 'True':
            probs.append('게임에서 보임')
        if e.get('SpriteDepth') != '0.001':
            probs.append(f'깊이 {e.get("SpriteDepth")}(규칙 0.001)')
        if not inside:
            probs.append('대형 내벽 밖')
        if probs:
            say('규칙', f'게이트 {e.get("identifier")}#{e.get("ID")} {get_rect(e)}: {", ".join(probs)}')
    say('요약', f'게이트 {n_g}개 검사')

    # ---------------------------------------------------------------- 웨이포인트
    wp = {e.get('ID'): e for e in root if e.tag == 'WayPoint' and e.get('spawn') == 'Path'}
    adj = {k: set() for k in wp}
    for k, e in wp.items():
        for a, v in e.attrib.items():
            if a.startswith('linkedto') and v in wp:
                adj[k].add(v)
                adj[v].add(k)
    seen, comps = set(), 0
    for k in wp:
        if k in seen:
            continue
        comps += 1
        st = [k]
        while st:
            x = st.pop()
            if x not in seen:
                seen.add(x)
                st += adj[x]
    spawns = Counter((e.get('spawn'), e.get('job') or '') for e in root if e.tag == 'WayPoint' and e.get('spawn') != 'Path')
    say('요약', f'웨이포인트 {len(wp)}개, 연결 덩어리 {comps}개, 스폰 {dict(spawns)}')
    if comps > 1:
        say('경고', '웨이포인트가 여러 덩어리로 나뉨 - AI 이동 불가 구간 있음')

    # ---------------------------------------------------------------- 밸러스트/크기
    V = B = 0
    for _, (x0, x1, y0, y1), room in hulls:
        V += (x1 - x0) * (y1 - y0)
        if 'ballast' in (room or '').lower():
            B += (x1 - x0) * (y1 - y0)
    need = 0.07 / (B / V) if B else 0
    nbl = [(e.get('identifier'), e.get('ID'), e.find('Steering').get('NeutralBallastLevel'))
           for e in root if e.tag == 'Item' and e.find('Steering') is not None]
    say('요약', f'밸러스트 {B / V * 100:.2f}% → 필요한 중립 수위 {need:.3f}, 단말기 설정 {nbl}')
    dims = root.get('dimensions', '0,0').split(',')
    w, h = float(dims[0]) / 100, float(dims[1]) / 100
    if w > 80 or h > 32:
        say('경고', f'저장된 크기 {w:.1f}×{h:.1f}m: 에디터 TooLargeForEndGame 경고(80×32m 초과)')
    else:
        say('요약', f'저장된 크기 {w:.1f}×{h:.1f}m (80×32m 이내)')

    # ---------------------------------------------------------------- 전원 미연결
    unp = Counter()
    for e in root:
        if e.tag != 'Item' or e.get('HiddenInGame') == 'True' or e.get('NonInteractable') == 'True':
            continue
        if 'junctionbox' in (e.get('Tags') or ''):
            continue
        p = e.find('ConnectionPanel')
        if p is None:
            continue
        ps = [c for c in p if c.tag == 'input' and c.get('name') in ('power_in', 'power')]
        if ps and not any(c.findall('link') for c in ps):
            unp[e.get('identifier')] += 1
    if unp:
        say('참고', '전원 입력 미연결: ' + ', '.join(f'{k} {v}' for k, v in unp.most_common()))
    print('\n'.join(out))


if __name__ == '__main__':
    main(sys.argv[1])
