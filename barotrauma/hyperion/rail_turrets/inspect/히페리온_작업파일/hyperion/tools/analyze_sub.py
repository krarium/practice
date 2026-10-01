"""잠수함 분석 덤프. 사용법:
  python3 tools/analyze_sub.py <파일.sub> rooms     # 방(헐) 표: 층, 헐 ID, 이름, 숨김 라벨, 좌표, 크기, 주요 설비
  python3 tools/analyze_sub.py <파일.sub> circuits  # 주요 설비/게이트의 연결 목록 (ID 는 파일마다 달라짐)
  python3 tools/analyze_sub.py <파일.sub> labels    # 모든 라벨 (숨김 여부 포함)
"""
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from subxml import load_sub, get_rect  # noqa: E402

DECKS = [('A', 713, 968), ('B', 457, 713), ('C', 200, 457), ('D', -56, 200), ('E', -312, -56), ('F', -568, -312),
         ('G', -960, -568)]
FUNC = {'isc_militarynavterminal': '군용항법단말기', 'navterminal': '항법단말기', 'statusmonitor': '상태모니터',
        'outpostreactor': '원자로', 'battery': '배터리', 'deconstructor': '분해기', 'fabricator': '제작기',
        'medicalfabricator': '의료제작기', 'isc_hugesteelcabinet': '초대형캐비닛', 'outpostoxygenerator': '산소발생기',
        'pump': '펌프', 'largeengine': '대형엔진', 'junctionbox': '정션박스', 'supercapacitor': '슈퍼커패시터',
        'op_researchterminal': '유전자연구단말기', 'artifactholder': '유물보관함', 'periscope': '잠망경',
        'suppliescabinet': '보급함', 'steelcabinet': '강철캐비닛', 'medcabinet': '의료캐비닛',
        'divingsuitlocker': '잠수복보관함', 'oxygentankshelf2': '산소통선반', 'lever': '레버', 'button': '버튼',
        'coilgun': '코일건', 'dockingport': '도킹포트', 'dockinghatch': '도킹해치', 'weaponholder': '무기거치대',
        'mediumsteelcabinet': '중형캐비닛', 'extinguisherbracket': '소화기거치대', 'op_vendingmachine1': '자판기'}
KEY = tuple(FUNC) + ('door', 'hatch', 'doorwbuttons', 'hatchwbuttons', 'windoweddoor')


def deck(y0, y1):
    out = [d for d, a, b in DECKS if a < y1 - 10 and b > y0 + 10]
    return '?' if not out else (out[0] if len(out) == 1 else out[0] + '~' + out[-1])


def main(path, mode):
    root = load_sub(path)
    hulls = sorted([e for e in root if e.tag == 'Hull'], key=lambda h: (-get_rect(h)[3], get_rect(h)[0]))

    def room_of(e):
        a, b, c, d = get_rect(e)
        x, y = (a + b) / 2, (c + d) / 2
        for h in hulls:
            x0, x1, y0, y1 = get_rect(h)
            if x0 <= x <= x1 and y0 <= y <= y1:
                return h
        return None

    labels = [e for e in root if e.get('identifier') == 'label' and e.find('ItemLabel') is not None]
    if mode == 'labels':
        for e in labels:
            h = room_of(e)
            print(f'{e.get("ID")} 숨김={e.get("HiddenInGame")} {get_rect(e)} [{h.get("RoomName") if h is not None else "헐 밖"}] '
                  f'{e.find("ItemLabel").get("Text")!r}')
        return
    if mode == 'rooms':
        items = defaultdict(Counter)
        for e in root:
            if e.tag != 'Item' or not e.get('rect') or e.get('HiddenInGame') == 'True':
                continue
            i = e.get('identifier')
            if i not in FUNC:
                continue
            h = room_of(e)
            if h is None:
                continue
            name = '쓰레기통튜브' if i == 'mediumsteelcabinet' and e.get('linked') else FUNC[i]
            if e.get('NonInteractable') == 'True':
                name += '(소품)'
            items[h.get('ID')][name] += 1
        print('| 층 | 헐 ID | RoomName | 숨김 라벨 | x 범위 | y 범위 | 크기(m) | 젖는방 | 주요 설비 |')
        print('|---|---|---|---|---|---|---|---|---|')
        for h in hulls:
            x0, x1, y0, y1 = get_rect(h)
            labs = [e.find('ItemLabel').get('Text') for e in labels if e.get('HiddenInGame') == 'True'
                    and room_of(e) is h and e.find('ItemLabel').get('Text')]
            it = ', '.join(f'{k}×{v}' if v > 1 else k for k, v in items[h.get('ID')].most_common())
            print(f'| {deck(y0, y1)} | {h.get("ID")} | {h.get("RoomName")} | {" / ".join(labs)} | {x0}~{x1} | '
                  f'{y0}~{y1} | {(x1 - x0) / 100:.2f}×{(y1 - y0) / 100:.2f} | '
                  f'{"예" if h.get("IsWetRoom") == "True" else ""} | {it} |')
        return
    ends = defaultdict(list)
    for e in root:
        p = e.find('ConnectionPanel') if e.tag == 'Item' else None
        if p is None:
            continue
        for c in p:
            for l in c.findall('link'):
                ends[l.get('w')].append((e, c.get('name')))

    def conns(e):
        out = []
        p = e.find('ConnectionPanel')
        if p is None:
            return out
        for c in p:
            for l in c.findall('link'):
                o = [f'{x.get("identifier")}#{x.get("ID")}.{n}' for x, n in ends[l.get('w')] if x is not e]
                out.append(f'{c.get("name")} -> {", ".join(o) if o else "(끊김)"}')
        return out

    for e in root:
        i = e.get('identifier', '')
        if e.tag != 'Item' or e.find('Wire') is not None:
            continue
        gate = i.endswith('component')
        if not gate and i not in KEY:
            continue
        cs = conns(e)
        if i in ('door', 'hatch', 'doorwbuttons', 'hatchwbuttons', 'windoweddoor') and not cs:
            continue
        h = room_of(e)
        extra = ''
        if gate and len(e):
            extra = ' ' + str({k: v for k, v in e[0].attrib.items()
                               if k in ('IsOn', 'TargetSignal', 'Output', 'FalseOutput', 'MaxPower', 'Channel', 'Delay')})
        print(f'{i}#{e.get("ID")} {get_rect(e)} [{h.get("RoomName") if h is not None else "헐 밖"}] '
              f'tags={e.get("Tags")} linked={e.get("linked")}{extra}')
        for c in cs:
            print('    ', c)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'rooms')
