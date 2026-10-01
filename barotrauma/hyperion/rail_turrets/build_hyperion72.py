from pathlib import Path
import sys, copy, json, math, gzip, re, xml.etree.ElementTree as ET
BASE=Path(__file__).resolve().parent
TOOLS=BASE/'inspect/히페리온_작업파일/hyperion/tools'
sys.path.insert(0,str(TOOLS))
from subxml import Sub, load_sub, save_sub, get_rect, set_rect
from wiring import Wiring
import waypoints
OUT=BASE/'deliverables/Hyperion_RailTurrets'
OUT.mkdir(parents=True,exist_ok=True)
src=BASE/'inspect/히페리온_작업파일/hyperion/input/히페리온 - 베이스 6 (사용자 수정).sub'
root=load_sub(src); sub=Sub(root)
kain=ET.parse(BASE/'inspect/xml/CA-1N_templates.xml').getroot()
kt={}
for e in kain.iter('Item'): kt.setdefault(e.get('identifier'),e)
logs=[]; manifest={'input':src.name,'rails':[],'changes':[]}
def log(s): logs.append(s); print(s,flush=True)
def clean(e):
    e=copy.deepcopy(e); e.attrib.pop('linked',None); e.attrib.pop('Layer',None)
    for c in e.findall('ConnectionPanel/*'):
        for l in c.findall('link'): c.remove(l)
    for c in e.findall('ItemContainer'): c.set('contained',','.join('' for _ in c.get('contained','').split(',')))
    return e
def delete(i):
    e=sub.by_id(i)
    for n in root:
        for c in n.findall('ConnectionPanel/*'):
            for l in list(c):
                if l.tag=='link' and l.get('w')==str(i): c.remove(l)
    root.remove(e)
def clone(t,x,y,**attrs):
    e=clean(t); e.set('ID',sub.new_id())
    a,b,c,d=get_rect(e); w,h=b-a,d-c
    set_rect(e,int(x-w/2),int(x+w/2),int(y-h/2),int(y+h/2))
    e.attrib.update({k:str(v) for k,v in attrs.items()});root.append(e);return e

# Remove only the accidentally imported NDRST control circuit and its wires.
for i in [3137,3138,3139,3140,3141,3049,3050,3051,3052]: delete(i)
sub.by_id(1139).set('RoomName','D층 엔진실')
# Match the existing F deck engine-room background within the D deck room.
delete(1329);delete(1330)
for i in range(1682,1692):
    t=sub.by_id(i);a,b,c,d=get_rect(t);q=clone(t,(a+b)/2,(c+d)/2+512)
sub.by_id(1673).set('RoomName','상부 이동포탑 격납고')
# Lower hangar ladder: 24 px to the right (still inside its ceiling hatch 368..496 and backdrop 406..470).
lad=sub.by_id(972);a,b,c,d=get_rect(lad);set_rect(lad,a+24,b+24,c,d)
# Room lighting at Orca's level: Orca's ceiling lamps use range 300..600 (avg ~420),
# alpha 80..130 and cast shadows. Hyperion's tubes were range 700, alpha 255, no shadows.
n_light=0
for e in root:
    if e.tag!='Item':continue
    for lc in e.findall('LightComponent'):
        col=lc.get('LightColor','').split(',')
        if e.get('identifier')=='lightfluorescentl01':
            lc.set('Range','420');lc.set('LightColor',','.join(col[:3]+['115']));lc.set('CastShadows','True');n_light+=1
        elif e.get('identifier')=='lightcomponent90' and len(col)==4 and int(col[3])>130:
            lc.set('LightColor',','.join(col[:3]+['120']));n_light+=1
manifest['lights_dimmed']=n_light
sub.by_id(1673).set('IsWetRoom','True')
sub.by_id(1164).set('RoomName','하부 이동포탑 격납고')
nav=sub.by_id(899);nav.set('Tags','light,navterminal,sonar_observer');nav.set('AllowSwapping','False')
# No steering output is connected on the D deck observer terminal.
for c in nav.findall('ConnectionPanel/output'):
    if c.get('name','').startswith('velocity_'):
        assert not c.findall('link')
for i in [861,867]:
    e=sub.by_id(i);e.set('identifier','isc_combatperiscope');e.set('Tags','combatperiscope');e.set('AllowSwapping','False')
    for key in 'wasd': ET.SubElement(e.find('ConnectionPanel'),'output',name=f'key_{key}_out')

# Two leaves form a 256 px opening; the original hull bounds remain unchanged.
def opening(wall_id,x0,x1,cy,label):
    wall=sub.by_id(wall_id);a,b,c,d=get_rect(wall)
    assert a<x0<x1<b
    set_rect(wall,a,x0,c,d)
    q=copy.deepcopy(wall);q.set('ID',sub.new_id());set_rect(q,x1,b,c,d);root.append(q)
    result=[]
    for x in (x0+64,x0+192):
        h=clone(sub.by_id(41),x,cy,Tags='weldable,door,'+label,AllowSwapping='False')
        h.find('Door').set('ToggleWhenClicked','False');h.find('Door').set('ToggleCoolDown','0.1')
        g=sub.gap(x-64,x+64,int(cy-24),int(cy+24),False);h.set('linked',g.get('ID'));result.append(h)
    # Match the user's cap treatment at each shell end without adding collision.
    cap0=sub.by_id(1092)
    for x in (x0-20,x1):
        cap=clone(cap0,x+10,cy,DisableCollision='True')
    return result
