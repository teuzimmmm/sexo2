/*
 * Dados demonstrativos do protótipo (simulação).
 * Win rates, partidas, inventários e jogadores são inventados para ilustrar a interface.
 * Ícones, nomes, IDs e preços vêm do jogo (js/game-data.js).
 * O win rate exibido nas recomendações de runas é o da runa-chave, como no LoLalytics.
 */
window.S2_DEMO = {
  patch: "16.20",
  lanes: {
    top: "Topo",
    jungle: "Selva",
    middle: "Meio",
    bottom: "Atirador",
    utility: "Suporte",
  },

  // Seleção de campeões simulada. A rota inimiga vem de inferência e pode ser corrigida.
  allies: [
    { player: "Kaio", champion: "Garen", lane: "top" },
    { player: "Bruna", champion: "LeeSin", lane: "jungle" },
    { player: "Você", champion: "Ahri", lane: "middle", me: true },
    { player: "Davi", champion: "Jinx", lane: "bottom" },
    { player: "Lia", champion: "Thresh", lane: "utility" },
  ],
  enemies: [
    { champion: "Darius", lanes: { top: 0.86, jungle: 0.08, middle: 0.06 } },
    { champion: "Vi", lanes: { jungle: 0.94, top: 0.06 } },
    { champion: "Annie", lanes: { middle: 0.78, utility: 0.17, top: 0.05 } },
    { champion: "Kaisa", lanes: { bottom: 0.91, middle: 0.09 } },
    { champion: "Lulu", lanes: { utility: 0.88, middle: 0.07, top: 0.05 } },
  ],
  pool: [
    "Ahri", "Akali", "Annie", "Aurora", "Darius", "Garen", "Hwei", "Jinx", "Kaisa", "Katarina", "Leblanc",
    "LeeSin", "Lulu", "Lux", "Orianna", "Syndra", "Taliyah", "Thresh", "Veigar", "Vex", "Vi", "Viktor",
    "Yasuo", "Zed",
  ],

  // Runas: páginas completas sugeridas e WR/partidas da runa-chave.
  runes: {
    Ahri: {
      win: { wr: 56.8, games: 7505, page: { primary: 8100, sub: 8200, perks: [8112, 8139, 8137, 8106, 8226, 8210, 5008, 5008, 5011] } },
      pick: { wr: 52.1, games: 41212, page: { primary: 8300, sub: 8200, perks: [8369, 8304, 8313, 8347, 8226, 8210, 5008, 5008, 5011] } },
      vs: {
        Annie: {
          win: { wr: 55.9, games: 1606, page: { primary: 8100, sub: 8400, perks: [8112, 8126, 8137, 8106, 8444, 8242, 5008, 5008, 5011] } },
          pick: { wr: 53.2, games: 2104, page: { primary: 8300, sub: 8200, perks: [8369, 8304, 8313, 8347, 8226, 8210, 5008, 5008, 5011] } },
        },
        Darius: {
          win: { wr: 54.1, games: 412, page: { primary: 8200, sub: 8300, perks: [8229, 8226, 8210, 8237, 8304, 8347, 5008, 5008, 5011] } },
          pick: { wr: 51.0, games: 690, page: { primary: 8100, sub: 8200, perks: [8112, 8139, 8137, 8106, 8226, 8210, 5008, 5008, 5011] } },
        },
      },
    },
    Syndra: {
      win: { wr: 53.4, games: 5120, page: { primary: 8200, sub: 8300, perks: [8229, 8226, 8210, 8237, 8304, 8347, 5008, 5008, 5011] } },
      pick: { wr: 51.7, games: 23890, page: { primary: 8300, sub: 8200, perks: [8369, 8304, 8313, 8347, 8226, 8210, 5008, 5008, 5011] } },
      vs: {},
    },
  },

  // Itens: trio observado em conjunto (WR do trio) e alternativas por posição (WR de cada item).
  // Conjunto de itens SEXO2: uma página com até três grupos de três seções.
  // Ahri: números e itens reais das fixtures LoLalytics do repositório (16.20, Esmeralda+, meio).
  items: {
    Ahri: {
      groups: [
        { title: "59,3% — 1.077 partidas", tip: "Win rate dos três primeiros itens juntos|1.077 partidas com esses três itens", seq: [3118, 3020, 3100, 3041, 4645, 3089], start: [[1056, 1], [2003, 2]], alt: [3157] },
        { title: "53,6% — 26.214 partidas", tip: "Win rate dos três primeiros itens juntos|26.214 partidas com esses três itens", seq: [3118, 3020, 4645, 3157, 3089, 3135], start: [[1056, 1], [2003, 2]], alt: [3041] },
      ],
      counter: {
        Annie: { title: "Counter Annie — 49,57% — 1.852 partidas", tip: "Win rate de Ahri contra Annie|1.852 partidas no confronto", seq: [6655, 3158, 3041, 4645, 3157, 3089], start: [[1056, 1], [2003, 2]], alt: [3135] },
      },
    },
    Syndra: {
      groups: [
        { title: "55,0% — 2.804 partidas", tip: "Win rate dos três primeiros itens juntos|2.804 partidas com esses três itens", seq: [6655, 3020, 3089, 3135, 3157, 3102], start: [[1056, 1], [2003, 2]], alt: [3165] },
        { title: "53,1% — 14.020 partidas", tip: "Win rate dos três primeiros itens juntos|14.020 partidas com esses três itens", seq: [6655, 3020, 4645, 3089, 3135, 3157], start: [[1056, 1], [2003, 2]], alt: [3102] },
      ],
      counter: {},
    },
  },

  // Aprimoramentos: nomes e ícones reais (capturas de ARAM Mayhem); estatísticas simuladas.
  // Os nomes aparecem no idioma do cliente; as capturas disponíveis estão em inglês.
  augments: {
    names: {
      "scopier-weapons": "Scopier Weapons", vulnerability: "Vulnerability", "combusting-interest": "Combusting Interest",
      overflow: "Overflow", "ravenous-bind": "Ravenous Bind", "upgrade-sheen": "Upgrade Sheen",
      "ultimate-revolution": "Ultimate Revolution", "blade-waltz": "Blade Waltz", overloaded: "Overloaded",
      "infernal-soul": "Infernal Soul", juiced: "Juiced", firefox: "FireFox",
    },
    // Cada modo tem a sua fonte e os seus números; nunca se misturam.
    mayhem: {
      source: "ARAMKit", patch: "16.20",
      offers: [["overflow", "ravenous-bind", "upgrade-sheen"], ["scopier-weapons", "vulnerability", "combusting-interest"], ["ultimate-revolution", "blade-waltz", "overloaded"]],
      rerolls: ["juiced", "firefox", "infernal-soul", "blade-waltz"],
      stats: {
        overflow: { wr: 52.4, pr: 6.1, n: 4210 }, "ravenous-bind": { wr: 49.8, pr: 2.3, n: 1580 }, "upgrade-sheen": { wr: 54.9, pr: 4.4, n: 3022 },
        "scopier-weapons": { wr: 51.2, pr: 7.9, n: 5410 }, vulnerability: { wr: 50.6, pr: 3.1, n: 2104 }, "combusting-interest": { wr: 48.9, pr: 1.2, n: 812 },
        "ultimate-revolution": { wr: 56.3, pr: 9.8, n: 1977 }, "blade-waltz": { wr: 53.0, pr: 5.5, n: 1103 },
        juiced: { wr: 50.1, pr: 2.6, n: 940 }, firefox: { wr: 47.7, pr: 1.9, n: 655 }, "infernal-soul": { wr: 52.0, pr: 3.3, n: 120 },
      },
    },
    arena: {
      source: "LoLalytics", patch: "16.20",
      offers: [["scopier-weapons", "blade-waltz", "ultimate-revolution"], ["infernal-soul", "juiced", "firefox"]],
      rerolls: ["vulnerability", "upgrade-sheen", "overflow"],
      // Arena: só PR e partidas (a WR de Arena fica oculta, ver docs/lolalytics/FONTES.md).
      stats: {
        "scopier-weapons": { pr: 17.7, n: 9777 }, "blade-waltz": { pr: 12.1, n: 6690 },
        "infernal-soul": { pr: 8.4, n: 4630 }, firefox: { pr: 5.2, n: 2871 }, vulnerability: { pr: 6.0, n: 3305 },
      },
    },
  },

  mods: {
    Ahri: [
      { name: "Ahri Arcana (cores)", file: "ahri-arcana.fantome" },
      { name: "Ahri Coven", file: "ahri-coven.modpkg" },
    ],
    Syndra: [],
  },

  // Partida simulada: inventários por momento (IDs reais; o valor vem do preço do jogo).
  match: {
    order: ["Garen", "LeeSin", "Ahri", "Jinx", "Thresh"],
    chaos: ["Darius", "Vi", "Annie", "Kaisa", "Lulu"],
    kda: {
      12: ["1/0/1", "2/1/3", "3/1/2", "1/1/2", "0/1/4", "0/1/0", "1/2/1", "1/2/1", "1/1/0", "0/1/1"],
      22: ["3/2/4", "4/3/9", "7/2/6", "5/2/6", "0/3/12", "2/4/2", "3/4/5", "4/5/4", "3/3/3", "1/3/6"],
      30: ["5/4/7", "6/5/13", "10/3/9", "8/4/10", "1/5/18", "4/6/5", "5/7/8", "6/7/7", "6/5/6", "1/5/11"],
    },
    inventories: {
      12: {
        order: [[3047, 3071], [3047, 6692], [3020, 6655, 1052], [3006, 1036, 1036], [3190, 3009]],
        chaos: [[3047, 1036], [3111, 1036], [3020, 1058], [3006, 1036], [3158, 1052]],
      },
      22: {
        order: [[3047, 3071, 3053], [3047, 6692, 3071], [3020, 6655, 4645], [3006, 6672, 3031], [3190, 3009, 3107]],
        chaos: [[3047, 3071, 1036], [3111, 6692], [3020, 6653, 3089], [3006, 6672, 1036], [3158, 6617]],
      },
      30: {
        order: [[3047, 3071, 3053, 3065], [3047, 6692, 3071, 3053], [3020, 6655, 4645, 3089, 3157], [3006, 6672, 3031, 3036, 3046], [3190, 3009, 3107, 3075]],
        chaos: [[3047, 3071, 3053, 1036], [3111, 6692, 3071], [3020, 6653, 3089, 3135], [3006, 6672, 3031, 3046], [3158, 6617, 3504]],
      },
    },
  },

  // Painel SEXO2 (fora da seleção).
  library: [
    { name: "Ahri Arcana (cores)", champion: "Ahri", category: "skins", size: "18,2 MB" },
    { name: "Ahri Coven", champion: "Ahri", category: "skins", size: "22,7 MB" },
    { name: "Jinx Star Guardian HD", champion: "Jinx", category: "skins", size: "31,0 MB" },
    { name: "Summoner's Rift Inverno", champion: null, category: "maps", size: "96,4 MB" },
    { name: "Beaufort Regular", champion: null, category: "fonts", size: "1,1 MB" },
    { name: "Narrador clássico", champion: null, category: "announcers", size: "12,9 MB" },
  ],
  favorites: { Ahri: "Ahri Espírito da Flor", Jinx: "Jinx Estrela Guardiã", Garen: "Garen Deus-Rei", Thresh: "Thresh Lua Sangrenta" },
  profiles: ["Padrão", "Temas de evento", "Só lendárias"],
  room: {
    link: "https://exemplo.trycloudflare.com/#…",
    members: [
      { name: "Você", status: "Pronto", skins: 1 },
      { name: "Bruna", status: "Pronto", skins: 1 },
      { name: "Davi", status: "Na seleção", skins: 0 },
    ],
  },
  diagnostics: {
    version: "1.6.4",
    checks: [
      ["Cliente do LoL", "Conectado"],
      ["Plugins", "Ativos"],
      ["Ferramentas de injeção", "Prontas"],
      ["Biblioteca de skins", "Atualizada"],
    ],
    issues: [
      { when: "Hoje, 14:02", text: "A injeção demorou mais que o esperado (8,4 s)." },
      { when: "Ontem, 22:41", text: "O cliente reiniciou durante a seleção; a sala reconectou." },
    ],
  },
};
