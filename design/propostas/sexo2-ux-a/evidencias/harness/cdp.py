import socket,base64,os,json,struct,subprocess,time,urllib.request,glob
CHROME=glob.glob(os.path.expanduser('~/Library/Caches/ms-playwright/chromium-1228/chrome-mac-arm64/*.app/Contents/MacOS/*'))[0]
class WS:
    def __init__(s,url):
        u=url[5:];host,path=u.split('/',1);h,p=host.split(':');s.s=socket.create_connection((h,int(p)))
        k=base64.b64encode(os.urandom(16)).decode()
        s.s.send(f"GET /{path} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {k}\r\nSec-WebSocket-Version: 13\r\n\r\n".encode())
        b=b''
        while b'\r\n\r\n' not in b: b+=s.s.recv(1)
        s.i=0
    def send(s,m):
        d=json.dumps(m).encode();mask=os.urandom(4);l=len(d);hd=b'\x81'
        if l<126:hd+=bytes([0x80|l])
        elif l<65536:hd+=bytes([0x80|126])+struct.pack('>H',l)
        else:hd+=bytes([0x80|127])+struct.pack('>Q',l)
        s.s.sendall(hd+mask+bytes(c^mask[i%4] for i,c in enumerate(d)))
    def rd(s,n):
        b=b''
        while len(b)<n:
            c=s.s.recv(n-len(b))
            if not c:raise EOFError
            b+=c
        return b
    def recv(s):
        msg=b''
        while True:
            h=s.rd(2);op=h[0]&15;fin=h[0]&128;l=h[1]&127
            if l==126:l=struct.unpack('>H',s.rd(2))[0]
            elif l==127:l=struct.unpack('>Q',s.rd(8))[0]
            d=s.rd(l);msg+=d
            if fin:break
        return json.loads(msg)
    def call(s,method,**p):
        s.i+=1;i=s.i;s.send({'id':i,'method':method,'params':p})
        while True:
            r=s.recv()
            if r.get('id')==i:
                if 'error' in r:raise Exception(r['error'])
                return r['result']
class Br:
    def __init__(s,w,h):
        s.p=subprocess.Popen([CHROME,'--headless=new','--remote-debugging-port=9333','--no-first-run','--disable-renderer-backgrounding','--disable-background-timer-throttling','--disable-backgrounding-occluded-windows','--disable-features=CalculateNativeWinOcclusion','--user-data-dir=/private/tmp/claude-501/sc/prof','--allow-file-access-from-files',f'--window-size={w},{h}','about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                t=json.load(urllib.request.urlopen('http://127.0.0.1:9333/json'));break
            except Exception:time.sleep(.2)
        pg=[x for x in t if x['type']=='page'][0];s.ws=WS(pg['webSocketDebuggerUrl'])
        s.c=s.ws.call;s.c('Page.enable');s.c('Emulation.setFocusEmulationEnabled',enabled=True);s.c('Page.bringToFront');s.c('Runtime.enable')
    def size(s,w,h):s.c('Emulation.setDeviceMetricsOverride',width=w,height=h,deviceScaleFactor=1,mobile=False)
    def go(s,url):s.c('Page.navigate',url=url);time.sleep(1.2)
    def js(s,e):
        r=s.c('Runtime.evaluate',expression=e,returnByValue=True,awaitPromise=True)
        if 'exceptionDetails' in r:raise Exception(r['exceptionDetails'])
        return r['result'].get('value')
    def shot(s,path):
        open(path,'wb').write(base64.b64decode(s.c('Page.captureScreenshot',format='png')['data']))
    def key(s,k,mod=0):
        codes={'Tab':9,'Escape':27,'Enter':13,' ':32}
        for t in('rawKeyDown','keyUp'):s.c('Input.dispatchKeyEvent',type=('keyDown' if (t=='rawKeyDown' and k in('Enter',' ')) else t),key=k,code=k,windowsVirtualKeyCode=codes[k],modifiers=mod,**({'text':{'Enter':'\r',' ':' '}[k]} if (t=='rawKeyDown' and k in('Enter',' ')) else {}))
    def close(s):s.p.terminate()
