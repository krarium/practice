"""히페리온 골격(.sub) 생성 스크립트.

좌표는 잠수함 좌하단을 (0,0)으로 한 y-up 픽셀 단위(100px = 1m)로 정의한 뒤,
중심이 원점이 되도록 옮겨서 Barotrauma rect(좌상단 x, 좌상단 y, 폭, 높이)로 저장한다.
"""
import gzip
import os
import random

W, H = 7000, 2256            # 70.0m x 22.56m
CX, CY = W // 2, H // 2
SHELL = 96                   # 외벽 두께
IN = 48                      # 대형 내벽 두께
NEUTRAL = 0.07               # SubmarineBody.NeutralBallastPercentage
NEUTRAL_LEVEL = 0.5          # Steering.NeutralBallastLevel 기본값

_id = [0]
def nid():
    _id[0] += 1
    return _id[0]

def rect(x0, x1, y0, y1):
    return f"{x0 - CX},{y1 - CY},{x1 - x0},{y1 - y0}"

structures, hulls = [], []

def shell_h(x0, x1, y0):
    structures.append(f'  <Structure name="외벽 A 0도" identifier="shella0deg" ID="{nid()}" rect="{rect(x0, x1, y0, y0 + SHELL)}" '
                      f'SpriteColor="90,80,75,255" Scale="1" Rotation="0" SpriteDepth="0.101" />')

def shell_v(x0, y0, y1):
    structures.append(f'  <Structure name="외벽 A 90도" identifier="shella90deg" ID="{nid()}" rect="{rect(x0, x0 + SHELL, y0, y1)}" '
                      f'SpriteColor="90,80,75,255" Scale="1" Rotation="0" SpriteDepth="0.101" />')

def wall_h(x0, x1, y0):
    structures.append(f'  <Structure name="대형 내벽 수평" identifier="ff_x_wall" ID="{nid()}" rect="{rect(x0, x1, y0, y0 + IN)}" '
                      f'SpriteColor="220,180,165,255" Scale="0.5" Rotation="0" SpriteDepth="0.101" />')

def wall_v(x0, y0, y1):
    structures.append(f'  <Structure name="대형 내벽 수직" identifier="ff_y_wall" ID="{nid()}" rect="{rect(x0, x0 + IN, y0, y1)}" '
                      f'SpriteColor="220,180,165,255" Scale="0.5" Rotation="0" SpriteDepth="0.102" />')

hull_list = []
def hull(x0, x1, y0, y1, room="", wet=False, ballast=False):
    hull_list.append(((x1 - x0) * (y1 - y0), ballast, room, (x0, x1, y0, y1)))
    vol = (x1 - x0) * (y1 - y0)
    hulls.append(f'  <Hull ID="{nid()}" rect="{rect(x0, x1, y0, y1)}" water="0" backgroundsections="" RoomName="{room}" '
                 f'AmbientLight="50,100,200,20" Oxygen="{vol}" IsWetRoom="{wet}" AvoidStaying="{wet}" '
                 f'DisallowedUpgrades="" SpriteDepth="0.001" Scale="1" HiddenInGame="False" />')

# ---------------- 수직 레이아웃 (y, 아래→위) ----------------
LOWER_TOP = 752          # 하층부(밸러스트층) 천장 내벽: 752~800
MID_SPLIT = 400          # 하층부 좌/우/중앙 방 가로 구분 내벽: 400~448
NOTCH_Y = 352            # 하부 오목부 바닥 외벽: 352~448
D3 = (800, 1104)
D2 = (1152, 1456)
D1 = (1504, 1808)
TOWER = (1856, 2160)

# ---------------- 수평 레이아웃 (x) ----------------
MAIN_R = 6304            # 본체 우측 외벽 바깥면
TOWER_R = 1920           # 상부 탑 우측 외벽 바깥면
NOTCH_L, NOTCH_R = 2592, 3920   # 하부 오목부 (외벽 바깥 기준)
TANK = 416               # 밸러스트 탱크 1칸 내부 폭
BL0 = NOTCH_L - 3 * TANK - 2 * IN          # 좌측 밸러스트 시작 (탱크 3개)
BR1 = NOTCH_R + 2 * TANK + IN              # 우측 밸러스트 끝 (탱크 2개)

