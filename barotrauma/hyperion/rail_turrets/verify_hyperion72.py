"""Static checks plus a frame-based model of the saved native signal circuit.
This is not a replacement for running Barotrauma's physics/netcode.
"""
from pathlib import Path
import sys,json,copy,collections,math,xml.etree.ElementTree as E
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'inspect/히페리온_작업파일/hyperion/tools'))
from subxml import load_sub,get_rect
P=BASE/'deliverables/Hyperion_RailTurrets';M=json.loads((BASE/'deliverables/manifest.json').read_text())
root=load_sub(P/'히페리온 - 베이스 7.2.sub')
ALL=[root]+[e for e in root if e.tag=='LinkedSubmarine']
checks=[]
def check(cond,msg):
    assert cond,msg;checks.append(msg)
def static():
    ids=[e.get('ID') for r in ALL for e in r if e.get('ID')]
    check(len(ids)==len(set(ids)),'Global parent/child entity IDs are unique')
    parentids={e.get('ID') for e in root if e.get('ID')}
    for r in ALL:
        local={e.get('ID'):e for e in r if e.get('ID')}
        ends=collections.defaultdict(list)
        for e in r:
            for c in e.findall('ConnectionPanel/*'):
                ls=c.findall('link');check(len(ls)<=5,f'Pin limit {e.get("ID")}.{c.get("name")}')
                for l in ls:ends[l.get('w')].append((e,c,l.get('i')))
            for lid in e.get('linked','').split(','):
                if lid:check(lid in local or lid in parentids,f'Link target {e.get("ID")} -> {lid} exists')
        for wid,ee in ends.items():
            check(wid in local and local[wid].find('Wire') is not None,f'Wire {wid} exists')
            check(len(ee)==2 and {x[2] for x in ee}=={'0','1'},f'Wire {wid} has both ends')
        for e in r:
            if e.tag=='Item' and e.get('identifier','').endswith('wire'):
                check(e.get('ID') in ends,f'Wire {e.get("ID")} has connections')
                check(e.get('HiddenInGame')=='True',f'Wire {e.get("ID")} hidden')
                vals=[float(v) for v in e.find('Wire').get('nodes','').split(';') if v]
                pts=list(zip(vals[::2],vals[1::2]));check(all(a[0]==b[0] or a[1]==b[1] for a,b in zip(pts,pts[1:])),f'Wire {e.get("ID")} orthogonal')
    for rail in M['rails']:
        cr=load_sub(P/rail['child']);embedded=next(e for e in root if e.tag=='LinkedSubmarine' and e.get('name')==rail['linked_name'])
        def contents(r):
            children=copy.deepcopy(list(r))
            for e in children:
                for n in e.iter():n.text=None;n.tail=None
            return [E.tostring(e) for e in children]
        check(contents(cr)==contents(embedded),'Embedded and standalone child contents match')
        loc={e.get('ID'):e for e in cr if e.get('ID')}
        check(not any('loader' in e.get('identifier','') for e in cr),'No child loader duplicates')
        for gid,lid,ident in zip(rail['child_guns'],rail['loaders'],['doublecoilgun','railgun']):
            check(loc[gid].get('identifier')==ident and loc[gid].get('linked')==lid,'Child gun links to its own fixed parent loader')
            check(loc[gid].get('AllowSwapping')=='False' and loc[gid].get('InvulnerableToDamage')=='True','Weapon swapping disabled, damage disabled')
            check(lid not in loc and lid in parentids,'Native remap leaves loader unresolved locally, resolves in parent')
        check(all(e.get('InvulnerableToDamage')=='True' for e in cr if e.tag=='Item'),'All child items invulnerable')
        check(all(e.get('Indestructible')=='True' and e.get('DisableCollision')=='True' for e in cr if e.tag=='Structure'),'Child art is indestructible with collision disabled')
        points=rail['points'];H,N,HOME=rail['junction'],rail['rail_end'],rail['home']
        edges=[(i,i+1) for i in range(N)]+[(H,N+1)]+[(i,i+1) for i in range(N+1,HOME)]
        # 7.2 prefabs: DockedDistance 0 (carriage on its anchor), capture tolerance 256 x 256.
        for i,j in edges:
            dx=abs(points[j][0]-points[i][0]);dy=abs(points[j][1]-points[i][1])
            check(dx<=80 and dy<=80,f'Step within capture tolerance {rail["name"]} {i}<->{j}')
        check(all(points[i][0]<points[i+1][0] for i in range(N)),'A/D indexed rail is monotonically left/right')
        if rail['name']=='lower':check(len({p[1] for p in points[:N+1]})==1,'Lower exterior rail is straight')
        # Body footprint clears the exterior shell before the hatch closes.
        # Turret art (238 px wide) passes the 256 px hatch opening; body clearance is checked in check72_geometry.py.
        for i in range(N+1,HOME+1):check(-780+119<=points[i][0]<=-524-119 if rail['name']=='upper' else 420+119<=points[i][0]<=676-119,'Hangar transit turret fits the opening')
    old=load_sub(BASE/'inspect/히페리온_작업파일/hyperion/input/히페리온 - 베이스 6 (사용자 수정).sub')
    for id in ['3149','1124','1123','1126','2090','1325','1336']:
        a=next((e for e in old if e.get('ID')==id),None);b=next((e for e in root if e.get('ID')==M['parent_id_map'][id]),None)
        if a is not None and a.get('rect'):check(a.get('rect')==b.get('rect'),f'Protected placement {id} unchanged')