upper_hatches=opening(1676,-780,-524,713,'상부포탑격납고해치')
lower_hatches=opening(1107,420,676,-952,'하부포탑격납고해치')
wr=Wiring(sub,log)
# The un-hulled bottom dock has isolated hatch frames. Use the connected hull
# wiring network for device approach stubs instead of snapping to an isolated frame.
seen=set();groups=[]
for cell,v in enumerate(wr.route):
    if not v or cell in seen:continue
    group=set([cell]);stack=[cell];seen.add(cell)
    while stack:
        q=stack.pop();i,j=q%wr.W,q//wr.W
        for ii,jj in [(i-1,j),(i+1,j),(i,j-1),(i,j+1)]:
            n=jj*wr.W+ii
            if 0<=ii<wr.W and 0<=jj<wr.H and wr.route[n] and n not in seen:seen.add(n);group.add(n);stack.append(n)
    groups.append(group)
network=max(groups,key=len)
for i,v in enumerate(wr.route):
    if v and i not in network:wr.route[i]=0;wr.inner[i]=0
# Rail ends now reach beyond the hull ends (outside the wiring grid). Their
# approach stub then runs orthogonally (horizontal, then vertical) to the
# nearest routable wall cell instead of a straight line.
_stub=wr.stub
def _stub_far(x,y):
    try:return _stub(x,y)
    except RuntimeError:
        best=None
        for j in range(wr.H):
            for i in range(wr.W):
                if wr.route[j*wr.W+i]:
                    cx,cy=wr.center(i,j);dd=abs(cx-x)+abs(cy-y)
                    if best is None or dd<best[0]:best=(dd,i,j)
        _,i,j=best;cx,cy=wr.center(i,j)
        return (i,j),[(x,y),(cx,y),(cx,cy)]
wr.stub=_stub_far
for e in root:
    if e.tag=='Item' and e.get('identifier','') in wr.tmpl:
        x,y=wr.pos(e);i,j=wr.cell(x,y)
        wr.gate_cells.update((i+k,j) for k in (-1,0,1))
for k in ['subtractcomponent','addercomponent','greatercomponent','equalscomponent','multiplycomponent','dividecomponent','oscillator','wificomponent']:
    if k in kt:wr.tmpl[k]=clean(kt[k])
if 'addercomponent' not in wr.tmpl:
    t=clean(kt['subtractcomponent']);t.set('identifier','addercomponent');t[0].tag='AdderComponent';wr.tmpl['addercomponent']=t
for k in list(wr.tmpl):wr.tmpl[k]=clean(wr.tmpl[k])
# Pathfinding is the same wall grid as the inherited wiring tools; cache repeated routes.
pathcache={}; oldpath=wr.path_nodes
def cached(a,b):
    key=(a,b)
    if key not in pathcache:pathcache[key]=oldpath(a,b)
    return pathcache[key]
wr.path_nodes=cached
def gate(ident,near,**kw):
    e=wr.gate(ident,near,**kw);e.set('InvulnerableToDamage','True');e.set('AllowSwapping','False');e.set('Tags',e.get('Tags','')+',hyperion_rail_control')
    return e
def rawconnect(a,pa,b,pb,color='bluewire',existing=None):
    wr.items.update({e.get('ID'):e for e in root if e.tag=='Item'})
    return wr.connect(a,pa,b,pb,color,existing)
fanout={}
def connect(a,pa,b,pb,color='bluewire'):
    if isinstance(a,str):a=wr.items[a]
    if isinstance(b,str):b=wr.items[b]
    key=(a.get('ID'),pa)
    candidates=fanout.setdefault(key,[(a,pa)])
    for n,p in candidates:
        if len(wr._pin(n,p).findall('link'))<4:
            return rawconnect(n,p,b,pb,color)
    n,p=candidates[-1]
    buf=gate('relaycomponent',wr.pos(n),IsOn='True',MaxPower='100000')
    rawconnect(n,p,buf,'signal_in1' if color!='redwire' else 'power_in',color)
    out='signal_out1' if color!='redwire' else 'power_out';candidates.append((buf,out))
    return rawconnect(buf,out,b,pb,color)
