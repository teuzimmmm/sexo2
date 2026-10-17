"""Mode identity shared by live features; never reinterpret collector statistics."""
from .draft import game_mode


def play_mode(data):
    if not isinstance(data, dict):return None
    queue=data.get('queue') if isinstance(data.get('queue'),dict) else {}
    qid=data.get('queueId',queue.get('id'))
    name=str(data.get('gameMode',queue.get('gameMode',''))).upper()
    if qid==2400 or name=='KIWI':return 'mayhem'
    if data.get('mapId',queue.get('mapId'))==11 and (qid==480 or name=='SWIFTPLAY'):return 'swiftplay'
    return game_mode(data)