# ---------------- 외벽 ----------------
shell_v(0, 0, H)                                   # 좌측
shell_h(0, TOWER_R, H - SHELL)                     # 탑 상단
shell_v(TOWER_R - SHELL, D1[1], H)                 # 탑 우측
shell_h(TOWER_R - SHELL, MAIN_R, D1[1])            # 본체 상단
shell_v(MAIN_R - SHELL, D2[1], D1[1] + SHELL)      # 본체 우측 상부
shell_v(MAIN_R - SHELL, 0, D3[0])                  # 본체 우측 하부
shell_h(MAIN_R - SHELL, W, D2[1])                  # 선수 상단
shell_h(MAIN_R - SHELL, W, D3[0] - SHELL)          # 선수 하단
shell_v(W - SHELL, D3[0] - SHELL, D2[1] + SHELL)   # 선수 끝
shell_h(0, NOTCH_L + SHELL, 0)                     # 하단 좌측
shell_h(NOTCH_R - SHELL, MAIN_R, 0)                # 하단 우측
shell_v(NOTCH_L, 0, NOTCH_Y + SHELL)               # 오목부 좌측
shell_v(NOTCH_R - SHELL, 0, NOTCH_Y + SHELL)       # 오목부 우측
shell_h(NOTCH_L, NOTCH_R, NOTCH_Y)                 # 오목부 바닥

# ---------------- 내벽 ----------------
wall_h(SHELL, TOWER_R - SHELL, D1[1])              # 탑 바닥
wall_h(SHELL, MAIN_R - SHELL, D2[1])               # 1층/2층 사이
wall_h(SHELL, W - SHELL, D3[1])                    # 2층/3층 사이 (선수까지)
wall_h(SHELL, MAIN_R - SHELL, LOWER_TOP)           # 3층/하층부 사이
wall_h(SHELL, BL0 - IN, MID_SPLIT)                 # 좌측 하층부 2단 구분
wall_h(BR1 + IN, MAIN_R - SHELL, MID_SPLIT)        # 우측 하층부 2단 구분
wall_v(BL0 - IN, SHELL, LOWER_TOP)                 # 좌측 밸러스트 좌벽
wall_v(BL0 + TANK, SHELL, LOWER_TOP)               # 밸러스트 1|2
wall_v(BL0 + 2 * TANK + IN, SHELL, LOWER_TOP)      # 밸러스트 2|3
wall_v(NOTCH_L, NOTCH_Y + SHELL, LOWER_TOP)        # 밸러스트 3 우벽(오목부 위)
wall_v(NOTCH_R - IN, NOTCH_Y + SHELL, LOWER_TOP)   # 밸러스트 4 좌벽(오목부 위)
wall_v(NOTCH_R + TANK, SHELL, LOWER_TOP)           # 밸러스트 4|5
wall_v(BR1, SHELL, LOWER_TOP)                      # 우측 밸러스트 우벽

# ---------------- 헐 ----------------
hull(SHELL, TOWER_R - SHELL, *TOWER)
hull(SHELL, MAIN_R - SHELL, *D1)
hull(SHELL, W - SHELL, *D2)
hull(SHELL, W - SHELL, *D3)
hull(SHELL, BL0 - IN, SHELL, MID_SPLIT)
hull(SHELL, BL0 - IN, MID_SPLIT + IN, LOWER_TOP)
for i in range(3):
    x0 = BL0 + i * (TANK + IN)
    hull(x0, x0 + TANK, SHELL, LOWER_TOP, "roomname.ballast", True, True)
hull(NOTCH_L + IN, NOTCH_R - IN, NOTCH_Y + SHELL, LOWER_TOP)
for i in range(2):
    x0 = NOTCH_R + i * (TANK + IN)
    hull(x0, x0 + TANK, SHELL, LOWER_TOP, "roomname.ballast", True, True)
hull(BR1 + IN, MAIN_R - SHELL, SHELL, MID_SPLIT)
hull(BR1 + IN, MAIN_R - SHELL, MID_SPLIT + IN, LOWER_TOP)

total = sum(v for v, *_ in hull_list)
ballast = sum(v for v, b, *_ in hull_list if b)
ratio = ballast / total
optimal = NEUTRAL * total / ballast

desc = "임시 골격. 외벽/내벽/헐만 배치됨."
xml = (f'<?xml version="1.0" encoding="utf-8"?>\n'
       f'<Submarine description="{desc}" checkval="{random.randint(1, 2**31 - 1)}" price="30000" tier="3" '
       f'initialsuppliesspawned="false" noitems="false" lowfuel="false" type="Player" ismanuallyoutfitted="false" '
       f'class="Undefined" tags="0" outposttags="" triggeroutpostmissionevents="" gameversion="1.13.4.0" '
       f'dimensions="{W},{H}" cargocapacity="0" recommendedcrewsizemin="4" recommendedcrewsizemax="8" '
       f'recommendedcrewexperience="CrewExperienceMid" requiredcontentpackages="Vanilla" name="히페리온">\n'
       + "\n".join(structures + hulls) + "\n</Submarine>\n")

out_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(out_dir, "히페리온.sub"), "wb") as f:
    f.write(gzip.compress(xml.encode("utf-8")))
with open(os.path.join(out_dir, "히페리온.xml"), "w", encoding="utf-8") as f:
    f.write(xml)

print(f"size {W/100}m x {H/100}m, structures {len(structures)}, hulls {len(hulls)}")
print(f"total hull volume {total}, ballast {ballast}, ratio {ratio:.4f}, optimal ballast level {optimal:.4f}")