class Circuit:
    def __init__(self,near):self.near=near
    def g(self,t,**kw):return gate(t,self.near,**kw)
    def const(self,n):return self.g('memorycomponent',Value=str(n),Writeable='False')
    def wire(self,s,e,p):connect(s[0],s[1],e,p)
    def source(self,e,p='signal_out'):return (e,p)
    def check(self,s,value,out='1',false='0'):
        e=self.g('signalcheckcomponent',TargetSignal=str(value),Output=str(out),FalseOutput=str(false));self.wire(s,e,'signal_in');return (e,'signal_out')
    def unary(self,t,s,**kw):
        e=self.g(t,**kw);self.wire(s,e,'signal_in');return(e,'signal_out')
    def binary(self,t,a,b,**kw):
        e=self.g(t,**kw)
        for p,s in [('signal_in1',a),('signal_in2',b)]:
            if isinstance(s,(int,float)):s=(self.const(s),'signal_out')
            self.wire(s,e,p)
        return(e,'signal_out')
    def AND(self,*s):
        q=s[0]
        for v in s[1:]:q=self.binary('andcomponent',q,v,Output='1',FalseOutput='0',TimeFrame='0.1')
        return q
    def OR(self,*s):
        q=s[0]
        for v in s[1:]:q=self.binary('orcomponent',q,v,Output='1',FalseOutput='0',TimeFrame='0.1')
        return q
    def NOT(self,s):return self.unary('notcomponent',s,ContinuousOutput='False')
    def delay(self,s,t):return self.unary('delaycomponent',s,Delay=str(t),ResetWhenSignalReceived='False',ResetWhenDifferentSignalReceived='True')
    def wifi(self,ch):return self.g('wificomponent',Channel=str(ch),Range='20000',AllowCrossTeamCommunication='False',LinkToChat='False')
    def select(self,value,enabled,collector):
        r=self.g('relaycomponent',IsOn='False');self.wire(enabled,r,'set_state');self.wire(value,r,'signal_in1');connect(r,'signal_out1',collector,'signal_in1');return r

global_c=Circuit((-1050,440))
command=global_c.g('relaycomponent',IsOn='False')
deploy=(command,'state_out'); recall=global_c.NOT(deploy)
# NOT's private signalReceived flag and Delay's queue are not serialized. This
# creates a fresh boot window on every load, avoiding saved rail indices trying
# to drive a shuttle which the linked-sub loader has respawned at its home port.
startup_clock=global_c.delay((global_c.const(1),'signal_out'),0.75)
startup=global_c.unary('notcomponent',startup_clock,ContinuousOutput='True')
global_c.wire(global_c.check(startup,1,0,''),command,'set_state')
power=global_c.binary('greatercomponent',(sub.by_id(69),'power_value_out'),50,Output='1',FalseOutput='0',TimeFrame='0.2')
blackout=global_c.check(global_c.delay(global_c.NOT(power),1.0),1,0,'')
global_c.wire(blackout,command,'set_state')
main=sub.by_id(897);ci=main.find('CustomInterface');labels=ci.get('Labels').split(',');labels[0]='이동포탑 전개 / 수납';ci.set('Labels',','.join(labels))
button_gate=global_c.g('relaycomponent',IsOn='False')
connect(main,'signal_out1',button_gate,'signal_in1');connect(button_gate,'signal_out1',command,'toggle')
manifest['command_id']=command.get('ID')

# Parent loading stations: real, visible and interactable, with no moving loader copies.
loaders={}
for name,locs in [('upper',[(-360,565),(-245,565)]),('lower',[(325,-810),(790,-810)])]:
    a=clone(kt['coilgunloader'],*locs[0],NonInteractable='False',HiddenInGame='False',SpriteColor='255,255,255,255',InvulnerableToDamage='False',AllowSwapping='False',Tags=f'coilgunloader,{name}_rail_loader')
    b=clone(kt['railgunloadersinglevertical'],*locs[1],NonInteractable='False',HiddenInGame='False',SpriteColor='255,255,255,255',InvulnerableToDamage='False',AllowSwapping='False',Tags=f'railgunloader,{name}_rail_loader')
    loaders[name]=[a.get('ID'),b.get('ID')]

# Hidden main ports use the same vanilla docking prefab and forced direction as Kain.
port_template=clean(next(e for e in kain if e.get('ID')=='675'))
all_ports=[];home_ports=[];home_states=[]
# 7.2 rail geometry. Points are turret centres = carriage port = parent anchor
# (the rail prefabs set DockedDistance 0, so docked ports coincide).
# Left end: beyond every exterior part so the upper turret can fire straight down.
# Right end: right of the old tail fin A (x 3554) and tail fin E P1 (x 3612).
# The upper slope starts right of the A deck tail fin F3 (x -1355) instead of on the A deck corner.
RAIL_XL,RAIL_XR=-4020,3660
UP_TOP,UP_FLAT,LO_Y=1156,900,-1120
SLOPE_X0,SLOPE_X1=-1300,-1000
def seg(x0,y0,x1,y1,step=76):
    n=max(1,math.ceil(math.hypot(x1-x0,y1-y0)/step))
    return [(round(x0+(x1-x0)*k/n),round(y0+(y1-y0)*k/n)) for k in range(1,n+1)]
def rail_points(upper):
    if upper:
        pts=[(RAIL_XL,UP_TOP)]+seg(RAIL_XL,UP_TOP,SLOPE_X0,UP_TOP)+seg(SLOPE_X0,UP_TOP,SLOPE_X1,UP_FLAT)+seg(SLOPE_X1,UP_FLAT,RAIL_XR,UP_FLAT)
        home=(-652,580)
    else:
        pts=[(RAIL_XL,LO_Y)]+seg(RAIL_XL,LO_Y,RAIL_XR,LO_Y);home=(548,-800)
    # The hangar branch leaves from an exact rail point.
    if home[0] not in [p[0] for p in pts]:
        y=next(p[1] for p in pts if p[0]>home[0]);pts=sorted(pts+[(home[0],y)])
    junction=next(i for i,p in enumerate(pts) if p[0]==home[0]);N=len(pts)-1
    y0=pts[junction][1];dy=home[1]-y0;K=math.ceil(abs(dy)/24)
    branch=[(home[0],round(y0+dy*j/K)) for j in range(1,K+1)]
    return pts+branch,junction,N,len(pts)+K-1