class Sim:
    dt=1/60
    def __init__(self,lock_seconds=.35):
        self.t=0.;self.lock_seconds=lock_seconds;self.grid=10000;self.keys={};self.events=[];self.fired=[];self.received={};self.angle={};self.transits=[]
        self.items={e.get('ID'):e for r in ALL for e in r if e.tag=='Item'}
        self.nodes={};self.order=[]
        for i,e in self.items.items():
            if 'hyperion_rail_control' in e.get('Tags',''):
                co=e[0];self.nodes[i]=dict(kind=co.tag,attrs=co.attrib.copy(),value=co.get('Value',''),on=co.get('IsOn','True')=='True',v=['',''],age=[100.,100.],queue=[],last=None);self.order.append(i)
            elif e.get('identifier')=='wificomponent' and int(e.find('WifiComponent').get('Channel'))>=7200:
                self.nodes[i]=dict(kind='WifiComponent',attrs=e.find('WifiComponent').attrib.copy())
        self.channels=collections.defaultdict(list)
        for i,n in self.nodes.items():
            if n['kind']=='WifiComponent':self.channels[int(n['attrs']['Channel'])].append(i)
        self.out=collections.defaultdict(list)
        for r in ALL:
            ee=collections.defaultdict(list)
            for e in r:
                for c in e.findall('ConnectionPanel/*'):
                    for l in c.findall('link'):ee[l.get('w')].append((e.get('ID'),c.get('name')))
            for wid,pairs in ee.items():
                if len(pairs)==2:
                    a,b=pairs;self.out[a].append(b);self.out[b].append(a)
        self.rails=[]
        for r in M['rails']:
            q=copy.deepcopy(r);q.update(physical=r['home'],docked=r['home'],arrival=None,leaves={i:0. for i in r['hatches']},request={i:False for i in r['hatches']},history=[r['home']]);self.rails.append(q)
        self.portmap={p:(r,i) for r in self.rails for i,p in enumerate(r['ports'])}
        self.hatchmap={h:r for r in self.rails for h in r['hatches']}
        self.gunmap={g:r for r in self.rails for g in r['child_guns']}
    def send(self,i,p,v,depth=0):
        if depth>100:raise AssertionError('Signal recursion')
        v=str(v)
        for j,q in self.out[(i,p)]:self.recv(j,q,v,depth+1)
    def recv(self,i,p,v,depth):
        self.received[(i,p)]=(self.t,v)
        if i in self.portmap and p=='set_state':
            r,j=self.portmap[i]
            if v=='0':
                if r['docked']==j:r['docked']=None;r['arrival']=None
            elif r['docked'] is None:
                old=r['physical'];a,b=r['points'][old],r['points'][j]
                if abs(a[0]-b[0])<=256 and abs(a[1]-b[1])<=256:
                    r['docked']=j;r['arrival']=self.t+self.lock_seconds
                    if old>r['rail_end'] or j>r['rail_end']:
                        assert all(r['leaves'][h]>.999 for h in r['hatches']),f'Closed hatch transit {r["name"]} {old}->{j}'
                        self.transits.append((r['name'],old,j,self.t))
        elif i in self.hatchmap and p=='set_state':self.hatchmap[i]['request'][i]=v!='0'
        elif i in self.gunmap and p=='trigger_in' and v!='0':self.fired.append((self.t,i))
        elif i in self.gunmap and p=='position_in':self.angle[i]=v
        n=self.nodes.get(i)
        if n is None:return
        k=n['kind'];a=n['attrs']
        if k=='WifiComponent' and p=='signal_in':
            for j in self.channels[int(a['Channel'])]:
                if j!=i:self.send(j,'signal_out',v,depth)
        elif k=='RelayComponent':
            if p=='set_state':n['on']=v!='0'
            elif p=='toggle' and v!='0':n['on']=not n['on']
            elif p.startswith('signal_in') and n['on']:self.send(i,p.replace('_in','_out'),v,depth)
        elif k=='MemoryComponent' and p=='signal_in' and a.get('Writeable','True')=='True':n['value']=v
        elif k=='SignalCheckComponent' and p=='signal_in':
            val=a.get('Output','1') if v==a.get('TargetSignal','0') else a.get('FalseOutput','0')
            if val!='':self.send(i,'signal_out',val,depth)
        elif k=='NotComponent' and p=='signal_in':n['signalReceived']=True;self.send(i,'signal_out','1' if v=='0' else '0',depth)
        elif k=='DelayComponent' and p=='signal_in':
            if a.get('ResetWhenDifferentSignalReceived')=='True' and n['queue'] and n['queue'][0][1]!=v:n['queue'].clear()
            n['queue'].append((self.t+float(a.get('Delay','1')),v))
        elif p in ['signal_in1','signal_in2'] and 'v' in n:
            j=int(p[-1])-1;n['v'][j]=v
            if k not in ['AndComponent','OrComponent','XorComponent'] or v!='0':n['age'][j]=0.
    def tick(self,n=1):
        for frame in range(n):
            self.t+=self.dt
            self.send(M['parent_id_map']['69'],'power_value_out',self.grid)
            for r in self.rails:
                if r['arrival'] is not None and self.t>=r['arrival']:
                    r['physical']=r['docked'];r['history'].append(r['physical']);r['arrival']=None
                for h in r['hatches']:
                    sign=1 if r['request'][h] else -1;r['leaves'][h]=max(0.,min(1.,r['leaves'][h]+sign*3*self.dt));self.send(h,'state_out',int(r['request'][h]))
                lock=r['docked'] is not None and r['arrival'] is None
                for j,p in enumerate(r['ports']):self.send(p,'state_out',int(lock and r['docked']==j))
                self.send(r['child_dock'],'state_out',int(lock))
                for p in ['key_a_out','key_d_out','key_w_out','trigger_out']:self.send(r['periscope'],p,self.keys.get((r['name'],p),0))
                self.send(r['periscope'],'position_out','1.2')
            for i in self.order:
                q=self.nodes[i];k=q['kind'];a=q['attrs']
                if k=='MemoryComponent':self.send(i,'signal_out',q['value'])
                elif k=='RelayComponent':self.send(i,'state_out',int(q['on']))
                elif k=='NotComponent' and a.get('ContinuousOutput')=='True':
                    if not q.get('signalReceived',False):self.send(i,'signal_out',1)
                    q['signalReceived']=False
                elif k=='DelayComponent':
                    while q['queue'] and q['queue'][0][0]<=self.t+self.dt/10:_,v=q['queue'].pop(0);self.send(i,'signal_out',v)
                elif k in ['AndComponent','OrComponent','XorComponent','EqualsComponent','GreaterComponent','AdderComponent','SubtractComponent','DivideComponent','MultiplyComponent']:
                    ages=q['age'];tf=float(a.get('TimeFrame','0'));recent=[v<=tf+self.dt/100 for v in ages]
                    if k in ['AndComponent','OrComponent','XorComponent']:
                        val=all(recent) if k=='AndComponent' else any(recent) if k=='OrComponent' else sum(recent)==1
                        self.send(i,'signal_out',a.get('Output','1') if val else a.get('FalseOutput','0'))
                    elif k in ['EqualsComponent','GreaterComponent'] and any(recent):
                        val=q['v'][0]==q['v'][1] if k=='EqualsComponent' else float(q['v'][0] or 0)>float(q['v'][1] or 0)
                        self.send(i,'signal_out',a.get('Output','1') if val else a.get('FalseOutput','0'))
                    elif all(recent):
                        aa,bb=[float(v or 0) for v in q['v']]
                        val=aa+bb if k=='AdderComponent' else aa-bb if k=='SubtractComponent' else aa*bb if k=='MultiplyComponent' else aa/bb if bb else 0
                        val=max(float(a.get('ClampMin','-999999')),min(float(a.get('ClampMax','999999')),val));self.send(i,'signal_out',f'{val:g}')
                    q['age']=[v+self.dt for v in q['age']]
    def until(self,fn,seconds=200):
        for _ in range(round(seconds/self.dt)):
            self.tick()
            if fn():return
        raise AssertionError(f'Timed out at {self.t:.2f}: '+str([(r['name'],r['physical'],r['docked'],self.nodes[r['target']]['value']) for r in self.rails]))
    def click(self):self.send(M['parent_id_map']['897'],'signal_out1','1')
    def active(self):return all(self.nodes[r['control']]['on'] for r in self.rails)
    def stowed(self):return all(r['physical']==r['home'] and r['arrival'] is None and max(r['leaves'].values())==0 for r in self.rails)

