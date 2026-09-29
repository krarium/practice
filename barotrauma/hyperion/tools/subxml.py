"""Barotrauma .sub XML 편집용 헬퍼.

좌표 규칙: rect="x,y,w,h" 에서 (x,y)는 좌상단, y축은 위쪽이 +.
여기서는 (x0, x1, y0, y1) = (왼쪽, 오른쪽, 아래, 위) 로 다룬다.
"""
import copy
import gzip
import json
import os
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))


def load_sub(path):
    raw = open(path, 'rb').read()
    try:
        raw = gzip.decompress(raw)
    except OSError:
        pass
    return ET.fromstring(raw.decode('utf-8'))


def save_sub(root, path, xml_path=None):
    ET.indent(root, space='  ')
    text = '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding='unicode') + '\n'
    with open(path, 'wb') as f:
        f.write(gzip.compress(text.encode('utf-8')))
    if xml_path:
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(text)


def get_rect(el):
    x, y, w, h = (int(round(float(v))) for v in el.get('rect').split(','))
    return x, x + w, y - h, y


def set_rect(el, x0, x1, y0, y1):
    el.set('rect', f'{int(x0)},{int(y1)},{int(x1 - x0)},{int(y1 - y0)}')


class Sub:
    def __init__(self, root):
        self.root = root
        ids = [int(e.get('ID')) for e in root if e.get('ID') and e.get('ID').isdigit()]
        self._next = max(ids) + 1
        self.templates = json.load(open(os.path.join(HERE, 'vanilla_templates.json'), encoding='utf-8'))

    # ---------------------------------------------------------------- basics
    def new_id(self):
        i = self._next
        self._next += 1
        return str(i)

    def by_id(self, i):
        for e in self.root:
            if e.get('ID') == str(i):
                return e
        raise KeyError(i)

    def remove(self, el):
        self.root.remove(el)

    def elements(self, tag=None, ident=None):
        for e in self.root:
            if tag and e.tag != tag:
                continue
            if ident and e.get('identifier') != ident:
                continue
            yield e

    def clone(self, el, x0, x1, y0, y1, **attrs):
        n = copy.deepcopy(el)
        n.set('ID', self.new_id())
        set_rect(n, x0, x1, y0, y1)
        for k, v in attrs.items():
            if v is None:
                n.attrib.pop(k, None)
            else:
                n.set(k, str(v))
        self.root.append(n)
        return n

    # ------------------------------------------------------------ structures
    def structure(self, ident, x0, y1, w=None, h=None, depth=None, fx=False, fy=False,
                  scale=None, color=None, tex_scale=None, tex_offset=None, rotation=None):
        """바닐라 템플릿으로 구조물 생성. (x0, y1) = 좌상단. 크기 고정 구조물은 템플릿 크기 사용."""
        t = self.templates['structures'][ident]
        a = dict(t['attrs'])
        if scale is not None:
            ratio = scale / float(a.get('Scale', 1))
            a['Scale'] = str(scale)
        else:
            ratio = 1.0
        ww = w if (w is not None and t['resW']) else int(round(t['w'] * ratio))
        hh = h if (h is not None and t['resH']) else int(round(t['h'] * ratio))
        el = ET.SubElement(self.root, 'Structure')
        el.set('name', a.pop('name', ''))
        el.set('identifier', ident)
        el.set('ID', self.new_id())
        el.set('rect', f'{int(x0)},{int(y1)},{int(ww)},{int(hh)}')
        if fx:
            el.set('flippedx', 'true')
        if fy:
            el.set('flippedy', 'true')
        a.pop('identifier', None)
        for k, v in a.items():
            el.set(k, v)
        if depth is not None:
            el.set('SpriteDepth', f'{depth:.3f}')
        if color is not None:
            el.set('SpriteColor', color)
        if tex_scale is not None:
            el.set('TextureScale', tex_scale)
        if tex_offset is not None:
            el.set('TextureOffset', tex_offset)
        if rotation is not None:
            el.set('Rotation', str(rotation))
        el.set('HiddenInGame', 'False')
        return el

    def template_size(self, kind, ident, scale=None):
        t = self.templates[kind][ident]
        ratio = 1.0 if scale is None else scale / float(t['attrs'].get('Scale', 1))
        return int(round(t['w'] * ratio)), int(round(t['h'] * ratio))

    def deco_item(self, ident, x0, y1, depth=None, fx=False, scale=None, color=None):
        """배경용 아이템: 상호작용 없음 + 손상되지 않음."""
        t = self.templates['items'][ident]
        a = dict(t['attrs'])
        ratio = 1.0 if scale is None else scale / float(a.get('Scale', 1))
        if scale is not None:
            a['Scale'] = str(scale)
        ww, hh = int(round(t['w'] * ratio)), int(round(t['h'] * ratio))
        el = ET.SubElement(self.root, 'Item')
        el.set('name', '')
        el.set('identifier', ident)
        el.set('ID', self.new_id())
        el.set('markedfordeconstruction', 'false')
        if fx:
            el.set('flippedx', 'true')
        el.set('rect', f'{int(x0)},{int(y1)},{ww},{hh}')
        keep = ('Rotation', 'Scale', 'SpriteColor', 'SpriteDepth', 'DisallowedUpgrades')
        for k in keep:
            if k in a:
                el.set(k, a[k])
        el.set('Tags', '')   # 침대(bunk) 등 AI가 찾아가는 태그 제거
        el.set('NonInteractable', 'True')
        el.set('NonPlayerTeamInteractable', 'True')
        el.set('InvulnerableToDamage', 'True')
        el.set('AllowSwapping', 'False')
        el.set('HiddenInGame', 'False')
        if depth is not None:
            el.set('SpriteDepth', f'{depth:.3f}')
        if color is not None:
            el.set('SpriteColor', color)
        return el

    # ----------------------------------------------------------------- hulls
    def hull(self, x0, x1, y0, y1, room, wet):
        el = ET.SubElement(self.root, 'Hull')
        el.set('ID', self.new_id())
        set_rect(el, x0, x1, y0, y1)
        el.set('water', '0')
        el.set('backgroundsections', '')
        el.set('RoomName', room)
        el.set('AmbientLight', '50,100,200,20')
        el.set('Oxygen', str((x1 - x0) * (y1 - y0)))
        el.set('IsWetRoom', 'True' if wet else 'False')
        el.set('AvoidStaying', 'True' if wet else 'False')
        el.set('DisallowedUpgrades', '')
        el.set('SpriteDepth', '0.001')
        el.set('Scale', '1')
        el.set('HiddenInGame', 'False')
        return el

    def gap(self, x0, x1, y0, y1, horizontal):
        """horizontal=True: 좌우로 흐르는 갭(문/세로 개구부), False: 상하(해치)."""
        el = ET.SubElement(self.root, 'Gap')
        el.set('ID', self.new_id())
        el.set('horizontal', 'true' if horizontal else 'false')
        el.set('HiddenInGame', 'false')
        el.set('Layer', '')
        set_rect(el, x0, x1, y0, y1)
        return el
