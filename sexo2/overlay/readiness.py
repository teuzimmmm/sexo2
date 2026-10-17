"""Anonymous readiness signal: the game process alone is not a running match."""
import math
import time
from .gold import LiveClient


class GameReadiness:
    def __init__(self,*,client=None,clock=time.monotonic):
        self.client=client or LiveClient();self.clock=clock
        self.at=float('-inf');self.last_time=None;self.context=None;self.available=False

    def check(self,context):
        if context!=self.context:
            self.context=context;self.last_time=None
        self.available=False
        try:
            started=self.clock()
            data=self.client.get('gamestats',started+2)
            value=data.get('gameTime') if isinstance(data,dict) else None
            if type(value) not in (int,float) or not math.isfinite(value) or not 0<value<86400:return False
            if self.last_time is not None and value<self.last_time:
                self.last_time=value;return False
            if self.clock()-started>=2:return False
            self.last_time=value;self.at=started;self.available=True
        except Exception:pass
        return self.available

    def fresh(self):return self.available and 0<=self.clock()-self.at<3
    def close(self):self.available=False;self.client.close()
