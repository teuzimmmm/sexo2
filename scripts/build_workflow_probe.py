"""Real source checks with a synthetic draft; never connects to or writes to LCU."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from lolalytics import Client
from lolalytics.transport import HTTPTransport
from sexo2.services.builds import BuildService


class SyntheticDraft:
    def __init__(self):
        self.finalization=False

    def get(self,path,**kwargs):
        data={
            '/lol-gameflow/v1/gameflow-phase':'ChampSelect',
            '/lol-gameflow/v1/session':{'gameData':{'gameId':1,'gameMode':'CLASSIC','mapId':11,'queue':{'id':420}}},
            '/lol-champ-select/v1/session':{'localPlayerCellId':0,'myTeam':[{'cellId':0,'championId':103,'assignedPosition':'middle'}],
                'theirTeam':[{'championId':1,'assignedPosition':'middle'}],
                'timer':{'phase':'FINALIZATION'if self.finalization else'BAN_PICK'}},
            '/lol-game-data/assets/v1/champion-summary.json':[{'id':103,'name':'Ahri','alias':'Ahri'},{'id':1,'name':'Annie','alias':'Annie'}],
        }
        if path not in data:raise ValueError('Only synthetic draft reads are permitted')
        return data[path]


class CountingTransport(HTTPTransport):
    def __init__(self):super().__init__();self.urls=[]
    def get(self,url):
        if len(self.urls)>=4:raise ValueError('Source query budget exceeded')
        self.urls.append(url)
        return super().get(url)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live-source',action='store_true',help='allow at most four logical source GETs, three attempts each')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args(argv)
    if not args.live_source:parser.error('pass --live-source to allow the bounded source checks')
    transport=CountingTransport();draft=SyntheticDraft()
    service=BuildService(draft,Client(transport=transport),risk=lambda:'medium')
    report={'checked_at':datetime.now(timezone.utc).isoformat(),'lcu':'synthetic; no game writes','checks':[]}
    code=0
    try:
        for kind in ['general','matchup']:
            if kind=='matchup':draft.finalization=True
            context=service.context()
            result=service.query({'revision':context['revision'],'selection':kind,'opponentId':1},service.begin_query())
            expected={'wr','common'}if kind=='general'else{'vs:1'}
            if set(row['id']for row in result['entries'])!=expected:raise ValueError('Unexpected prepared pages')
            report['checks'].append({'selection':kind,'status':'passed','entries':[
                {'id':row['id'],'source_url':row['page']['source_url'],'patch':row['page']['resolved']['patch'],
                 'keystone':row['page']['keystone'],'runes':row['page']['runes'],'core_metrics':row['page']['core_metrics'],
                 'rune_metrics':row['runeMetrics'],'rune_metric_scope':row['runeMetricScope'],
                 'blocks':[b['kind']for b in row['page']['blocks']]}for row in result['entries']]})
    except Exception as error:
        report['failure']=type(error).__name__+': '+str(error)
        code=1
    finally:service.close()
    report['source_gets']=len(transport.urls)
    text=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if args.output:args.output.write_text(text,encoding='utf-8')
    print(text,end='')
    return code


if __name__=='__main__':raise SystemExit(main())
