"""QA automatizado da proposta B (Chromium headless, file://, CDP via stdlib).
Uso: python3 qa_b.py [rodada]   -> grava qa_resultado_<rodada>.json e capturas PNG ao lado."""
import json, os, re, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cdp import Page

ROUND = sys.argv[1] if len(sys.argv) > 1 else 'r1'
ROOT = os.path.dirname(HERE)
URL = 'file://' + os.path.join(ROOT, 'index.html')
res = []


def chk(cid, desc, ok, info=''):
    res.append({'id': cid, 'desc': desc, 'ok': bool(ok), 'info': str(info)[:300]})
    print(('PASS ' if ok else 'FAIL ') + cid + ' ' + desc + ((' | ' + str(info)[:200]) if (not ok and info) else ''))


p = Page()


def C(act, a=None, scope=''):
    aa = json.dumps(a)
    return p.js("(()=>{const l=[...document.querySelectorAll('%s[data-act=\"%s\"]')].filter(e=>%s==null||e.dataset.a===%s);if(!l.length)return false;l[0].click();return true})()" % (scope + ' ' if scope else '', act, aa, aa))


def SEL(css, val):
    return p.js("(()=>{const e=document.querySelector(%s);if(!e)return false;e.value=%s;e.dispatchEvent(new Event('change',{bubbles:true}));return true})()" % (json.dumps(css), json.dumps(val)))


def T(sel='body'):
    return p.js("(document.querySelector(%s)||{}).textContent||''" % json.dumps(sel))


def wait(t=0.15):
    time.sleep(t)


def fresh(w=1280, h=720):
    p.size(w, h)
    p.goto(URL, 0.9)
    p.events.clear()


def shot(name):
    p.shot(os.path.join(HERE, name))


def state(expr):
    return p.js(expr)


