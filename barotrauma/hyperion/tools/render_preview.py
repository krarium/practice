"""구조 미리보기 PNG. 사용법:
  python3 tools/render_preview.py <파일.sub> <출력.png> [배율=0.3] [x0,x1,y0,y1]

그리는 것: 헐(파랑=건조, 분홍=젖는 방, ID+RoomName), 외벽(검정), 대형 내벽(갈색), 플랫폼(회색),
갭(초록 테두리), 문/해치(파랑), 사다리(초록 테두리), 주요 설비(보라 테두리+이름), 256 단위 격자.
배선은 그리지 않음(배선 확인은 render_wires 옵션: 네 번째 인자 뒤에 wires).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from subxml import load_sub, get_rect  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

FONT = '/usr/share/fonts/truetype/nanum/NanumGothicCodingBold.ttf'
DEVICES = ('pump', 'dockingport', 'dockinghatch', 'battery', 'junctionbox', 'statusmonitor', 'deconstructor',
           'fabricator', 'artifactholder', 'largeengine', 'outpostreactor', 'outpostoxygenerator', 'lever', 'button')
WIRE_COL = {'redwire': '#e11', 'bluewire': '#25a', 'greenwire': '#1a6', 'orangewire': '#f80', 'wire': '#666'}


def main():
    src, out = sys.argv[1], sys.argv[2]
    S = float(sys.argv[3]) if len(sys.argv) > 3 else 0.3
    root = load_sub(src)
    if len(sys.argv) > 4 and sys.argv[4] != 'wires':
        X0, X1, Y0, Y1 = [float(v) for v in sys.argv[4].split(',')]
    else:
        rs = [get_rect(e) for e in root if e.tag in ('Structure', 'Hull') and e.get('rect')]
        X0, X1 = min(r[0] for r in rs) - 100, max(r[1] for r in rs) + 100
        Y0, Y1 = min(r[2] for r in rs) - 100, max(r[3] for r in rs) + 100
    wires = 'wires' in sys.argv[4:]
    W, H = int((X1 - X0) * S) + 20, int((Y1 - Y0) * S) + 20
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)
    font = ImageFont.truetype(FONT, max(10, int(30 * S)))
    small = ImageFont.truetype(FONT, max(8, int(18 * S)))

    def P(x, y):
        return 10 + (x - X0) * S, 10 + (Y1 - y) * S

    def box(r, **k):
        x0, x1, y0, y1 = r
        a, b = P(x0, y1)
        c, e = P(x1, y0)
        d.rectangle([a, b, c, e], **k)

    for gx in range(int(X0) // 256 * 256, int(X1), 256):
        d.line([P(gx, Y0), P(gx, Y1)], fill='#eee')
        d.text(P(gx, Y0 + 40), str(gx), fill='#888', font=small)
    for gy in range(int(Y0) // 256 * 256, int(Y1), 256):
        d.line([P(X0, gy), P(X1, gy)], fill='#eee')
        d.text(P(X0, gy), str(gy), fill='#888', font=small)
    for e in root:
        if e.tag == 'Hull':
            box(get_rect(e), fill='#ffd6d6' if e.get('IsWetRoom') == 'True' else '#e6eeff', outline='#57a')
    for e in root:
        i = e.get('identifier', '')
        if e.tag != 'Structure' or float(e.get('SpriteDepth', '1')) > 0.3 and 'platform' not in i.lower():
            continue
        if i.startswith('shell'):
            box(get_rect(e), fill='#222')
        elif i in ('ff_x_wall', 'ff_y_wall'):
            box(get_rect(e), fill='#b07050')
        elif 'platform' in i.lower():
            box(get_rect(e), fill='#999')
    for e in root:
        i = e.get('identifier', '')
        if e.tag == 'Gap':
            box(get_rect(e), outline='#0c0', width=2)
        elif e.tag == 'Item' and e.get('rect'):
            if i == 'ladder':
                box(get_rect(e), outline='#0a0', width=2)
            elif 'door' in i or 'hatch' in i:
                box(get_rect(e), fill='#06f')
            elif i in DEVICES or 'terminal' in i or 'cabinet' in i:
                r = get_rect(e)
                box(r, outline='#c0c', width=2)
                d.text(P(r[0], r[3]), i[:12], fill='#909', font=small)
    if wires:
        for e in root:
            w = e.find('Wire') if e.tag == 'Item' else None
            if w is None or not w.get('nodes') or not e.get('identifier', '').endswith('wire'):
                continue
            v = [float(x) for x in w.get('nodes').split(';')]
            pts = [P(x, y) for x, y in zip(v[::2], v[1::2])]
            if len(pts) > 1:
                d.line(pts, fill=WIRE_COL.get(e.get('identifier'), '#000'), width=2)
    for e in root:
        if e.tag == 'Hull':
            x0, x1, y0, y1 = get_rect(e)
            d.text(P(x0 + 10, y1 - 10), e.get('ID') + ' ' + e.get('RoomName', '').replace('roomname.', ''),
                   fill='#036', font=font)
    im.save(out)
    print(out, im.size)


if __name__ == '__main__':
    main()
