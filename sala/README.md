# Sala sempre online (Cloudflare Worker)

Relay da sala do SEXO2 (D-133). Mesmo protocolo de `party/hosting/friends_relay.py`: uma Durable
Object por sala, chaveada pela chave derivada do anfitrião. Plano gratuito da Cloudflare; as conexões
hibernam e o `ping` é respondido sem acordar a sala. O app aponta para ele em
`party/network/relay_config.py`.

## Publicar (Windows, uma vez e a cada mudança em `src/`)
Precisa do Node.js (https://nodejs.org, versão LTS). Num terminal, dentro desta pasta:

```
npx wrangler login     # abre o navegador; autorize a conta da Cloudflare
npx wrangler deploy
```

O deploy substitui o "Hello World" do Worker `sexo2-sala`. Conferir:
`https://sexo2-sala.matheus-barbosa-gomes10.workers.dev` responde
`{"status":"ok","service":"sexo2-friends-relay"}`.

## Testar localmente
`npx wrangler dev --port 8799` e aponte o app com `SEXO2_RELAY_URL=ws://127.0.0.1:8799`.
