"""Monta `apresentacao.html`: a segunda rodada de ícones do SEXO2, com o galo como núcleo.

    python design/propostas/icone/galo-r2/apresentacao.py

Reaproveita as simulações do Windows da primeira rodada (`../redesign-2.0/apresentacao.py`), trocando só os
arquivos de ícone. Um arquivo só, com SVG, PNG e fontes embutidos. Nada aqui altera `assets/` (decisão pendente).
Requer cairosvg (só para gerar esta página; não faz parte do app).
"""

import importlib.util
from pathlib import Path

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("rodada1", HERE.parent / "redesign-2.0" / "apresentacao.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def svg_file(letter, small=False):
    if letter == "atual":
        return base.ATUAL
    return HERE / "svg" / f"{letter}-{'pequeno' if small else 'icone'}.svg"


base.svg_file = svg_file  # as simulações chamam esta função em tempo de execução
img, vector, taskbar, scenes = base.img, base.vector, base.taskbar, base.scenes
GUIDE = base.GUIDE


def anatomia(letter, notas):
    """O ícone com chamadas numeradas sobre as partes do galo."""
    inner = svg_file(letter).read_text(encoding="utf-8")
    inner = inner[inner.index(">", inner.index("<svg")) + 1 : inner.rindex("</svg>")]
    inner = "".join(line for line in inner.splitlines() if not line.startswith("<title"))
    marks = ""
    for i, (x, y, lx, ly) in enumerate(notas, 1):
        marks += (
            f'<path d="M{lx} {ly}L{x} {y}" stroke="{GUIDE}" stroke-width="1"/><circle cx="{x}" cy="{y}" r="2.4" fill="{GUIDE}"/>'
            f'<circle cx="{lx}" cy="{ly}" r="7" fill="#0d0e10" stroke="{GUIDE}"/>'
            f'<text x="{lx}" y="{ly + 3.4}" fill="{GUIDE}" font-family="Inter" font-size="9" font-weight="700" text-anchor="middle">{i}</text>'
        )
    return f'<svg viewBox="0 0 256 256" width="300" height="300" class="cons" role="img" aria-label="Anatomia">{inner}{marks}</svg>'


PROPOSTAS = [
    dict(
        l="g1",
        nome="Galo busto",
        territorio="Território 1 · Evolução com preservação de equity",
        conceito="O galo do ícone atual, que você já reconhece, redesenhado como retrato: crista de pontas, bico em cunha, a fresta que corta o rosto, a barbela vermelha e o pescoço de penas. O mesmo galo, com régua.",
        galinacidade=[
            "<b>Crista de três pontas</b> com a do meio mais alta: o traço mais antigo do ícone.",
            "<b>Bico em cunha</b> apontado para a direita, a direção do ícone atual.",
            "<b>A fresta</b>: a faixa escura do ícone atual passa a ser a linha da boca (o bico aberto), em vez de um tapa-olho.",
            "<b>Barbela vermelha</b>, o único acento, agora maior e presa ao bico.",
            "<b>Pescoço de penas</b> em dentes e corte do retrato embaixo, que dá escala e evita a base solta.",
        ],
        raciocinio=[
            "A silhueta é o desenho: branco sobre grafite, sem fundo interno, para valer em 16 px e em uma cor.",
            "O corte do busto na borda inferior troca a forma recortada de antes (que parecia uma máscara) por um retrato com peso.",
            "A fresta passou do meio da cabeça para o bico: o que era um visor vira boca, e o galo deixa de parecer de óculos.",
            "Só três cores do app (grafite, branco, um vermelho). Sem grade geométrica rígida: a faceta é o estilo, como no original.",
        ],
        cores=[
            ("Grafite", base.INK, "fundo"),
            ("Branco do app", base.PAPER, "cabeça e pescoço"),
            ("Vermelho", base.RED, "só a barbela"),
        ],
        notas=[(103, 38, 40, 24), (231, 147, 238, 118), (160, 152, 200, 232), (175, 192, 232, 232), (58, 190, 22, 232)],
        legenda=["Crista", "Bico", "Fresta (boca)", "Barbela", "Pescoço de penas"],
        fortes=[
            "Máxima continuidade: quem conhece o ícone atual reconhece na hora.",
            "A melhor leitura em 16 e 24 px das três: uma silhueta clara, branca sobre grafite.",
            "Funciona em uma cor, invertida, desfocada e girada.",
            "Já está no estilo do app: facetas, ângulos vivos, quadrado.",
        ],
        riscos=[
            "Bico longo e crista de pontas lembram raposa ou lobo em tamanho pequeno (o olho resolveria; foi testado e fica como opção).",
            "É o mais próximo do clichê de mascote “gamer” agressivo, embora sem olhar nem sorriso.",
            "É o menos novo: a evolução é de acabamento, não de conceito.",
            "Ainda tem arestas desenhadas a mão, de até 3° fora do ângulo limpo (refino depois da escolha).",
        ],
        testes=[
            ("16 px", "forte: crista, bico e barbela legíveis"),
            ("32 / 64 / 256 px", "ok em todos"),
            ("Uma cor", "ok: silhueta de galo inconfundível"),
            ("Invertido", "ok"),
            ("Desfoque", "mancha de galo com ponta vermelha"),
            ("180° / espelho", "sem leitura estranha"),
        ],
    ),
    dict(
        l="g2",
        nome="Galo plano",
        territorio="Território 2 · Abstração sofisticada",
        conceito="O galo como uma dobradura de planos: crista e barbela vermelhas como no animal, um plano branco (crânio e bico), outro cinza (maxilar), separados pela fresta. Sem pescoço: só a cabeça, como um objeto.",
        galinacidade=[
            "<b>Crista vermelha</b> de três pontas sobre o crânio, como a do galo de verdade.",
            "<b>Bico</b> em cunha, formado pelo plano branco que avança.",
            "<b>A fresta</b> do ícone atual vira o vão entre os dois planos: a divisão que atravessa a cabeça.",
            "<b>Barbela vermelha</b> pendurada no plano de baixo e <b>olho</b> em cunha escura.",
            "A galinacidade está na <b>estrutura</b> (crista, bico, barbela), não em contorno de pena.",
        ],
        raciocinio=[
            "Dois planos e uma fresta é o mesmo gesto do Duelo da primeira rodada, agora aplicado a uma cabeça que se reconhece.",
            "A cor segue a natureza: o vermelho só onde o galo é vermelho (crista e barbela); o resto, os dois tons do app.",
            "Sem pescoço, a cabeça flutua e o ícone ganha ar de objeto de marca, menos de mascote.",
            "Cinza (o segundo texto do app) só no plano de baixo, para a leitura de volume sem sombra nem degradê.",
        ],
        cores=[
            ("Grafite", base.INK, "fundo"),
            ("Branco do app", base.PAPER, "crânio e bico"),
            ("Cinza do app", "#a4a9b0", "maxilar"),
            ("Vermelho", base.RED, "crista e barbela"),
        ],
        notas=[
            (89, 30, 40, 24),
            (125, 126, 22, 90),
            (220, 154, 238, 118),
            (137, 156, 200, 232),
            (172, 186, 232, 232),
            (94, 197, 22, 232),
        ],
        legenda=["Crista", "Olho", "Bico", "Fresta entre os planos", "Barbela", "Plano do maxilar"],
        fortes=[
            "O equilíbrio mais sofisticado e contemporâneo: o galo sem ser desenho.",
            "Leitura imediata de galo pela cor da crista e da barbela.",
            "Menos agressivo que o busto e menos infantil que um mascote.",
            "Prolonga a linguagem de planos e fresta da rodada anterior.",
        ],
        riscos=[
            "Muda o DNA mais visível: a crista deixa de ser branca; o equity fica no gesto, não na cor.",
            "O plano cinza se confunde com o fundo em 16 px (por isso o corte pequeno alarga a fresta).",
            "Pode parecer papagaio ou pássaro qualquer se perder a crista de três pontas.",
            "Quatro cores contra três dos outros; o cinza pede disciplina.",
        ],
        testes=[
            ("16 px", "médio: crista e bico ok, maxilar embaça"),
            ("32 / 64 / 256 px", "ok; melhor a partir de 32"),
            ("Uma cor", "ok: dois planos pela fresta"),
            ("Invertido", "ok"),
            ("Desfoque", "crista vermelha e massa branca; maxilar some"),
            ("180° / espelho", "sem leitura estranha"),
        ],
    ),
    dict(
        l="g3",
        nome="Galo-2",
        territorio="Território 3 · Galo-signo / emblema",
        conceito="O 2 é o galo. A curva de cima é a cabeça (crista, olho, bico, barbela); a diagonal e a base são o pescoço e o corpo. Lê-se como número e como animal numa forma só, o nome do produto virado em marca.",
        galinacidade=[
            "<b>Crista vermelha</b> sobre o alto da cabeça, em pontas.",
            "<b>Bico</b> em cunha à esquerda e <b>barbela</b> vermelha logo abaixo.",
            "<b>Olho</b> em cunha escura, que ancora a cabeça.",
            "<b>Pescoço arqueado</b>: a curva do 2 é o pescoço do galo cantando.",
            "É o mais abstrato em contorno e o mais explícito em ideia: o galo está no gesto do corpo.",
        ],
        raciocinio=[
            "O produto se chama SEXO2: o número já é a marca. Fazer o 2 virar galo cola o nome ao animal sem explicação em texto.",
            "A forma é sólida e pesada, de emblema: bem institucional, sem miúdos de pena.",
            "A cabeça é a curva do 2; a crista nasce no topo dela, que é onde a crista fica no galo.",
            "O vermelho marca as duas partes que dizem galo (crista e barbela); o resto é o branco do app.",
        ],
        cores=[
            ("Grafite", base.INK, "fundo"),
            ("Branco do app", base.PAPER, "o 2 / o galo"),
            ("Vermelho", base.RED, "crista e barbela"),
        ],
        notas=[(118, 24, 60, 14), (94, 113, 20, 96), (31, 141, 16, 176), (90, 179, 34, 228), (154, 51, 236, 40)],
        legenda=["Crista", "Olho", "Bico", "Barbela", "Pescoço: a curva do 2"],
        fortes=[
            "O mais autoral e memorável: não há outro galo-2.",
            "Lê como emblema institucional, com um nome que se vê.",
            "Em uma cor e invertido, o 2 sozinho já segura.",
            "Casa o nome do produto com o galo, que era o que faltava dizer.",
        ],
        riscos=[
            "O mais fraco em 16 px: crista, olho e barbela se perdem e fica um 2 branco com pontos vermelhos.",
            "Corre o maior risco de perder a galinacidade: sem a crista, parece cisne ou ganso.",
            "Prende o ícone ao número 2 (na 3.0 pede revisão).",
            "Exige um segundo olhar: o galo aparece depois do 2.",
        ],
        testes=[
            ("16 px", "fraco: vira um 2 com pontos vermelhos"),
            ("32 / 64 / 256 px", "ok a partir de 32"),
            ("Uma cor", "ok: 2 com crista"),
            ("Invertido", "ok"),
            ("Desfoque", "um 2 com mancha vermelha"),
            ("180° / espelho", "180° vira um gancho; espelhado, um 5 com bico"),
        ],
    ),
]

EXTRA_CSS = """
.anat{display:grid;grid-template-columns:300px 1fr;gap:20px;align-items:start}.anat ol{margin:0;padding-left:20px}.anat li{margin:0 0 4px;color:var(--fg2)}
@media(max-width:760px){.anat{grid-template-columns:1fr}}
.q td:first-child{width:34%;color:var(--fg2)}.pill{display:inline-block;border:1px solid var(--line);padding:1px 8px;font:600 11px Inter;margin-right:6px}.pill.on{border-color:var(--red);color:var(--fg)}
"""


def page():
    P = []
    P.append(
        "<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
    )
    P.append(
        "<title>SEXO2 · o galo, segunda rodada</title><style>"
        + base.font_css()
        + base.CSS
        + EXTRA_CSS
        + "</style></head><body>"
    )
    P.append(
        "<nav class='top'><a href='#ctx'>Equity</a><a href='#g1'>1 · Galo busto</a><a href='#g2'>2 · Galo plano</a><a href='#g3'>3 · Galo-2</a><a href='#comp'>Comparação</a><a href='#rec'>Recomendação</a></nav><div class='wrap'>"
    )
    P.append(
        "<h1>SEXO2 · o galo como núcleo</h1><p class='lead'>Segunda rodada de exploração do ícone: três territórios criativos, todos com a galinacidade como ativo central. Nada foi aplicado: <code>assets/sexo2.svg</code> continua como está.</p>"
    )
    P.append(
        "<div class='banner'><b>Material experimental</b> · só na branch <code>gunderfrank</code> · pasta <code>design/propostas/icone/galo-r2/</code>. As simulações do Windows são desenhadas; os ícones aparecem rasterizados no tamanho real.</div>"
    )

    P.append("<h2 id='ctx'>O equity do galo</h2><div class='card diag'>")
    P.append(
        f"<div>{img('atual', 192)}<p class='muted' style='margin-top:6px'>Ícone atual (D-123)</p><div style='display:flex;gap:10px;align-items:flex-end'>{img('atual', 48)}{img('atual', 32)}{img('atual', 24)}{img('atual', 16)}</div></div>"
    )
    P.append(
        "<div><h4>O que o galo atual tem de valioso</h4><ul class='t'>"
        "<li><b>Crista de pontas</b> sobre uma cabeça facetada: a primeira coisa que se reconhece.</li>"
        "<li><b>Bico em cunha</b> para a direita e <b>barbela vermelha</b>: o único acento.</li>"
        "<li><b>A fresta</b> que atravessa o rosto: o traço mais próprio do ícone.</li>"
        "<li><b>Grafite, branco e um vermelho</b>, no formato quadrado do app.</li></ul>"
        "<h4>O que atrapalha</h4><ul class='t'>"
        "<li>A fresta lê como tapa-olho ou visor, que é o que dá o ar de “gamer”.</li>"
        "<li>O desenho é irregular, sem ângulos limpos, cortado de forma solta embaixo.</li>"
        "<li>A barbela some abaixo de 32 px.</li></ul>"
        "<h4>Duas notas de contexto</h4><ul class='t'>"
        "<li>O “Galo” que a decisão D-112 tirou do app era o escudo de um clube de futebol, marca de terceiros. Aqui o galo é <b>de autoria própria</b>, desenhado do zero; nenhum traço do escudo foi usado.</li>"
        "<li>A D-112 diz que o Galo não tem mais papel de marca. Escolher qualquer um destes territórios <b>exige revisar a D-112</b> (pendente da sua aprovação; não alterei o registro).</li></ul></div></div>"
    )
    P.append(
        "<p class='muted'>Método: skill de logo (Redesign): diagnóstico, auditoria de patrimônio, conceitos de uma frase, três territórios, SVG, renderização, refino, auditoria e testes. Não há garantia de registro de marca; recomenda-se busca de anterioridade.</p>"
    )

    for p in PROPOSTAS:
        l = p["l"]
        P.append(f"<h2 id='{l}'>{p['nome']}</h2><p class='muted'>{p['territorio']}</p>")
        P.append(
            f"<div class='hero'><div class='big'>{vector(l, 320)}</div><div><h4 style='margin-top:0'>Conceito central</h4><p class='lead' style='font-size:17px'>{p['conceito']}</p><h4>Galinacidade preservada</h4><ul class='t'>"
            + "".join(f"<li>{x}</li>" for x in p["galinacidade"])
            + "</ul></div></div>"
        )
        P.append(
            "<div class='two' style='margin-top:20px'><div class='card'><h4 style='margin-top:0'>Raciocínio visual</h4><ul class='t'>"
            + "".join(f"<li>{x}</li>" for x in p["raciocinio"])
            + "</ul>"
        )
        P.append(
            "<h4>Cores</h4><div class='sw'>"
            + "".join(
                f"<div><i style='background:{c}'></i><span><b>{n}</b> {c}<br>{u}</span></div>" for n, c, u in p["cores"]
            )
            + "</div></div>"
        )
        P.append(
            "<div class='card'><h4 style='margin-top:0'>Anatomia</h4><div class='anat'>"
            + anatomia(l, p["notas"])
            + "<ol>"
            + "".join(f"<li>{x}</li>" for x in p["legenda"])
            + "</ol></div></div></div>"
        )
        P.append(
            "<h4>Leitura em tamanhos pequenos (16 e 24 px usam o corte pequeno)</h4><div class='ladder'>"
            + "".join(
                f"<figure>{img(l, s)}<figcaption>{s} px</figcaption></figure>" for s in (16, 24, 32, 64, 128, 256)
            )
            + "</div>"
        )
        P.append(
            "<div class='ladder light' style='margin-top:10px'>"
            + "".join(
                f"<figure>{img(l, s)}<figcaption>{s} px sobre claro</figcaption></figure>" for s in (16, 24, 32, 64)
            )
            + "</div>"
        )
        mono = base.b64((HERE / "svg" / f"{l}-simbolo.svg").read_bytes())
        P.append(
            "<div class='ladder light' style='margin-top:10px;align-items:center'>"
            f"<figure><img src='data:image/svg+xml;base64,{mono}' width='96' height='96' alt=''><figcaption>uma cor, sobre claro</figcaption></figure>"
            f"<figure style='background:#000;padding:0'><img src='data:image/svg+xml;base64,{mono}' width='96' height='96' alt='' style='filter:invert(1)'><figcaption style='color:#aaa;background:#e9e9e9'>uma cor, invertida</figcaption></figure></div>"
        )
        P.append(
            "<h4>Testes do skill</h4><table>"
            + "".join(f"<tr><th>{a}</th><td>{b}</td></tr>" for a, b in p["testes"])
            + "</table>"
        )
        P.append("<h4>Aplicações simuladas no Windows</h4>" + scenes(l))
        P.append(
            "<div class='two' style='margin-top:16px'><div class='card'><h4 style='margin-top:0'>Pontos fortes</h4><ul class='t good'>"
            + "".join(f"<li>{x}</li>" for x in p["fortes"])
            + "</ul></div>"
        )
        P.append(
            "<div class='card'><h4 style='margin-top:0'>Riscos e limitações</h4><ul class='t bad'>"
            + "".join(f"<li>{x}</li>" for x in p["riscos"])
            + "</ul></div></div>"
        )

    P.append(
        "<h2 id='comp'>Comparação dos três caminhos</h2><p class='lead'>O ícone atual e os três territórios, no mesmo tamanho, sobre escuro e claro e na barra de tarefas.</p>"
    )
    row = lambda cls, sizes: "".join(
        f"<div class='ladder {cls}' style='margin-bottom:10px'>"
        + "".join(
            f"<figure>{img(k, s)}<figcaption>{n} · {s}</figcaption></figure>"
            for k, n in (("atual", "atual"), ("g1", "1"), ("g2", "2"), ("g3", "3"))
        )
        + "</div>"
        for s in sizes
    )
    P.append("<h4>Sobre escuro</h4>" + row("", (16, 32, 64, 128)) + "<h4>Sobre claro</h4>" + row("light", (24, 48)))
    P.append("<h4>Na barra de tarefas</h4><div class='sc wide'>")
    for k, n in (("atual", "Atual"), ("g1", "1 · Galo busto"), ("g2", "2 · Galo plano"), ("g3", "3 · Galo-2")):
        P.append(f"<p class='muted' style='margin:8px 0 2px'>{n}</p>{taskbar(k)}")
    P.append("</div>")
    P.append(
        "<h4>As perguntas de um especialista</h4><table class='q'><tr><th>Pergunta</th><th>1 · Galo busto</th><th>2 · Galo plano</th><th>3 · Galo-2</th></tr>"
        "<tr><td>O que do galo se preserva</td><td>Quase tudo: crista de pontas, bico, fresta, barbela, pescoço, o desenho facetado</td><td>Crista, bico, barbela e a fresta como divisão de planos; sai a crista branca e o contorno de pena</td><td>Crista, bico, barbela e o pescoço arqueado; sai o rosto como retrato</td></tr>"
        "<tr><td>Preservação de equity</td><td><b>Máxima</b></td><td>Média: o gesto, não o desenho</td><td>Baixa a média: só os sinais (crista, bico)</td></tr>"
        "<tr><td>Como ícone de aplicativo</td><td><b>O melhor</b>: silhueta alta e contrastada</td><td>Bom: precisa do corte pequeno</td><td>O mais fraco: depende de tamanho</td></tr>"
        "<tr><td>Leitura em tamanho pequeno</td><td><b>1º</b></td><td>2º</td><td>3º (em 16 px é um 2 com pontos)</td></tr>"
        "<tr><td>Risco de clichê</td><td>Médio-alto: mascote/gamer; pode lembrar raposa</td><td>Médio: dobradura, papagaio</td><td>Baixo em clichê; o risco é de pegadinha</td></tr>"
        "<tr><td>Risco de perder a galinacidade</td><td>Baixo</td><td>Médio</td><td><b>Alto</b>: sem a crista é um cisne/2</td></tr>"
        "<tr><td>Equilíbrio originalidade, reconhecimento e sofisticação</td><td>Reconhecimento alto, originalidade baixa</td><td><b>O mais equilibrado</b></td><td>Originalidade máxima, reconhecimento arriscado</td></tr></table>"
    )

    P.append(
        "<h2 id='rec'>Recomendação</h2><div class='card' style='border-color:var(--red)'>"
        "<p class='lead' style='color:var(--fg)'><span class='pill on'>Recomendação</span> <b>1 · Galo busto</b>, como o ícone do app.</p>"
        "<ul class='t'><li><b>Mais forte em preservação de equity:</b> 1 · Galo busto (é o galo atual, com acabamento).</li>"
        "<li><b>Mais forte como app icon:</b> 1 · Galo busto (16 e 24 px mais claros, uma cor e invertido sem perda).</li>"
        "<li><b>Mais forte como identidade:</b> 3 · Galo-2 (o mais autoral e memorável, mas só funciona de 32 px para cima).</li>"
        "<li><b>Mais equilibrado e contemporâneo:</b> 2 · Galo plano (a opção se você priorizar sofisticação sobre continuidade).</li></ul>"
        "<p>Meu caminho: ficar com o <b>Galo busto</b> no app e refiná-lo depois da sua aprovação (ângulos limpos, um olho opcional que tira o risco de raposa), e guardar o <b>Galo-2</b> como marca institucional em tamanhos grandes (abertura animada, instalador, README), onde ele tem espaço para ser lido.</p>"
        "<p class='muted'>Se você preferir um só ícone para tudo, o 2 · Galo plano é a segunda escolha. Nada disto foi implementado; as três opções ficam apenas em <code>design/propostas/icone/galo-r2/</code>.</p></div>"
    )
    P.append(
        "<h2>O que acontece depois da sua avaliação</h2><div class='card'><ol class='t'><li>Você escolhe um território (ou combina elementos) e pede ajustes.</li><li>Refino final: ângulos, proporções e corte pequeno.</li><li>Só então a revisão da D-112 e a integração (<code>docs/ICONE-NOVO.md</code>), com testes e conferência no Windows real.</li></ol></div>"
    )
    P.append("</div></body></html>")
    return "".join(P)


if __name__ == "__main__":
    out = HERE / "apresentacao.html"
    out.write_text(page(), encoding="utf-8")
    print(f"escrito: {out} ({out.stat().st_size // 1024} KB)")
