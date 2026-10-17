"""Private display-only v2 protocol; no game identity, source bodies or paths."""
import json
import threading
import time
from .model import Card,View
from .display import Frame
from .wire import MAX_BYTES,MAX_CARDS,MAX_LINES,MAX_SEQUENCE,_text,ProtocolError


def encode(frame,sequence,context):
    if type(sequence) is not int or not 1<=sequence<=MAX_SEQUENCE:raise ProtocolError('Invalid sequence')
    if type(context) is not int or not 0<=context<=MAX_SEQUENCE:raise ProtocolError('Invalid context')
    for flag in (frame.active,frame.offer_layout,frame.opponent_switch):
        if type(flag) is not bool:raise ProtocolError('Invalid display flags')
    cards=[]
    if frame.active:
        if len(frame.view.cards)>MAX_CARDS:raise ProtocolError('Too many cards')
        for card in frame.view.cards:
            if len(card.lines)>MAX_LINES:raise ProtocolError('Too many lines')
            cards.append({'title':_text(card.title),'lines':[_text(v) for v in card.lines]})
    selected=frame.view.selected if cards else 0
    data={'v':2,'seq':sequence,'context':context,'ttlMs':2000,'active':frame.active,
          'offers':frame.offer_layout,'opponent':frame.opponent_switch,'selected':selected,'cards':cards}
    raw=(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n').encode()
    decode(raw)
    return raw


def decode(raw):
    if not isinstance(raw,bytes) or len(raw)>MAX_BYTES or not raw.endswith(b'\n'):raise ProtocolError('Frame size or terminator invalid')
    try:data=json.loads(raw)
    except (ValueError,UnicodeError,RecursionError):raise ProtocolError('Malformed frame') from None
    if not isinstance(data,dict) or set(data)!={'v','seq','context','ttlMs','active','offers','opponent','selected','cards'} or data['v']!=2:raise ProtocolError('Unknown schema')
    for key,lo,hi in [('seq',1,MAX_SEQUENCE),('context',0,MAX_SEQUENCE),('ttlMs',1,2000)]:
        if type(data[key]) is not int or not lo<=data[key]<=hi:raise ProtocolError('Invalid numeric field')
    if any(type(data[k]) is not bool for k in ('active','offers','opponent')):raise ProtocolError('Invalid flags')
    cards=data['cards']
    if not isinstance(cards,list) or len(cards)>MAX_CARDS or (not data['active'] and cards):raise ProtocolError('Invalid cards')
    if type(data['selected']) is not int or not 0<=data['selected']<max(1,len(cards)):raise ProtocolError('Invalid selection')
    for card in cards:
        if not isinstance(card,dict) or set(card)!={'title','lines'}:raise ProtocolError('Invalid card')
        _text(card['title'])
        if not isinstance(card['lines'],list) or len(card['lines'])>MAX_LINES:raise ProtocolError('Invalid lines')
        for value in card['lines']:_text(value)
    if data['active'] and data['offers'] and len(cards)!=3:raise ProtocolError('Three offers required')
    return data


class Inbox:
    def __init__(self,*,clock=time.monotonic):
        self.clock=clock;self.lock=threading.Lock();self.data=None;self.until=0;self.sequence=0;self.closed=False

    def accept(self,raw):
        try:
            data=decode(raw)
            with self.lock:
                if self.closed or data['seq']<=self.sequence:raise ProtocolError('Out of order frame')
                self.data=data;self.sequence=data['seq'];self.until=self.clock()+data['ttlMs']/1000
        except ProtocolError:
            self.close();raise

    def close(self):
        with self.lock:self.data=None;self.closed=True

    def frame(self):
        with self.lock:
            d=self.data
            if self.closed or d is None or self.clock()>=self.until:return Frame()
            return Frame(d['active'],View(str(d['context']),tuple(Card(c['title'],tuple(c['lines'])) for c in d['cards']),d['selected']),
                         opponent_switch=d['opponent'],offer_layout=d['offers'])