def scenarios(lock):
    s=Sim(lock);s.tick(180)
    check(s.stowed() and not s.active(),'Initial state stowed, controls disabled')
    for r in s.rails:
        for p in ['trigger_out','key_w_out','key_a_out','key_d_out']:s.keys[(r['name'],p)]=1
    s.tick(30);check(not s.fired,'Stowed mouse/W produce no fire')
    s.keys={};s.click();s.until(s.active,60)
    check(not s.fired,'Firing remains disabled during hangar deployment')
    check(all(r['physical']==r['junction'] for r in s.rails),'Deployment reaches both exterior junctions')
    s.until(lambda:all(max(r['leaves'].values())==0 for r in s.rails),5)
    for r in s.rails:s.keys[(r['name'],'trigger_out')]=1;s.keys[(r['name'],'key_w_out')]=1
    s.tick(30);check(set(i for t,i in s.fired)=={i for r in s.rails for i in r['child_guns']},'Mouse and W reach their respective guns')
    check(all(len({s.angle.get(i) for i in r['child_guns']})==1 for r in s.rails),'Both guns receive identical target angles')
    s.keys={}
    for r in s.rails:s.keys[(r['name'],'key_a_out')]=1
    s.until(lambda:all(r['physical']==0 for r in s.rails),200)
    s.tick(45);check(all(r['physical']==0 for r in s.rails),'Left endpoint is clamped')
    for r in s.rails:s.keys[(r['name'],'key_d_out')]=1
    s.tick(40);check(all(r['physical']==0 for r in s.rails),'A+D produces no motion')
    s.keys={}
    for r in s.rails:s.keys[(r['name'],'key_d_out')]=1
    s.until(lambda:all(r['physical']==r['rail_end'] for r in s.rails),240)
    s.tick(45);check(all(r['physical']==r['rail_end'] for r in s.rails),'Right endpoint is clamped')
    s.click();s.tick(20)
    check(not s.nodes[M['command_id']]['on'],'Recall command immediately switches shared deployment request off')
    start=s.t
    for r in s.rails:s.keys[(r['name'],'trigger_out')]=1;s.keys[(r['name'],'key_w_out')]=1
    s.tick(45);check(not any(t>start for t,i in s.fired),'Recall mouse/W are blocked')
    s.click();s.tick(15);check(not s.nodes[M['command_id']]['on'],'A click during recall cannot redeploy')
    s.until(s.stowed,240);check(not s.active(),'Remote recall completes and closes both hatches')
    s.keys={};s.click();s.until(s.active,60)
    for r in s.rails:s.keys[(r['name'],'key_a_out')]=1
    s.tick(180);s.grid=0;s.until(lambda:not s.nodes[M['command_id']]['on'],3)
    s.until(s.stowed,200);check(s.stowed(),'Power loss returns both turrets without power-dependent actuators')
    s.grid=10000;s.tick(180);check(s.stowed() and not s.nodes[M['command_id']]['on'],'Power restoration does not auto-deploy')
    # Mid-deployment cancellation.
    s.keys={};s.click();s.tick(120);s.click();s.until(s.stowed,100)
    check(s.stowed(),'Deploy cancellation returns to storage')
    restored=Sim(lock)
    restored.nodes[M['command_id']]['on']=True
    for r in restored.rails:
        restored.nodes[r['actual']]['value']='0';restored.nodes[r['target']]['value']='0';restored.nodes[r['control']]['on']=True
    restored.tick(180)
    check(restored.stowed() and not restored.active() and not restored.nodes[M['command_id']]['on'],'Load resets saved remote indices and deployment state to native home spawn')
    return dict(lock_model_seconds=lock,time_model_seconds=round(s.t,2),transit_steps=len(s.transits),all_passed=True)
if __name__=='__main__':
    static();print('Static assertions:',len(checks),flush=True)
    results=[scenarios(.35),scenarios(1.0)]
    report=dict(static_assertions=len(checks),scenarios=results,limitation='Saved circuit evaluated in a Python model based on native component sources. Barotrauma physics, camera selection, multiplayer and real ammo consumption are not executed.')
    (BASE/'deliverables/verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
