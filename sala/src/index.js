// Sala do SEXO2 sempre online, num Worker da Cloudflare.
// Mesmo protocolo do relay local (party/hosting/friends_relay.py): uma Durable Object
// por sala, chaveada pela chave que o anfitrião deriva (compute_room_key em ws_relay.py).
// A chave da sala tem 128 bits e é o segredo; o relay não pede outra senha.
// As conexões hibernam: "ping" é respondido sem acordar a sala, e os dados de cada
// membro ficam no anexo do WebSocket, que sobrevive à hibernação.
import { DurableObject } from 'cloudflare:workers';

const MAX_MEMBERS = 10;
const MIN_VERSION = [1, 4, 4];
const MAX_MESSAGE = 65536;
const RATE_LIMIT = 30; // mensagens por segundo, por conexão

function text(body, status) {
  return new Response(body, { status, headers: { 'content-type': 'text/plain; charset=utf-8' } });
}

function tooOld(raw) {
  const parts = String(raw || '0')
    .split('.')
    .slice(0, 3)
    .map((part) => (/^\d+$/.test(part) ? Number(part) : NaN));
  if (parts.some(Number.isNaN)) return true;
  for (let i = 0; i < MIN_VERSION.length; i++) {
    const part = parts[i] ?? -1;
    if (part !== MIN_VERSION[i]) return part < MIN_VERSION[i];
  }
  return false;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if ((request.headers.get('Upgrade') || '').toLowerCase() !== 'websocket') {
      if (url.pathname === '/') return Response.json({ status: 'ok', service: 'sexo2-friends-relay' });
      return text('Not found\n', 404);
    }
    if (url.pathname !== '/room') return text('Link da sala inválido ou expirado.\n', 403);
    const key = url.searchParams.get('key') || '';
    if (key.length < 8 || key.length > 64) return text('Invalid room\n', 400);
    if (tooOld(url.searchParams.get('v'))) return text('Atualize o aplicativo para uma versão compatível.\n', 426);
    return env.ROOMS.get(env.ROOMS.idFromName(key)).fetch(request);
  },
};

const isId = (value) => Number.isSafeInteger(value) && value >= 0;

// Igual a FriendsRelay.skin: só os campos conhecidos, com tipos e tamanhos conferidos.
export function cleanSkin(value) {
  if (value === null || value === undefined) return null;
  if (typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid skin');
  const out = {};
  for (const name of ['champion_id', 'skin_id', 'chroma_id', 'sent_at']) {
    const val = value[name];
    if (val !== null && val !== undefined) {
      if (!isId(val)) throw new Error('Invalid ID');
      out[name] = val;
    }
  }
  for (const name of ['custom_mod_hash', 'custom_mod_content_hash']) {
    const val = value[name];
    if (val !== null && val !== undefined) {
      if (typeof val !== 'string' || val.length > 128) throw new Error('Invalid hash');
      out[name] = val;
    }
  }
  if (value.is_custom === true) out.is_custom = true;
  if (Array.isArray(value.removed)) out.removed = value.removed.slice(0, 10).filter((v) => Number.isSafeInteger(v) && v > 0);
  const friends = value.friends;
  if (friends && typeof friends === 'object' && friends.version === 1) {
    const data = { version: 1, ready: friends.ready === true, lottery_optin: friends.lottery_optin === true };
    if (Array.isArray(friends.choices)) {
      data.choices = friends.choices
        .slice(0, 2)
        .filter(
          (p) =>
            p &&
            typeof p === 'object' &&
            Number.isSafeInteger(p.champion_id) &&
            Number.isSafeInteger(p.skin_id) &&
            p.champion_id > 0 &&
            p.champion_id < 1000000 &&
            Math.floor(p.skin_id / 1000) === p.champion_id,
        )
        .map((p) => ({
          champion_id: p.champion_id,
          skin_id: p.skin_id,
          skin_name: String(p.skin_name || '').slice(0, 150),
          champion_name: String(p.champion_name || '').slice(0, 100),
        }));
    }
    const lottery = friends.lottery;
    if (
      lottery &&
      typeof lottery === 'object' &&
      typeof lottery.seed === 'string' &&
      /^[0-9a-f]{32}$/.test(lottery.seed) &&
      Number.isSafeInteger(lottery.created) &&
      typeof lottery.theme === 'string' &&
      lottery.theme.length <= 60 &&
      Array.isArray(lottery.targets)
    ) {
      data.lottery = {
        seed: lottery.seed,
        created: lottery.created,
        theme: lottery.theme,
        targets: lottery.targets.slice(0, 10).filter((sid) => Number.isSafeInteger(sid) && sid > 0),
      };
    }
    out.friends = data;
  }
  return out;
}

export class Room extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    ctx.setWebSocketAutoResponse(new WebSocketRequestResponsePair('ping', 'pong'));
    this.rates = new WeakMap();
  }

  async fetch() {
    if (this.ctx.getWebSockets().length >= MAX_MEMBERS) return text('Room is full\n', 409);
    const [client, server] = Object.values(new WebSocketPair());
    this.ctx.acceptWebSocket(server);
    server.send(JSON.stringify({ type: 'members', members: this.members() }));
    return new Response(null, { status: 101, webSocket: client });
  }

  joined(except) {
    return this.ctx.getWebSockets().filter((ws) => ws !== except && ws.deserializeAttachment());
  }

  members(except) {
    return this.joined(except).map((ws) => ws.deserializeAttachment());
  }

  broadcast(except) {
    const sockets = this.joined(except);
    const payload = JSON.stringify({ type: 'members', members: sockets.map((ws) => ws.deserializeAttachment()) });
    for (const ws of sockets) {
      try {
        ws.send(payload);
      } catch {
        // conexão já fechando; o webSocketClose dela refaz a lista
      }
    }
  }

  limited(ws) {
    const now = Date.now();
    const times = (this.rates.get(ws) || []).filter((t) => now - t <= 1000);
    times.push(now);
    this.rates.set(ws, times);
    return times.length > RATE_LIMIT;
  }

  async webSocketMessage(ws, raw) {
    if (this.limited(ws)) return ws.close(1008, 'rate limited');
    if (typeof raw !== 'string' || raw.length > MAX_MESSAGE) return;
    let msg;
    try {
      msg = JSON.parse(raw);
    } catch {
      return;
    }
    if (!msg || typeof msg !== 'object' || Array.isArray(msg)) return;
    if (msg.type === 'join') {
      const sid = msg.summoner_id;
      if (!Number.isSafeInteger(sid) || sid <= 0) return ws.close(1008, 'invalid member');
      for (const other of this.joined(ws)) {
        if (other.deserializeAttachment().summoner_id === sid) {
          other.serializeAttachment(null);
          other.close(1000, 'replaced');
        }
      }
      ws.serializeAttachment({ summoner_id: sid, summoner_name: String(msg.summoner_name || 'Amigo').slice(0, 128) });
      this.broadcast();
    } else if (msg.type === 'skin') {
      const data = ws.deserializeAttachment();
      if (!data) return;
      try {
        data.skin = cleanSkin(msg.skin);
      } catch {
        return ws.close(1008, 'invalid skin');
      }
      ws.serializeAttachment(data);
      this.broadcast();
    } else if (msg.type === 'leave') {
      ws.serializeAttachment(null);
      ws.close(1000, 'leave');
      this.broadcast(ws);
    }
  }

  async webSocketClose(ws, code, reason) {
    try {
      ws.close(code, reason);
    } catch {
      // já fechada
    }
    this.broadcast(ws);
  }

  async webSocketError(ws) {
    this.broadcast(ws);
  }
}