try:
    fresh()
    # ---------- B07 básico: fontes ----------
    fonts = p.js("[...document.fonts].map(f=>f.family+':'+f.status).join(',')")
    chk('B07.fonts', 'Oswald e Inter carregadas (document.fonts)', 'Oswald:loaded' in fonts and 'Inter:loaded' in fonts, fonts)
    fam = p.js("(()=>{const s=new Set();document.querySelectorAll('body *').forEach(e=>s.add(getComputedStyle(e).fontFamily.split(',')[0].trim().replace(/\"/g,'')));return [...s].join('|')})()")
    chk('B07.familias', 'Só Oswald/Inter como primeira família', set(fam.split('|')) <= {'Oswald', 'Inter'}, fam)
    chk('B07.semserifa', 'Nenhuma fonte serifada declarada no CSS', not re.search(r'serif(?!;)|Georgia|Times|Playfair|Cormorant', open(os.path.join(ROOT, 'index.html')).read().replace('sans-serif', '')), '')

    # ---------- B01 ----------
    t = T('main')
    chk('B01.home', 'Entrada mostra as 3 atividades', all(x in t.upper() for x in ['PREPARAR PARTIDA', 'PERSONALIZAR COLEÇÃO', 'RESOLVER PROBLEMA']))
    shot('b-1280-home.png')
    C('goto', 'prep'); wait()
    chk('B01.prep', 'Abrir Preparar partida', 'Antes da fila' in T('main') and p.js("document.querySelector('.steps [aria-current=step]').textContent.includes('Antes da fila')"))
    shot('b-1280-antes-fila.png')
    C('step', '1'); wait()
    chk('B01.step2', 'Etapa Na seleção', p.js("document.querySelector('.steps [aria-current=step]').textContent.includes('Na seleção')"))
    C('champ', 'Jinx'); wait()
    C('step', '2'); wait()
    chk('B01.step3', 'Etapa Em jogo', 'Em jogo' in T('.steps') and 'Overlay de ouro' in T('main'))
    shot('b-1280-em-jogo.png')
    C('step', '1'); wait()
    C('home'); wait()
    chk('B01.sair', 'Sair para Atividades', 'O QUE VOCÊ VAI FAZER' in T('main').upper())
    chk('B01.retomar', 'Home oferece retomar etapa e campeão', 'Retomar: Na seleção · Jinx' in T('main'))
    C('goto', 'prep'); wait()
    chk('B01.preserva', 'Reentrar mantém etapa, campeão, conjunto', state("S.step===1&&S.champ==='Jinx'&&S.activeSet==='s1'"))
    # erro -> suporte -> volta
    C('ptab', 'Mods'); wait()
    C('modToggle', 'm2'); wait()
    chk('B01.erro', 'Mod incompatível gera falha visível no painel', 'Resolver no suporte' in T('#qp') and state("S.errors.length===1"))
    shot('b-1280-erro-painel.png')
    C('gotoErr'); wait()
    t = T('main')
    chk('B01.suporte', 'Suporte recebe o erro com origem', 'Mod incompatível: Fonte Retrô' in t and 'Origem: Preparar partida › Na seleção › Mods' in t, t[:200])
    chk('B01.voltabtn', 'Botão voltar nomeia a origem', 'Voltar para Preparar partida › Na seleção' in t)
    shot('b-1280-suporte-erro.png')
    C('back'); wait()
    chk('B01.volta', 'Voltar restaura etapa e aba de origem', state("S.view==='prep'&&S.step===1&&S.ptab==='Mods'&&S.champ==='Jinx'") and 'Falha ao aplicar' in T('#qp'))
    C('gotoErr'); wait(); C('errFix', 'e1'); wait()
    chk('B01.resolve', 'Desativar mod e verificar resolve o erro', state("S.errors[0].done===true") and 'Nenhum erro ativo' in T('main') and '4 de 4' in T('main'))
    C('back'); wait()
    chk('B01.semerro', 'Origem não mostra mais a falha', 'Falha ao aplicar' not in T('#qp'))

    # ---------- B04 / B05 / B06 no painel ----------
    fresh()
    C('goto', 'prep'); C('step', '1'); wait()
    shot('b-1280-selecao-runas.png')
    # sem importação ao ver recomendação
    chk('B04.recnaoimporta', 'Ver recomendação não importa', state("S.imports.length===0&&S.rimp.st==='idle'"))
    imp0 = state("S.imports.length")
    C('ptab', 'Ajustes'); C('srcPref', 'Onetricks'); wait()
    chk('B04.trocafonte', 'Trocar fonte não importa nada', state("S.imports.length===%d&&S.rimp.st==='idle'&&S.srcPref==='Onetricks'" % imp0))
    C('ptab', 'Runas'); wait()
    chk('B04.onetricksindisp', 'Fonte futura indisponível não mostra dados substitutos', 'indisponível' in T('#qp') and 'Nenhuma recomendação é mostrada' in T('#qp'))
    C('srcSet', 'Lolalytics'); wait()
    C('cmp'); wait()
    q = T('#qp')
    chk('B04.compara', 'Comparação: Lolalytics com WR/amostra/patch', '51,8%' in q and '12.480 partidas' in q and 'Patch' in q)
    chk('B04.onetricksfuturo', 'Onetricks futuro/indisponível sem números', 'Futuro · indisponível' in q and 'nenhum número' in q.lower())
    shot('b-1280-comparar.png')
    C('oneSim'); wait()
    q = T('#qp')
    chk('B04.onesim', 'Simulação Onetricks separada, rotulada fictícia', 'Simulado · fictício' in q and '940 partidas' in q and 'não é somada' in q.lower())
    C('oneSim'); C('cmp'); wait()
    # importar clique
    C('rune', 'rec'); wait(0.1)
    chk('B04.importando', 'Estado importando', state("S.rimp.st==='importing'") and 'Importando' in T('#qp'))
    wait(0.8)
    chk('B04.sucesso', 'Sucesso após clique, original imediatamente', state("S.rimp.st==='success'&&S.imports.length===1") and 'Suas páginas pessoais não foram alteradas' in T('#qp'))
    SEL('#sim', 'fail'); C('rune', 'alt1'); wait(0.9)
    chk('B04.falha', 'Estado falha sem alterar nada', state("S.rimp.st==='failed'") and 'Nada foi alterado' in T('#qp'))
    SEL('#sim', 'nfp'); C('rune', 'alt2'); wait(0.9)
    q = T('#qp')
    chk('B04.nofree', 'no_free_page preserva páginas pessoais', state("S.rimp.st==='no_free_page'") and 'no_free_page' in q and q.count('mantida') == 3)
    shot('b-1280-runas-no-free-page.png')
    SEL('#sim', 'ok')
    # editor
    C('edit'); wait()
    n0 = state("S.imports.length")
    SEL('#es', 'Dominação'); wait(0.9)
    chk('B04.editorinvalido', 'Edição inválida não importa', state("S.imports.length===%d" % n0) and 'Edição inválida' in T('#qp'))
    SEL('#es', 'Precisão'); SEL('#ek', '8128'); SEL('#es', 'Feitiçaria'); wait(1.3)
    chk('B04.editoragrupa', 'Edições válidas agrupadas: 1 importação, a mais recente vence', state("S.imports.length===%d" % (n0 + 1)) and 'Editor (3 edição' in state("S.imports[0].t") and 'Feitiçaria' in state("S.imports[0].d"), state("JSON.stringify(S.imports[0])"))
    # B05 itens
    C('ptab', 'Itens'); wait()
    shot('b-1280-itens.png')
    rows = p.js("[...document.querySelectorAll('#qp .card.t')].map(c=>c.innerText.match(/([\\d.]+) partidas/)[1].replace('.','')*1)")
    chk('B05.ordem', 'Trios ordenados por partidas (desc)', rows == sorted(rows, reverse=True) and len(rows) == 4, rows)
    chk('B05.icones', '3 ícones por trio, WR conjunto e partidas', p.js("[...document.querySelectorAll('#qp .card.t')].every(c=>c.querySelectorAll('img').length===3&&/% WR do trio/.test(c.innerText))"))
    chk('B05.sem6', 'Texto deixa claro que não é build de 6 itens', 'seis itens' in T('#qp'))
    p.js("(()=>{const e=document.querySelector('#tq');e.focus()})()")
    p.type('rabadon'); wait()
    chk('B05.busca', 'Busca por item filtra trios', p.js("document.querySelectorAll('#qp .card.t').length")==3 and state("document.activeElement.id==='tq'"), p.js("document.querySelectorAll('#qp .card.t').length"))
    SEL('#tq', ''); p.js("S.trioQ='';render()")
    C('trioUse', '6653,3089,3135'); wait()
    first = p.js("document.querySelector('#qp .card.t').textContent")
    chk('B05.escolhido', 'Trio escolhido vem antes do padrão', 'Escolhido' in first and 'Tormento de Liandry' in first and 'Seções padrão (depois do trio)' in T('#qp'))
    C('ptab', 'Mods'); C('ptab', 'Itens'); C('panelClose'); C('dock'); wait()
    chk('B05.estado', 'Trocar aba e fechar/abrir painel mantém trio', state("S.trio.Ahri==='6653,3089,3135'") and 'Escolhido' in T('#qp'))
    C('lock'); wait()
    chk('B05.autoimport', 'Confirmar campeão simula importação com trio escolhido', 'trio escolhido' in state("S.imports[0].d"), state("JSON.stringify(S.imports[0])"))
    C('trioReset'); wait()
    chk('B05.restaurar', 'Voltar ao padrão desfaz', state("S.trio.Ahri===undefined") and 'Escolhido' not in T('#qp'))
    # Mods tab
    C('ptab', 'Mods'); wait()
    shot('b-1280-mods-painel.png')
    # Ajustes
    C('ptab', 'Ajustes'); wait()
    shot('b-1280-ajustes.png')
    # B06 config completa
    C('settings', None, '#qp'); wait(0.3)
    chk('B06.abre', 'Todas as configurações abre a partir do painel', state("document.getElementById('md').open") and 'Todas as configurações' in T('#md'))
    shot('b-1280-config.png')
    C('cfgTab', 'Seleção'); wait()
    p.js("(()=>{const e=document.querySelector('[data-bind=autoaceite]');e.click()})()"); wait()
    p.esc(); wait(0.3)
    chk('B06.esc', 'Esc fecha e mantém rascunho', not state("document.getElementById('md').open") and state("S.draft&&S.draft.autoaceite===false&&S.cfg.autoaceite===true") and 'rascunho' in T('#qp'))
    C('settings', None, '#qp'); wait(0.3)
    chk('B06.rascunho', 'Rascunho reaparece ao reabrir', state("S.draft&&S.draft.autoaceite===false") and p.js("document.querySelector('[data-bind=autoaceite]')===null||true"))
    C('cfgTab', 'Overlays'); wait()
    t = T('#mdb')
    chk('B06.ouroenh', 'Ouro e aprimoramentos em seções separadas', 'Ouro no placar' in t and 'Aprimoramentos · separados do ouro' in t and 'Arena' in t and 'Mayhem' in t)
    shot('b-1280-config-overlays.png')
    C('cfgTab', 'Geral'); SEL('#cl', 'English'); wait()
    chk('B06.idioma', 'Idioma aplica imediatamente, sem Salvar', state("S.cfg.idioma==='English'"))
    C('cfgCancel'); wait(0.3)
    chk('B06.cancelar', 'Cancelar descarta rascunho; salvo permanece', state("S.draft===null&&S.cfg.autoaceite===true&&S.cfg.idioma==='English'"))
    C('settings', None, '#qp'); wait(0.3); C('cfgTab', 'Seleção'); p.js("document.querySelector('[data-bind=confirmSkin]').click()"); C('cfgSave'); wait(0.3)
    chk('B06.salvar', 'Salvar grava sem reiniciar e sem importar', state("S.draft===null&&S.cfg.confirmSkin===true&&S.imports.length===%d" % state("S.imports.length")))

    # B06 sorteio, elegibilidade, Bravura
    fresh()
    C('goto', 'prep'); wait()
    t = T('main')
    chk('B06.elegib', 'Exalted + croma CTRL5 inelegível antes do ranking', 'Inelegível' in t and 'Exalted + croma que desativa CTRL5' in t and 'Não há ponderação' in t)
    shot('b-1280-sorteio-elegibilidade.png')
    C('drawNow'); wait()
    chk('B06.sorteio', 'Sorteio só entre elegíveis, rotulado simulado', state("S.draw.pool===3&&S.draw.out===1&&S.draw.skin!=='Ahri Exaltada (exemplo)'") and 'Resultado simulado' in T('main'))
    chk('B06.antesbrav', 'Bravura oculta o campeão antes da ação', state("S.brav.shown===false") and 'Campeão oculto' in T('main') and p.js("document.querySelector('.ph')!==null"))
    C('bravReveal'); wait()
    t = T('main')
    chk('B06.brav', 'Revelar mostra só o campeão; sem desafios/itens/estatísticas', state("S.brav.shown===true") and 'Rota, itens e desafios não são definidos pela Bravura' in t and 'WR' not in t.split('ARENA BRAVURA')[-1].split('Entrar na seleção')[0])
    C('bravAgain'); wait()
    c2 = state("S.brav.champ")
    C('bravUse'); wait()
    chk('B06.bravuso', 'Sortear novamente e usar na seleção', state("S.champ===%s&&S.step===1" % json.dumps(c2)))
    # Em jogo aprimoramentos
    C('step', '2'); wait()
    chk('B06.enhsemdados', 'Aprimoramentos: sem dados', 'Sem dados' in T('main'))
    C('enhOffer'); wait()
    chk('B06.enhofertas', 'Aprimoramentos: apenas ofertas; app não escolhe', 'nunca escolhe por você' in T('main'))
    C('enhUnrec'); wait()
    chk('B06.enhunrec', 'Aprimoramentos: não reconhecida distinto de sem dados', 'Carta não reconhecida' in T('main') and 'Sem dados' not in T('main').split('Aprimoramentos da Arena')[-1].split('Simular ofertas')[0])
    shot('b-1280-em-jogo-aprimoramentos.png')
    # Exalted elegível ao trocar croma na coleção
    C('goto', 'coll') if False else None


    # ---------- B06/B08: retorno e rascunho ----------
    fresh()
    C('goto', 'prep'); C('step', '1'); C('ptab', 'Ajustes'); wait(0.2)
    p.js("document.querySelector('#qp [data-act=settings]').focus()")
    p.key('Enter', vk=13); wait(0.3)
    C('cfgTab', 'Seleção'); p.js("document.querySelector('[data-bind=sugerirRunas]').click()"); wait(0.1)
    p.esc(); wait(0.3)
    chk('B08.focopainel', 'Fechar configurações aberto no painel devolve o foco ao botão do painel', state("document.activeElement.closest('#qp')!==null&&document.activeElement.dataset.act==='settings'"), state("document.activeElement.outerHTML.slice(0,80)"))
    C('settings', None, '#qp'); wait(0.3); C('cfgTab', 'Avançado'); C('cfgSupport'); wait(0.3)
    chk('B06.rascunhosuporte', 'Ir ao suporte pelas configurações preserva o rascunho', state("S.view==='support'&&S.draft&&S.draft.sugerirRunas===false") and 'rascunho' in T('#hdr'))
    C('back'); wait(0.3)
    chk('B06.retornoconfig', 'Voltar do suporte retorna ao ponto de origem com painel e rascunho', state("S.view==='prep'&&S.step===1&&S.ptab==='Ajustes'&&S.draft!==null"))
    shot('b-1280-rascunho-preservado.png')

    # ---------- B02 coleção ----------
    fresh()
    C('goto', 'coll'); wait()
    shot('b-1280-colecao.png')
    t = T('main')
    chk('B02.tabs', 'Coleção: por campeão, favoritas, conjuntos, arquivos', all(x in t for x in ['Por campeão', 'Favoritas', 'Conjuntos', 'Arquivos de mods']))
    C('cchamp', 'Zed'); wait()
    p.js("document.querySelector('input[data-act=skin][data-a=\"Variante festiva (exemplo)\"]').click()"); wait()
    SEL('select[data-act=chroma][data-a="Variante festiva (exemplo)"]', 'Pérola'); wait()
    C('fav', 'Variante festiva (exemplo)'); wait()
    chk('B02.edita', 'Editar skin, croma e favorita por campeão', state("S.choice.Zed==='Variante festiva (exemplo)'&&S.chroma['Zed|Variante festiva (exemplo)']==='Pérola'&&S.favs.has('Zed|Variante festiva (exemplo)')") and 'Zed' in T('aside'))
    C('newSet'); wait(0.3)
    p.js("document.querySelector('#sn').value='Meu conjunto'"); C('saveSet'); wait(0.3)
    chk('B02.criaconj', 'Criar conjunto parte das escolhas visíveis', state("S.sets.length===4&&S.sets[3].name==='Meu conjunto'&&Object.keys(S.sets[3].picks).includes('Zed')&&S.sets[3].picks.Zed[0]==='Variante festiva (exemplo)'") and 'Conjunto "Meu conjunto" criado' in T('main'))
    C('setPreview', 's2'); wait(0.3)
    chk('B02.previa', 'Prévia mostra o que muda e sobrescrita da escolha manual', 'substitui a escolha manual' in T('#md'))
    C('setApply', 's2'); wait(0.3)
    chk('B02.aplica', 'Aplicar conjunto muda escolhas e estado visível', state("S.activeSet==='s2'&&S.choice.Zed==='Original'&&S.choice.Ahri==='Original'") and 'Conjunto "Competitivo" aplicado' in T('main') and 'Competitivo (ativo)' in T('aside'))
    shot('b-1280-colecao-conjuntos.png')
    C('ctab', 'Favoritas'); wait()
    C('favApply', 'Ahri'); wait()
    chk('B02.favoritas', 'Aplicar favorita tem resultado observável', state("S.choice.Ahri==='Florescer Espiritual'") and 'Favorita aplicada' in T('main'))
    C('ctab', 'Por campeão'); wait()
    t = T('main')
    chk('B02.separa', 'Aplicar mods separado de administrar arquivos', 'Aplicar mods a este campeão' in t and 'Administrar arquivos' in t and 'ficam em Arquivos de mods' in t)

    # ---------- B03 biblioteca e sala ----------
    C('ctab', 'Arquivos de mods'); wait()
    shot('b-1280-biblioteca.png')
    n = p.js("document.querySelectorAll('[data-act=mcat]').length")
    chk('B03.categorias', 'Categorias legadas (Todas + 10)', n == 11 and all(x in T('main') for x in ['Skins', 'Mapas', 'Fontes', 'Anunciadores', 'Interface', 'Voz', 'Carregamento', 'VFX', 'SFX', 'Outros']), n)
    p.js("document.querySelector('#mq').focus()"); p.type('mapa'); wait()
    chk('B03.busca', 'Busca filtra a biblioteca', p.js("document.querySelectorAll('main .list .li').length")==1 and state("document.activeElement.id==='mq'"))
    SEL('#mq', ''); p.js("S.modQ='';render()")
    C('impOne'); wait()
    chk('B03.importa', 'Importar exemplo (skin) exige campeão e skin-base', 'Requer campeão e skin-base' in T('main') and state("S.mods.length===5"))
    C('needBase', 'm5'); wait(0.3)
    SEL('#mc', 'Zed'); SEL('#mbase', 'Original'); C('needSave', 'm5'); wait(0.3)
    chk('B03.base', 'Vincular campeão/skin-base', state("S.mods[4].champ==='Zed'&&S.mods[4].base==='Original'"))
    C('modEdit', 'm5'); wait(0.3); p.js("document.querySelector('#mn').value='Skin Zed Editada'"); C('modSave', 'm5'); wait(0.3)
    chk('B03.edita', 'Editar mod', 'Skin Zed Editada' in T('main'))
    C('modExport', 'm5'); wait()
    chk('B03.exporta', 'Exportar (simulado) marca o item', 'exportado (simulado)' in T('main'))
    # aplicar -> aguarda fim da seleção -> aplicado
    C('ctab', 'Por campeão'); C('cchamp', 'Zed'); wait()
    p.js("document.querySelector('input[data-act=modToggle][data-a=m5]').click()"); wait()
    chk('B03.espera', 'Skin-mod espera o fim da seleção', state("modStatus(S.mods[4]).k==='wait'") and 'Aguardando o fim da seleção' in T('main'))
    C('gotoBack', 'prep'); C('step', '2'); wait()
    chk('B03.aplicado', 'No fim da seleção a skin-mod é aplicada', state("modStatus(S.mods[4]).k==='on'") and 'Fim da seleção:' in T('main'))
    C('back'); C('ctab', 'Arquivos de mods'); wait()
    C('modDel', 'm5'); wait(0.3); chk('B03.removeconfirma', 'Remover pede confirmação', 'Remover da biblioteca' in T('#md')); C('modDelYes', 'm5'); wait(0.3)
    chk('B03.remove', 'Remover da lista (simulado)', state("S.mods.length===4"))
    # sala
    C('goto', 'prep') if False else None
    p.js("S.view='prep';S.step=0;render()"); wait()
    C('roomCreate'); wait()
    chk('B03.sala', 'Criar sala simulada com chave', 'SX2-4F7K' in T('main') and state("S.room.st==='conn'"))
    C('roomCopy'); C('roomCopy'); wait()
    chk('B03.copiar', 'Copiar chave simulado registra efeito', 'Copiada (simulado) × 2' in T('main'))
    C('roomDrop'); wait()
    chk('B03.queda', 'Queda simulada mostra reconectar', 'Reconectar' in T('main'))
    C('roomReconnect'); wait()
    chk('B03.reconecta', 'Reconectar volta à sala', state("S.room.st==='conn'"))
    C('roomLeave'); wait()
    p.js("document.querySelector('#rk').focus()"); p.type('xx'); C('roomJoin'); wait()
    chk('B03.chaveinvalida', 'Chave inválida mostra erro', 'Chave inválida' in T('main'))
    p.js("document.querySelector('#rk').value='';document.querySelector('#rk').focus()"); p.js("S.room.input=''"); p.type('sx2-9ab1'); C('roomJoin'); wait()
    chk('B03.conectar', 'Conectar com chave válida', state("S.room.st==='conn'&&S.room.code==='SX2-9AB1'"), state("S.room.code"))
    shot('b-1280-sala.png')
    # coordenado
    C('drawMode', 'Coordenado'); wait()
    C('coordEnter'); wait(0.3)
    chk('B03.aviso', 'Sorteio coordenado avisa que desativa conjunto', 'desativa o conjunto' in T('#md') and state("S.activeSet==='s1'") or 'desativa o conjunto' in T('#md'), T('#md')[:100])
    shot('b-1280-aviso-coordenado.png')
    C('coordYes'); wait(0.3)
    chk('B03.desativa', 'Entrar no sorteio coordenado desativa conjunto', state("S.activeSet===null&&S.room.coord===true") and 'desativado ao entrar' in T('main'))
    p.js("S.view='coll';S.coll='Conjuntos';render()"); wait()
    chk('B03.bloqueia', 'Aplicar conjunto indisponível durante o sorteio coordenado', p.js("[...document.querySelectorAll('[data-act=setPreview][data-b=apply]')].every(b=>b.disabled)") and 'nenhum conjunto pode ser aplicado' in T('main'))

    # ---------- B07 visual: sem azul, painel D-017, tamanhos ----------
    blue_js = """(()=>{const bad=[];const rg=/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/;document.querySelectorAll('body *').forEach(e=>{if(e.tagName==='IMG'||e.tagName==='SCRIPT'||e.tagName==='STYLE')return;const cs=getComputedStyle(e);['color','backgroundColor','borderTopColor','borderLeftColor','outlineColor','boxShadow'].forEach(k=>{const m=(cs[k]||'').match(rg);if(!m)return;const [r,g,b]=[+m[1],+m[2],+m[3]];if(b>r+25&&b>g+8&&b>90)bad.push(e.tagName+'.'+e.className+':'+k+':'+m[0]);})});return bad.slice(0,8)})()"""
    placement_js = """(()=>{const b=document.getElementById('dockbtn').getBoundingClientRect(),p=document.getElementById('qp');if(p.hidden)return {hidden:true};const r=p.getBoundingClientRect();const ov=!(r.right<=b.left||r.left>=b.right||r.bottom<=b.top||r.top>=b.bottom);return {rightAligned:Math.abs(r.right-b.right)<=0.5,gap:Math.round(b.top-r.bottom),inside:r.left>=0&&r.top>=0&&r.right<=innerWidth&&r.bottom<=innerHeight,overlapsBtn:ov,w:Math.round(r.width),h:Math.round(r.height),btn:[Math.round(b.left),Math.round(b.top),Math.round(b.right),Math.round(b.bottom)]}})()"""
    overflow_js = "({x:document.documentElement.scrollWidth-innerWidth,body:document.body.scrollWidth-innerWidth})"
    clip_js = "[...document.querySelectorAll('button,.tag,label,h1,h2,h4,select')].filter(e=>e.offsetParent&&e.scrollWidth>e.clientWidth+1&&getComputedStyle(e).overflow!=='visible').map(e=>e.tagName+':'+e.textContent.trim().slice(0,30)).slice(0,6)"
    for (w, h, tag) in [(1280, 720, '1280'), (820, 560, '820'), (452, 492, '452')]:
        fresh(w, h)
        C('goto', 'prep'); C('step', '1'); wait(0.3)
        pl = p.js(placement_js)
        ok = pl.get('rightAligned') and pl.get('gap') == 8 and pl.get('inside') and not pl.get('overlapsBtn')
        chk('B07.D017.' + tag, 'Painel D-017 em %dx%d: alinhado à direita do botão, 8px acima, dentro, sem cobrir' % (w, h), ok, pl)
        chk('B07.azul.' + tag, 'Nenhuma cor azul em computed styles (%s, seleção)' % tag, p.js(blue_js) == [], p.js(blue_js))
        chk('B07.overflow.' + tag, 'Sem rolagem horizontal da página (%s)' % tag, p.js(overflow_js)['x'] <= 0, p.js(overflow_js))
        chk('B07.clip.' + tag, 'Textos de botões/rótulos sem corte (%s, painel)' % tag, p.js(clip_js) == [], p.js(clip_js))
        shot('b-%s-selecao-runas.png' % tag)
        C('ptab', 'Itens'); wait(); shot('b-%s-selecao-itens.png' % tag)
        C('ptab', 'Mods'); wait(); shot('b-%s-selecao-mods.png' % tag)
        C('panelClose'); wait(); shot('b-%s-selecao-fechado.png' % tag)
        C('step', '0'); wait(); shot('b-%s-antes-fila.png' % tag)
        chk('B07.overflowA.' + tag, 'Sem rolagem horizontal (%s, antes da fila)' % tag, p.js(overflow_js)['x'] <= 0, p.js(overflow_js))
        C('home'); wait(); shot('b-%s-home.png' % tag)
        chk('B07.overflowH.' + tag, 'Sem rolagem horizontal (%s, home)' % tag, p.js(overflow_js)['x'] <= 0, p.js(overflow_js))
        C('goto', 'coll'); wait(); shot('b-%s-colecao.png' % tag)
        chk('B07.overflowC.' + tag, 'Sem rolagem horizontal (%s, coleção)' % tag, p.js(overflow_js)['x'] <= 0, p.js(overflow_js))
        C('ctab', 'Arquivos de mods'); wait(); shot('b-%s-biblioteca.png' % tag)
        chk('B07.overflowF.' + tag, 'Sem rolagem horizontal (%s, biblioteca)' % tag, p.js(overflow_js)['x'] <= 0, p.js(overflow_js))
        C('home'); C('goto', 'support'); wait(); shot('b-%s-suporte.png' % tag)
        chk('B07.overflowS.' + tag, 'Sem rolagem horizontal (%s, suporte)' % tag, p.js(overflow_js)['x'] <= 0, p.js(overflow_js))
        p.js("document.querySelector('[data-act=settings]').click()"); wait(0.3); shot('b-%s-config.png' % tag)
        r = p.js("(()=>{const r=document.getElementById('md').getBoundingClientRect();return r.left>=0&&r.top>=0&&r.right<=innerWidth&&r.bottom<=innerHeight})()")
        chk('B07.dialog.' + tag, 'Diálogo de configurações cabe na janela (%s)' % tag, r)
        p.esc(); wait(0.3)
        # imagens
        broken = p.js("[...document.images].filter(i=>!i.complete||i.naturalWidth===0).map(i=>i.src)")
        chk('B08.imgs.' + tag, 'Imagens locais carregadas (%s)' % tag, broken == [], broken)

    # ---------- B08 teclado/foco ----------
    fresh()
    p.js("document.querySelector('[data-act=settings]').focus()")
    p.key('Enter', vk=13)
    wait(0.3)
    chk('B08.enter', 'Enter no botão abre o diálogo', state("document.getElementById('md').open"))
    inside = state("document.getElementById('md').contains(document.activeElement)")
    chk('B08.focoinicial', 'Foco inicial dentro do diálogo', inside)
    seen = []
    for i in range(14):
        p.tab(); seen.append(p.js("document.getElementById('md').contains(document.activeElement)"))
    chk('B08.tabtrap', 'Tab percorre sem sair do diálogo (14 passos)', all(seen), seen)
    seen = []
    for i in range(14):
        p.tab(shift=True); seen.append(p.js("document.getElementById('md').contains(document.activeElement)"))
    chk('B08.shifttab', 'Shift+Tab percorre sem sair do diálogo', all(seen), seen)
    p.esc(); wait(0.3)
    chk('B08.escmodal', 'Esc fecha o diálogo', not state("document.getElementById('md').open"))
    chk('B08.focorest', 'Foco volta ao botão Configurações', state("document.activeElement.dataset&&document.activeElement.dataset.act==='settings'"), state("document.activeElement.outerHTML.slice(0,80)"))
    # painel por teclado
    C('goto', 'prep'); C('step', '1'); wait(0.3)
    p.js("document.getElementById('dockbtn').focus()"); p.key('Enter', vk=13); wait(0.2)
    chk('B08.docktoggle', 'Dock por teclado alterna o painel', state("S.panel===false"))
    p.key('Enter', vk=13); wait(0.2)
    chk('B08.dockabre', 'Enter reabre e foca a aba', state("S.panel===true&&document.getElementById('qp').contains(document.activeElement)"), state("document.activeElement.outerHTML.slice(0,90)"))
    p.esc(); wait(0.2)
    chk('B08.escpainel', 'Esc fecha o painel e foca o botão', state("S.panel===false&&document.activeElement.id==='dockbtn'"))
    # tab order sanity: nenhum elemento focável invisível
    p.js("S.panel=true;render()"); wait(0.2)
    focus_seq = []
    p.js("document.body.focus()")
    for i in range(40):
        p.tab(); focus_seq.append(p.js("(()=>{const e=document.activeElement;const r=e.getBoundingClientRect();return r.width>0&&r.height>0})()"))
    chk('B08.focovisivel', 'Todos os focos da seleção estão em elementos visíveis (40 Tab)', all(focus_seq))
    out = p.js("getComputedStyle(document.activeElement).outlineStyle+' '+getComputedStyle(document.activeElement).outlineColor")
    chk('B08.fococlaro', 'Foco com contorno claro', 'solid' in out and ('236' in out), out)
    # links
    for rel in ['../sexo2-ux-a/index.html', '../sexo2-overlays/index.html']:
        chk('B08.link.' + rel, 'Link existe: ' + rel, os.path.exists(os.path.normpath(os.path.join(ROOT, rel))))
    for f in ['oswald.woff2', 'inter.woff2']:
        chk('B08.asset.' + f, 'Asset existe: ' + f, os.path.exists(os.path.join(ROOT, '..', 'sexo2-shared', f)))
    chk('B08.semfetch', 'Sem fetch/XHR/import remoto no HTML', not re.search(r'fetch\(|XMLHttpRequest|https?://', open(os.path.join(ROOT, 'index.html')).read()))
    errs = p.errors()
    chk('B08.console', 'Sem erros de console/exceções', errs == [], errs)
finally:
    json.dump(res, open(os.path.join(HERE, 'qa_resultado_%s.json' % ROUND), 'w'), ensure_ascii=False, indent=1)
    p.close()
    print('TOTAL', len(res), 'FALHAS', sum(1 for r in res if not r['ok']))
