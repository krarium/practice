"""Regression for the native editor load -> SaveToXElement -> Test Play path.

Mirrors IdRemap's sorted compaction and LinkedSubmarine.Load/Save's retained XML.
The game itself is not launched. Original failure fixture is optional.
"""
from pathlib import Path
import copy,collections,json,sys,xml.etree.ElementTree as E
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'inspect/히페리온_작업파일/hyperion/tools'))
from subxml import load_sub
P=BASE/'deliverables/Hyperion_RailTurrets'

def editor_save_ids(root):
    source=sorted(int(e.get('ID')) for e in root if e.get('ID'))
    assert len(source)==len(set(source))
    remap={old:i+1 for i,old in enumerate(source)}
    saved=[]
    for e in root:
        if e.tag=='LinkedSubmarine':
            # Load: AssignMaxId; Save: retained saveElement, no ID setter.
            if e.get('ID'):saved.append(int(e.get('ID')))
        elif e.get('ID'):saved.append(remap[int(e.get('ID'))])
    return sorted(i for i,n in collections.Counter(saved).items() if n>1),remap

def verify():
    r=load_sub(P/'히페리온 - 베이스 7.2.sub')
    fixture=Path('/tmp/hyperion7_crash_repro.sub')
    old_dupes=[]
    if fixture.exists():
        old_dupes,_=editor_save_ids(load_sub(fixture))
        assert old_dupes==[5604,5605],old_dupes
    duplicates,remap=editor_save_ids(r)
    assert duplicates==[]
    assert all(old==new for old,new in remap.items()),'Parent IDs must be stable across the editor save'
    linked=[e for e in r if e.tag=='LinkedSubmarine']
    assert len(linked)==2 and all('ID' not in e.attrib for e in linked)
    parent={int(e.get('ID')):e for e in r if e.get('ID')}
    loader_links=0
    for child in linked:
        assert int(child.get('linkedto')) in parent
        assert int(child.get('originalmyport')) in {int(e.get('ID')) for e in child if e.get('ID')}
        own={int(e.get('ID')) for e in child if e.get('ID')}
        for gun in child:
            if gun.get('identifier') not in ['doublecoilgun','railgun']:continue
            lid=int(gun.get('linked'));assert lid not in own
            for offset in [1,301,7000]:
                game_remap={old:new+offset-1 for old,new in remap.items()}
                loaded_parent={game_remap[old]:e for old,e in parent.items()}
                loader=loaded_parent[game_remap[lid]]
                assert loader.get('identifier')==('coilgunloader' if gun.get('identifier')=='doublecoilgun' else 'railgunloadersinglevertical')
            loader_links+=1
    # Simulate repeated editor save/load: dense parent and ID-less wrappers stay stable.
    for _ in range(3):
        d,m=editor_save_ids(r);assert not d and all(k==v for k,v in m.items())
    pf=E.parse(P/'RailPorts.xml').getroot()
    variants={e.get('identifier'):e for e in pf}
    for ident,direction in [('hyperion_rail_anchor','Left'),('hyperion_rail_carriage','Right')]:
        v=variants[ident]
        assert v.get('variantof')=='dockingport'
        assert v.find('ClearAll/LightComponent') is not None
        assert v.find('DockingPort').get('forcedockingdirection')==direction
        assert v.find('DockingPort').get('applyeffectsondocking')=='false'
        # Native CreateVariantXML removes ALL matching base components.
        for scope in [r]+linked:
            for item in scope:
                if item.get('identifier')==ident:assert not item.findall('LightComponent') and item.find('DockingPort') is not None and item.find('PowerTransfer') is not None
    main_ports=[e for e in r if e.get('identifier')=='hyperion_rail_anchor']
    M=json.loads((BASE/'deliverables/manifest.json').read_text())
    assert len(main_ports)==sum(len(x['ports']) for x in M['rails'])
    original=load_sub(BASE/'inspect/히페리온_작업파일/hyperion/input/히페리온 - 베이스 6 (사용자 수정).sub')
    before=[E.tostring(e.find('LightComponent')) for e in original if e.get('identifier') in ['lightfluorescentl01','lightfluorescentm02']]
    after=[E.tostring(e.find('LightComponent')) for e in r if e.get('identifier') in ['lightfluorescentl01','lightfluorescentm02']]
    # 7.2: ceiling tubes dimmed to Orca level (range 420, alpha 115, shadows); nothing added or removed.
    assert len(before)==len(after)
    for e in r:
        if e.get('identifier')=='lightfluorescentl01':
            l=e.find('LightComponent');assert l.get('Range')=='420' and l.get('LightColor').endswith(',115') and l.get('CastShadows')=='True'
    count=sum(len(e.findall('LightComponent')) for e in r)
    assert count==188
    filelist=E.parse(P/'filelist.xml').getroot()
    assert filelist.find('Item').get('file')=='%ModDir%/RailPorts.xml'
    for e in filelist:assert (P/e.get('file').replace('%ModDir%/','')).exists()
    result=dict(old_editor_save_duplicate_ids=old_dupes,new_editor_save_duplicate_ids=duplicates,editor_save_cycles=3,parent_loader_links=loader_links,game_id_offsets=[1,301,7000],editor_light_components=count,hidden_rail_ports=len(main_ports),room_lighting='ceiling tubes range 420 / alpha 115 / shadows',limitations='Source-based editor serialization and prefab checks; game executable and physics not run.')
    (BASE/'deliverables/roundtrip_check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return result

if __name__=='__main__':verify()
