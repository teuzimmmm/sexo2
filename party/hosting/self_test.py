"""Packaged host verification; synthetic players, no user settings or game access."""
import asyncio,json,queue,time,ssl,logging
from pathlib import Path
from urllib.parse import urlsplit,parse_qs,urlencode
import certifi
from ..network.tunnel_connection import secure_connection
from .controller import HostController

async def exchange(link):
    p=urlsplit(link);token=parse_qs(p.fragment)['rose'][0]
    url='wss://'+p.netloc+'/room?'+urlencode({'key':'rose-packaged-test-room','access':token,'v':'1.4.7'})
    logger=logging.getLogger('rose.host.selftest');logger.setLevel(logging.WARNING)
    kwargs={'ssl':ssl.create_default_context(cafile=certifi.where()),'logger':logger,'open_timeout':15,'close_timeout':2}
    async with secure_connection(url,**kwargs)as a,secure_connection(url,**kwargs)as b:
        await a.recv();await b.recv()
        await a.send(json.dumps({'type':'join','summoner_id':1001,'summoner_name':'Teste A'}))
        await b.send(json.dumps({'type':'join','summoner_id':1002,'summoner_name':'Teste B'}))
        metadata={'version':1,'ready':True,'lottery_optin':True,'choices':[{'champion_id':11,'skin_id':11001}], 'lottery':{'seed':'a'*32,'created':int(time.time()*1000),'theme':'PROJETO','targets':[1001,1002]}}
        await a.send(json.dumps({'type':'skin','skin':{'champion_id':11,'skin_id':11001,'friends':metadata}}))
        await b.send(json.dumps({'type':'skin','skin':{'champion_id':22,'skin_id':22002}}))
        async def received(ws,expected):
            for _ in range(15):
                msg=json.loads(await asyncio.wait_for(ws.recv(),10))
                if any((m.get('skin')or{}).get('skin_id')==expected and (expected!=11001 or (m.get('skin')or{}).get('friends',{}).get('lottery',{}).get('seed')=='a'*32) for m in msg.get('members',[])):return
            raise RuntimeError('Skin state did not arrive')
        await received(a,22002);await received(b,11001)

def run(output):
    controller=HostController();result={'ok':False,'public_tunnel':False,'two_clients':False,'preferences_changed':False}
    try:
        controller.start();deadline=time.monotonic()+210
        while time.monotonic()<deadline:
            try:kind,value=controller.events.get(timeout=1)
            except queue.Empty:continue
            if kind=='error':raise RuntimeError(value)
            if kind=='ready':
                result['public_tunnel']=True;asyncio.run(exchange(value));result['two_clients']=True;result['friends_metadata']=True;result['ok']=True;break
        else:raise RuntimeError('Startup timeout')
    except Exception as e:
        result['error']=str(e)
        result['last_check_error']=controller.last_check_error
        result['tunnel_log_tail']=controller.last_logs[-8:]
    finally:
        controller.stop(wait=True);result['stopped']=not bool(controller.thread and controller.thread.is_alive())
        Path(output).write_text(json.dumps(result,indent=2),encoding='utf-8')