for railno,name in enumerate(['upper','lower']):
    upper=name=='upper';points,H,N,HOME=rail_points(upper);near=(-650,440) if upper else (550,-580)
    C=Circuit(near);channel=7200+railno*20
    actual=C.g('memorycomponent',Value=str(HOME),Writeable='True');target=C.g('memorycomponent',Value=str(HOME),Writeable='True')
    startup_home=C.check(startup,1,HOME,'')
    C.wire(startup_home,actual,'signal_in');C.wire(startup_home,target,'signal_in')
    cur=(actual,'signal_out');req=(target,'signal_out')
    fb=C.wifi(channel+1);connect(fb,'signal_out',actual,'signal_in')
    tx=C.wifi(channel);C.wire(req,tx,'signal_in')
    locked=C.wifi(channel+2)
    equal=C.binary('equalscomponent',cur,req,Output='1',FalseOutput='0',TimeFrame='0.2')
    stable=C.AND(equal,(locked,'signal_out'))
    ready=C.AND(stable,C.delay(stable,0.25))
    onbranch=C.binary('greatercomponent',cur,N,Output='1',FalseOutput='0',TimeFrame='0.2');onrail=C.NOT(onbranch)
    athome=C.check(cur,HOME);atjunction=C.check(cur,H);atfirst=C.check(cur,N+1)
    home_states.append(athome)
    # Open during transit only; a returning vehicle first reaches its external junction.
    transit=C.OR(C.AND(onbranch,C.OR(C.NOT(athome),deploy)),C.AND(recall,atjunction))
    hatches=upper_hatches if upper else lower_hatches
    for h in hatches:C.wire(transit,h,'set_state')
    closed=C.AND(*[(h,'state_out') for h in hatches]);closed=C.NOT(C.OR(*[(h,'state_out') for h in hatches]))
    open_live=C.AND(*[(h,'state_out') for h in hatches])
    open_delayed=C.delay(open_live,0.65)
    # A transit request must see the full opening delay, even if the previous state was closed.
    transit_ok=C.OR(C.NOT(transit),C.AND(transit,open_delayed))
    ready=C.AND(ready,transit_ok)
    operable=C.AND(deploy,onrail,closed)
    control=C.g('relaycomponent',IsOn='False');C.wire(operable,control,'set_state')
    kill=C.g('relaycomponent',IsOn='False');C.wire(deploy,kill,'set_state')
    periscope=sub.by_id(867 if upper else 861)
    for i,p in enumerate(['position_out','trigger_out','key_w_out','key_a_out','key_d_out'],1):
        connect(periscope,p,kill,f'signal_in{i}');connect(kill,f'signal_out{i}',control,f'signal_in{i}')
    for i in [1,2,3]:
        w=C.wifi(channel+2+i);connect(control,f'signal_out{i}',w,'signal_in')
    # Two always-on collectors keep every pin at five or fewer connections.
    collectors=[C.g('relaycomponent',IsOn='True') for _ in range(2)]
    for c in collectors:connect(c,'signal_out1',target,'signal_in')
    branch_guard=C.g('relaycomponent',IsOn='False')
    delayed_open_filter=C.g('relaycomponent',IsOn='False');C.wire(open_live,delayed_open_filter,'set_state');C.wire(open_delayed,delayed_open_filter,'signal_in1')
    connect(delayed_open_filter,'signal_out1',branch_guard,'set_state')
    # Clear the opening permit as soon as the hatch command closes. A previous
    # cycle's delayed 1 must never authorize the next opening cycle.
    C.wire(C.check(open_live,0,0,''),branch_guard,'set_state')
    connect(branch_guard,'signal_out1',collectors[1],'signal_in1')
    add=lambda a,b,lo=-999,hi=999:C.binary('addercomponent',a,b,ClampMin=str(lo),ClampMax=str(hi),TimeFrame='0.2')
    minus=lambda a,b,lo=-999,hi=999:C.binary('subtractcomponent',a,b,ClampMin=str(lo),ClampMax=str(hi),TimeFrame='0.2')
    # Deploy follows the inward branch backwards, then stops at the rail junction.
    C.select(minus(cur,1),C.AND(ready,deploy,onbranch,C.NOT(atfirst)),branch_guard)
    C.select((C.const(H),'signal_out'),C.AND(ready,deploy,atfirst),branch_guard)
    # Recall first walks the exterior rail towards the junction, then enters the hangar.
    sign=minus(H,cur,-1,1)
    C.select(add(cur,sign),C.AND(ready,recall,onrail,C.NOT(atjunction)),collectors[0])
    C.select((C.const(N+1),'signal_out'),C.AND(ready,recall,atjunction),branch_guard)
    C.select(add(cur,1,0,HOME),C.AND(ready,recall,onbranch,C.NOT(athome)),branch_guard)
    direction=minus((control,'signal_out5'),(control,'signal_out4'),-1,1)
    moving=C.NOT(C.check(direction,0))
    manual_guard=C.g('relaycomponent',IsOn='False');C.wire(deploy,manual_guard,'set_state');connect(manual_guard,'signal_out1',collectors[1],'signal_in1')
    C.select(add(cur,direction,0,N),C.AND(ready,operable,moving),manual_guard)
    ports=[]
    for i,(x,y) in enumerate(points):
        # RailPorts.xml sets DockedDistance 0: the docked carriage sits exactly on this anchor.
        p=clone(port_template,x,y,Scale='0.55',NonInteractable='True',HiddenInGame='True',InvulnerableToDamage='True',SpriteColor='255,255,255,0',Tags=f'dock,hyperion_rail_{name}_{i}',AllowSwapping='False')
        p.find('DockingPort').set('ApplyEffectsOnDocking','False');p.find('DockingPort').set('ForceDockingDirection','Left')
        wr.items[p.get('ID')]=p
        local=Circuit((max(-3200,min(3200,x)),max(-850,min(680,y))))
        rx=local.wifi(channel);chosen=local.check((rx,'signal_out'),i)
        local.wire(chosen,p,'set_state')
        encoder=local.check((p,'state_out'),1,i,'');emit=local.wifi(channel+1);local.wire(encoder,emit,'signal_in')
        ports.append(p)
    all_ports+=ports;home_ports.append(ports[HOME])
    # Electrical bus runs through all rail ports; power connectors on ports are bidirectional.
    for a,b in zip(ports,ports[1:]):rawconnect(a,'power',b,'power','redwire')
    manifest['rails'].append(dict(name=name,points=points,junction=H,rail_end=N,home=HOME,ports=[p.get('ID') for p in ports],actual=actual.get('ID'),target=target.get('ID'),hatches=[h.get('ID') for h in hatches],periscope=periscope.get('ID'),loaders=loaders[name],channel=channel,control=control.get('ID')))
    log(f'{name}: rail {N+1} ports, hangar branch {HOME-N} ports, control constructed')

