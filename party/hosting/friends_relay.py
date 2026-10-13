"""Small in-memory friends relay. Listens on loopback only; cloudflared provides TLS."""
import asyncio
import hmac
import logging
import json
import time
from collections import defaultdict, deque
from urllib.parse import urlsplit,parse_qs
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

class FriendsRelay:
    def __init__(self, token, max_members=10):
        if len(token)<32: raise ValueError('A session needs a random access token')
        self.token = token
        self.max_members = max_members
        self.rooms = defaultdict(dict)
        self.connections = set()
        self.server = None
        self.port = None

    def request(self, connection, request):
        parts = urlsplit(request.path)
        if parts.path=='/' and request.headers.get('Upgrade','').lower()!='websocket':
            return connection.respond(200,json.dumps({'status':'ok','service':'rose-friends-relay'}))
        query = parse_qs(parts.query)
        supplied = query.get('access',[''])[0]
        key = query.get('key',[''])[0]
        if parts.path!='/room' or not hmac.compare_digest(supplied.encode("utf-8"),self.token.encode("utf-8")):
            return connection.respond(403,'Link da sala inválido ou expirado.\n')
        if not 8<=len(key)<=64: return connection.respond(400,'Invalid room\n')
        try:
            version=tuple(int(x) for x in query.get('v',['0'])[0].split('.')[:3])
        except ValueError:version=(0,)
        if version<(1,4,4):return connection.respond(426,'Atualize o aplicativo para uma versão compatível.\n')
        if len(self.connections)>=self.max_members: return connection.respond(409,'Room is full\n')
        connection.rose_room = key
        return None

    async def start(self,port=0):
        logger = logging.getLogger("rose.private.server")
        logger.setLevel(logging.WARNING)
        self.server = await serve(self.handler,'127.0.0.1',port,process_request=self.request,max_size=65536,max_queue=8,close_timeout=2,ping_interval=20,ping_timeout=30,server_header=None,logger=logger)
        self.port = self.server.sockets[0].getsockname()[1]
        return self.port

    async def close(self):
        if self.server:
            self.server.close();await self.server.wait_closed();self.server=None

    async def broadcast(self,key):
        members=list(self.rooms.get(key,{}).items())
        payload=json.dumps({'type':'members','members':[data for _,data in members]},ensure_ascii=False)
        async def send(ws):
            try: await asyncio.wait_for(ws.send(payload),2)
            except (ConnectionClosed,TimeoutError): pass
        await asyncio.gather(*(send(ws) for ws,data in members))

    @staticmethod
    def skin(value):
        if value is None: return None
        if not isinstance(value,dict): raise ValueError('Invalid skin')
        out={}
        for name in ('champion_id','skin_id','chroma_id','sent_at'):
            val=value.get(name)
            if val is not None:
                if type(val) is not int or not 0<=val<2**53: raise ValueError('Invalid ID')
                out[name]=val
        for name in ('custom_mod_hash','custom_mod_content_hash'):
            val=value.get(name)
            if val is not None:
                if not isinstance(val,str) or len(val)>128: raise ValueError('Invalid hash')
                out[name]=val
        if value.get('is_custom') is True: out['is_custom']=True
        removed=value.get('removed')
        if isinstance(removed,list):out['removed']=[v for v in removed[:10] if type(v)is int and v>0]
        friends = value.get('friends')
        if isinstance(friends, dict) and friends.get('version') == 1:
            data = {'version': 1, 'ready': friends.get('ready') is True, 'lottery_optin': friends.get('lottery_optin') is True}
            choices = friends.get('choices')
            if isinstance(choices, list):
                data['choices'] = [{'champion_id': p['champion_id'], 'skin_id': p['skin_id'], 'skin_name': str(p.get('skin_name') or '')[:150], 'champion_name': str(p.get('champion_name') or '')[:100]} for p in choices[:2] if isinstance(p, dict) and type(p.get('champion_id')) is int and type(p.get('skin_id')) is int and 0 < p['champion_id'] < 1000000 and p['skin_id'] // 1000 == p['champion_id']]
            lottery = friends.get('lottery')
            if isinstance(lottery, dict):
                seed = lottery.get('seed'); created = lottery.get('created'); theme = lottery.get('theme'); targets = lottery.get('targets')
                if isinstance(seed, str) and len(seed) == 32 and all(c in '0123456789abcdef' for c in seed) and type(created) is int and isinstance(theme, str) and len(theme) <= 60 and isinstance(targets, list):
                    data['lottery'] = {'seed': seed, 'created': created, 'theme': theme, 'targets': [sid for sid in targets[:10] if type(sid) is int and 0 < sid < 2**53]}
            out['friends'] = data
        return out

    async def handler(self,ws):
        if len(self.connections)>=self.max_members:
            await ws.close(1013,'full');return
        self.connections.add(ws)
        key=ws.rose_room
        room=self.rooms[key]
        rate=deque()
        try:
            await ws.send(json.dumps({'type':'members','members':list(room.values())}))
            async for raw in ws:
                now=time.monotonic()
                while rate and now-rate[0]>1:rate.popleft()
                rate.append(now)
                if len(rate)>30:
                    await ws.close(1008,'rate limited');break
                if raw=='ping': await ws.send('pong');continue
                if not isinstance(raw,str):continue
                try:msg=json.loads(raw)
                except ValueError:continue
                if not isinstance(msg,dict):continue
                kind=msg.get('type')
                if kind=='join':
                    sid=msg.get('summoner_id')
                    if type(sid)is not int or not 0<sid<2**53:
                        await ws.close(1008,'invalid member');break
                    previous=[other for other,data in list(room.items()) if other is not ws and data['summoner_id']==sid]
                    for other in previous:
                        room.pop(other,None)
                        await other.close(1000,'replaced')
                    room[ws]={'summoner_id':sid,'summoner_name':str(msg.get('summoner_name') or 'Amigo')[:128]}
                    await self.broadcast(key)
                elif kind=='skin' and ws in room:
                    try:room[ws]['skin']=self.skin(msg.get('skin'))
                    except ValueError:
                        await ws.close(1008,'invalid skin');break
                    await self.broadcast(key)
                elif kind=='leave':break
        except ConnectionClosed:pass
        finally:
            self.connections.discard(ws)
            room.pop(ws,None)
            await self.broadcast(key)
            if not room and not any(getattr(other,"rose_room",None)==key for other in self.connections):
                if self.rooms.get(key)is room:self.rooms.pop(key,None)