both_home=global_c.AND(*home_states)
allow_button=global_c.AND(power,global_c.OR(deploy,both_home),global_c.NOT(startup));global_c.wire(allow_button,button_gate,'set_state')

# Kain's child visuals are retained, while all inherited weapon-selection and loader items are removed.
# IDs are intentionally disjoint from the parent: the native parent remapper resolves cross-sub loader links.
def build_child(rail,idx):
    old=ET.parse(BASE/'inspect/xml/Turret Shuttle hatch system SL.xml').getroot()
    cr=ET.Element('Submarine',dict(old.attrib));cr.set('name',f'Hyperion {rail["name"]} rail turret')
    cr.set('description','히페리온 전용 이동포탑. 장전기는 본함에 있습니다.');cr.attrib.pop('previewimage',None)
    cr.set('gameversion',root.get('gameversion'));cr.set('requiredcontentpackages','Vanilla')
    placeholder=ET.SubElement(cr,'Hull',ID='1');cs=Sub(cr);cr.remove(placeholder);cs._next=20000+idx*5000
    def ce(e,x=None,y=None,**attrs):
        q=clean(e);q.set('ID',cs.new_id());q.attrib.update({k:str(v) for k,v in attrs.items()});cr.append(q)
        if x is not None:
            a,b,c,d=get_rect(q);set_rect(q,x-(b-a)//2,x+(b-a)//2,y-(d-c)//2,y+(d-c)//2)
        return q
    upper=idx==0
    # Local frame: turret centre = carriage port = (0,0). Kain's art keeps its
    # placement around the turret; the upper (deck-mounted) turret is mirrored.
    ka,kb,kc,kd=get_rect(next(e for e in old if e.get('identifier')=='doublecoilgun'));TX,TY=(ka+kb)/2,(kc+kd)/2
    for e in old:
        if e.tag=='Structure':
            q=ce(e,Indestructible='True',NoAITarget='True',DisableCollision='True')
            a,b,c,d=get_rect(q);a,b,c,d=a-TX,b-TX,c-TY,d-TY
            if upper:
                c,d=-d,-c
                flag='flippedx' if round(float(q.get('Rotation','0') or 0))%180==90 else 'flippedy'
                if q.get(flag)=='true':q.attrib.pop(flag)
                else:q.set(flag,'true')
            set_rect(q,a,b,c,d)
    # The only collision fixture of a submarine body is its hull. Keep it far
    # outboard (above the upper turret, below the lower one) so it never
    # overlaps Hyperion's hulls, walls or doors at any rail or hangar position.
    # It also leaves no hull next to the carriage port, so docking creates no
    # extra docking hulls or blocker bodies inside the hangar (ladder fix).
    HULL_Y=400 if upper else -300
    hull=cs.hull(-8,8,HULL_Y-8,HULL_Y+8,'이동포탑 본체',False)
    dock=ce(next(e for e in old if e.get('ID')=='1'),0,0,InvulnerableToDamage='True',AllowSwapping='False',HiddenInGame='True',NonInteractable='True',Tags='dock,hyperion_turret_dock')
    dock.find('DockingPort').set('ForceDockingDirection','Right');dock.find('DockingPort').set('ApplyEffectsOnDocking','False')
    gun=ce(next(e for e in old if e.get('identifier')=='doublecoilgun'),InvulnerableToDamage='True',AllowSwapping='False',NonInteractable='True',Tags='turret,hyperion_doublecoilgun')
    railgun=ce(next(e for e in old if e.get('identifier')=='railgun'),InvulnerableToDamage='True',AllowSwapping='False',NonInteractable='True',Tags='turret,hyperion_railgun')
    for g in [gun,railgun]:
        a,b,c,d=get_rect(g);w,h=b-a,d-c;set_rect(g,-w//2,w-w//2,-h//2,h-h//2)
    for g,l in zip([gun,railgun],rail['loaders']):g.set('linked',l)
    for g in [gun,railgun]:
        g.attrib.pop('flippedx',None);g.attrib.pop('flippedy',None)
        turret=g.find('Turret')
        # BaseRotation is applied over the item rotation on load: deck-mounted (0) upper, hanging (180) lower.
        g.set('Rotation','0' if upper else '180');turret.set('BaseRotation','0' if upper else '180')
        # Both turrets receive the same target angle; 0..360 is a full circle.
        turret.set('RotationLimits','0,360');turret.set('AutoOperate','False')
    battery=ce(next(e for e in old if e.get('identifier')=='shuttlebattery'),-24,0,InvulnerableToDamage='True',HiddenInGame='True',NonInteractable='True')
    bc=battery.find('PowerContainer');bc.set('Capacity','5000');bc.set('Charge','5000');bc.set('MaxOutPut','2000');bc.set('MaxRechargeSpeed','1000');bc.set('RechargeSpeed','1000')
    sc=ce(next(e for e in old if e.get('identifier')=='supercapacitor'),24,0,InvulnerableToDamage='True',HiddenInGame='True',NonInteractable='True')
    sc.find('PowerContainer').set('RechargeSpeed','1000')
    # Child wiring and radio units fit inside a hidden, collision-free electronics backplate.
    back=cs.structure('ff_x_wall',-160,24,320,48,depth=.1);back.set('DisableCollision','True');back.set('Indestructible','True');back.set('HiddenInGame','True')
    items={e.get('ID'):e for e in cr if e.tag=='Item'}
    def cwire(a,pa,b,pb,color='bluewire'):
        w=clean(wr.wire_tmpl);w.set('ID',cs.new_id());w.set('identifier',color);w.set('HiddenInGame','True');w.set('SpriteDepth','0.001');w.set('InvulnerableToDamage','True');w.set('NonInteractable','True');w.set('AllowSwapping','False')
        w.set('SpriteColor','254,23,17,255' if color=='redwire' else '51,121,173,255')
        x,y=wr.pos(a);xx,yy=wr.pos(b);w.set('rect',f'{int(x)},{int(y)},42,16');w.find('Wire').set('nodes',f'{x:g};{y:g};{xx:g};{y:g};{xx:g};{yy:g}')
        for e,p,end in [(a,pa,0),(b,pb,1)]:ET.SubElement(next(c for c in e.find('ConnectionPanel') if c.get('name')==p),'link',w=w.get('ID'),i=str(end))
        cr.append(w)
    def radio(ch,x):
        q=ce(wr.tmpl['wificomponent'],x,0,HiddenInGame='True',SpriteDepth='0.001',InvulnerableToDamage='True',AllowSwapping='False')
        q.find('Holdable').set('Attached','True');q.find('WifiComponent').set('Channel',str(ch));q.find('WifiComponent').set('Range','20000');return q
    ch=rail['channel'];aim=radio(ch+3,-120);cofire=radio(ch+4,-80);rfire=radio(ch+5,80);lock=radio(ch+2,120)
    # The periscope focuses (camera + ammo HUD) on the last turret its aim signal
    # reaches. Wire the double coilgun last so it is the default view.
    for g in [railgun,gun]:cwire(aim,'signal_out',g,'position_in');cwire(sc,'power_out',g,'power_in','redwire')
    cwire(cofire,'signal_out',gun,'trigger_in');cwire(rfire,'signal_out',railgun,'trigger_in');cwire(dock,'state_out',lock,'signal_in')
    cwire(dock,'power',battery,'power_in','redwire');cwire(battery,'power_out',sc,'power_in','redwire')
    name=f'Hyperion_{rail["name"]}_turret.sub';save_sub(cr,OUT/name)
    linked=ET.SubElement(root,'LinkedSubmarine',name=cr.get('name'),filepath=f'LocalMods/Hyperion_RailTurrets/{name}',linkedto=rail['ports'][rail['home']],pos=f'{rail["points"][rail["home"]][0]},{rail["points"][rail["home"]][1]}')
    # Native LinkedSubmarine.Load allocates its own ID; Save retains its XML.
    # An explicit ID here survives editor remapping and collides on Test Play.
    linked.set('originalmyport',dock.get('ID'))
    for k,v in cr.attrib.items():
        if k not in ['name']:linked.set(k,v)
    for e in cr:linked.append(copy.deepcopy(e))
    rail.update(child=name,child_guns=[gun.get('ID'),railgun.get('ID')],child_dock=dock.get('ID'),linked_name=linked.get('name'))
    return cr
children=[build_child(r,i) for i,r in enumerate(manifest['rails'])]

# Repair the inherited docking wires, keeping the docking terminal's fourth button.
rawconnect(sub.by_id(1554),'signal_out4',sub.by_id(2980),'toggle','greenwire',sub.by_id(1823))
ET.SubElement(wr._pin(sub.by_id(2980),'toggle'),'link',w='1823',i='1')
rawconnect(sub.by_id(2980),'state_out',sub.by_id(47),'set_state','greenwire',sub.by_id(1824))
ET.SubElement(wr._pin(sub.by_id(2980),'state_out'),'link',w='1824',i='0')
# Both live navigation stations control the additional D deck engine.
for i in [897,1554]:connect(sub.by_id(i),'velocity_x_out',sub.by_id(1332),'set_force')
# Reroute the imported diagonal research terminal cable.
rawconnect(sub.by_id(115),'power',sub.by_id(2090),'power_in','redwire',sub.by_id(2275))

# Automatic drainage keeps the two reloading rooms usable after a deployment cycle.
for near in [(-820,485),(310,-916)]:
    t=next(e for e in root if e.tag=='Item' and e.find('Pump') is not None)
    p=clone(t,*near,Scale='0.25',AllowSwapping='False',Tags='pump,hyperion_hangar_drain')
    x,y=near;set_rect(p,x-50,x+50,y-24,y+24)
    p.find('Pump').set('IsOn','True');p.find('Pump').set('FlowPercentage','-100');wr.items[p.get('ID')]=p

# All functional unpowered equipment gets a proper output -> input connection.
# Port power buses are also fed from the main grid. The user's example coilgun is left alone.
loads=[]
for e in root:
    if e.tag!='Item' or e.get('ID')=='3149' or e.get('NonInteractable')=='True' or e.get('HiddenInGame')=='True':continue
    for p in e.findall('ConnectionPanel/input'):
        if p.get('name') in ['power_in','power'] and not p.findall('link'):loads.append((e,p.get('name')))
loads += [(p,'power') for p in home_ports]
jbs=[e for e in root if e.tag=='Item' and e.get('identifier')=='junctionbox']
newpower=[]
def powerfeed(e,pin):
    x,y=wr.pos(e)
    candidates=[(n,'power') for n in jbs if len(wr._pin(n,'power').findall('link'))<5]+[(n,'power_out') for n in newpower if len(wr._pin(n,'power_out').findall('link'))<4]
    if not candidates:
        parent=min(newpower,key=lambda n:len(wr._pin(n,'power_out').findall('link')))
        q=gate('relaycomponent',(x,y),IsOn='True',MaxPower='20000',CanBeOverloaded='True');rawconnect(parent,'power_out',q,'power_in','redwire');newpower.append(q);candidates=[(q,'power_out')]
    parent,out=min(candidates,key=lambda v:sum(abs(a-b) for a,b in zip(wr.pos(v[0]),(x,y))))
    # Reserve the final junction-box socket for a distribution relay.
    if parent in jbs and len(wr._pin(parent,out).findall('link'))==4:
        q=gate('relaycomponent',(x,y),IsOn='True',MaxPower='20000',CanBeOverloaded='True');rawconnect(parent,out,q,'power_in','redwire');newpower.append(q);parent,out=q,'power_out'
    rawconnect(parent,out,e,pin,'redwire')
for e,p in loads:powerfeed(e,p)
log(f'Connected {len(loads)} previously unpowered devices / rail buses')
# Repairable decorative camera/searchlight retain the user's appearance and now have power.
spawns=[copy.deepcopy(e) for e in root if e.tag=='WayPoint' and e.get('spawn')!='Path']
waypoints.build(sub,log)
for e in spawns:e.set('ID',sub.new_id());root.append(e)
# Hull glitch: a thin sealed hull on the outer face of each hangar hatch. The
# hatch gaps then join two hulls (hangar <-> seal) instead of hangar <-> sea,
# so opening the hatch lets no water in. Added after the waypoint pass so the
# seal gets no navigation nodes.
glitch_hulls=[]
for hatches,outward,label in [(upper_hatches,1,'상부'),(lower_hatches,-1,'하부')]:
    rs=[get_rect(sub.by_id(h.get('linked'))) for h in hatches]
    x0,x1=min(r[0] for r in rs),max(r[1] for r in rs)
    if outward>0:y0=max(r[3] for r in rs);y1=y0+10
    else:y1=min(r[2] for r in rs);y0=y1-10
    gh=sub.hull(x0,x1,y0,y1,f'{label} 이동포탑 해치 차수막',False);gh.set('AvoidStaying','True')
    glitch_hulls.append(gh.get('ID'))
manifest['glitch_hulls']=glitch_hulls
# Update neutral ballast to account for the two tiny linked hulls.
V=sum((b-a)*(d-c) for e in root if e.tag=='Hull' for a,b,c,d in [get_rect(e)])+512
B=sum((b-a)*(d-c) for e in root if e.tag=='Hull' and 'ballast' in e.get('RoomName','').lower() for a,b,c,d in [get_rect(e)])
for e in root:
    if e.find('Steering') is not None:e.find('Steering').set('NeutralBallastLevel',f'{.07*V/B:.6f}')
# The counter counts components even when IsOn=False or alpha=0. Remove the
# two lamps from the actual rail prefab, rather than merely its saved instance.
prefabs=ET.Element('Items')
for suffix,direction in [('anchor','Left'),('carriage','Right')]:
    p=ET.SubElement(prefabs,'Item',identifier=f'hyperion_rail_{suffix}',variantof='dockingport',name=f'Hyperion rail {suffix}',tags='dock,hyperion_rail')
    ET.SubElement(ET.SubElement(p,'ClearAll'),'LightComponent')
    # None of these are instance-saveable in 1.13.4.0, so they live in the prefab.
    # DockedDistance 0: the locked carriage sits exactly on its anchor.
    # DistanceTolerance 256: every rail/hangar step is <= 80 px, so a carriage that
    # was knocked off during a step is still recaptured by the requested anchor.
    ET.SubElement(p,'DockingPort',forcedockingdirection=direction,applyeffectsondocking='false',
                  ishorizontal='true',distancetolerance='256,256',dockeddistance='0')
removed_lights=0
for r in [root]+children:
    for e in r:
        if e.tag=='Item' and e.get('identifier')=='dockingport' and 'hyperion_' in e.get('Tags',''):
            e.set('identifier','hyperion_rail_anchor' if r is root else 'hyperion_rail_carriage')
            for light in e.findall('LightComponent'):e.remove(light);removed_lights+=1
ET.indent(prefabs);ET.ElementTree(prefabs).write(OUT/'RailPorts.xml',encoding='utf-8',xml_declaration=True)

# Canonical dense parent IDs prevent the editor's ID compaction from invalidating
# the parent-loader references retained inside an unloaded linked-sub XML body.
idmap={old:str(i+1) for i,old in enumerate(sorted((e.get('ID') for e in root if e.get('ID')),key=int))}
def refs(value):return re.sub(r'\d+',lambda m:idmap.get(m.group(),m.group()),value)
for e in root:
    if e.tag=='LinkedSubmarine':
        for key in ['linkedto','originallinkedto']:
            if key in e.attrib:e.set(key,refs(e.get(key)))
        continue
    if e.get('ID'):e.set('ID',idmap[e.get('ID')])
    for n in e.iter():
        for key in list(n.attrib):
            if key in ['linked','contained','ladders','gap'] or key.startswith('linkedto') or (n.tag=='link' and key=='w'):
                n.set(key,refs(n.get(key)))
for r,rail in zip(children,manifest['rails']):
    embedded=next(e for e in root if e.tag=='LinkedSubmarine' and e.get('name')==rail['linked_name'])
    for gunid in rail['child_guns']:
        gun=next(e for e in r if e.get('ID')==gunid);gun.set('linked',idmap[gun.get('linked')])
    for e in list(embedded):embedded.remove(e)
    for e in r:embedded.append(copy.deepcopy(e))
    save_sub(r,OUT/rail['child'])
    for key in ['ports','hatches','loaders']:rail[key]=[idmap[i] for i in rail[key]]
    for key in ['actual','target','periscope','control']:rail[key]=idmap[rail[key]]
manifest['command_id']=idmap[manifest['command_id']]
manifest['parent_id_map']=idmap
manifest['lighting']={'editor_before':572,'editor_after':sum(len(e.findall('LightComponent')) for e in root),'removed_main':384,'removed_including_children':removed_lights,'room_lights_preserved':True}
log(f'Rail lamps removed: {removed_lights} including children; editor light components: {manifest["lighting"]["editor_after"]}')
root.set('name','히페리온 - 베이스 7.2');root.set('description','이동포탑 2기: C층 좌측 잠망경=하부, 우측=상부. A/D 이동, 마우스 이중 코일건(기본 화면), W 레일건. 함장실 메인단말기 첫 버튼으로 전개/수납. 장전은 본함 격납고에서 합니다. 7.2: 레일 이탈 수정, 레일 연장, 해치 차수막, 조명 조정.')
for old_name in ['히페리온 - 베이스 7.sub','히페리온 - 베이스 7.1.sub']:(OUT/old_name).unlink(missing_ok=True)
save_sub(root,OUT/'히페리온 - 베이스 7.2.sub')
filelist=ET.Element('contentpackage',name='Hyperion Rail Turrets',corepackage='false',gameversion=root.get('gameversion','1.13.4.0'),modversion='0.1.2')
ET.SubElement(filelist,'Item',file='%ModDir%/RailPorts.xml')
for name in ['히페리온 - 베이스 7.2.sub']+[r['child'] for r in manifest['rails']]:ET.SubElement(filelist,'Submarine',file='%ModDir%/'+name)
ET.indent(filelist);ET.ElementTree(filelist).write(OUT/'filelist.xml',encoding='utf-8',xml_declaration=True)
manifest.update(power_connections=len(loads),neutral_ballast=.07*V/B,parent_max_id=len(idmap))
(BASE/'deliverables/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
(BASE/'deliverables/build.log').write_text('\n'.join(logs))
log('Saved base 7 and both embedded / standalone rail turrets')
