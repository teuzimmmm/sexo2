"""Gera os SVG de cada variante e ../rodada3.html a partir de variantes.py."""
import html
from pathlib import Path

from variantes import V

AQUI = Path(__file__).resolve().parent
TOP = {"L7": "Recomendação 1", "R1": "Recomendação 2"}


def svg(inner, size=256):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 256 256">{inner}</svg>')


def card(k, nome, texto, inner):
    tag = f"<em>{TOP[k]}</em>" if k in TOP else ""

    def s(n):
        return svg(inner, n)

    return (f'<div class="card{" top" if k in TOP else ""}">{tag}{s(150)}<b>{k} · {html.escape(nome)}</b>'
            f'<span>{html.escape(texto)}</span>'
            f'<div class="sizes">{s(48)}{s(32)}{s(16)}</div>'
            f'<div class="light">{s(32)}{s(24)}{s(16)}</div>'
            f'<div class="blur">{s(48)}{s(32)}{s(16)}</div></div>')


def secao(fam):
    return "".join(card(k, v[0], v[2], v[3]) for k, v in V.items() if v[1] == fam)


for k, v in V.items():
    (AQUI / f"{k}.svg").write_text(svg(v[3]) + "\n", encoding="utf-8")

PAGE = """<!doctype html>
<html lang="pt-BR">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Portfólio de ícones · rodada 3</title>
<style>
@font-face{font-family:Oswald;src:url(../../fonts/oswald-latin-wght-normal.woff2) format("woff2");font-weight:200 700}
@font-face{font-family:Inter;src:url(../../fonts/inter-latin-wght-normal.woff2) format("woff2");font-weight:100 900}
*{box-sizing:border-box;margin:0}
body{background:#0d0e10;color:#ececec;font:14px/1.5 Inter,sans-serif;padding:24px 16px 48px;max-width:1200px;margin:auto}
h1,h2{font-family:Oswald;font-weight:600;text-transform:uppercase;letter-spacing:.02em}
h1{font-size:26px}h2{font-size:18px;margin:26px 0 4px}
p,li{color:#a4a9b0;font-size:13px}.lead{margin:8px 0 14px;max-width:800px}
ul{margin:6px 0 0 18px}
.row{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;margin-top:10px}
.card{position:relative;background:#15171a;border:1px solid #2a2d32;padding:14px;display:flex;flex-direction:column;align-items:center;gap:8px}
.card.top{border-color:#d2412f}
.card em{position:absolute;top:6px;left:8px;font:600 11px Oswald;text-transform:uppercase;letter-spacing:.04em;color:#d2412f;font-style:normal}
.card b{font:600 15px Oswald;text-transform:uppercase;letter-spacing:.03em}
.card span{font-size:12px;color:#a4a9b0;text-align:center}
.sizes{display:flex;gap:8px;align-items:flex-end}
.light{background:#f3f3f3;border-radius:6px;padding:6px 10px;display:flex;gap:8px;align-items:center}
.blur{display:flex;gap:8px;align-items:flex-end;filter:blur(1.1px)}
</style>
<h1>Portfólio de ícones · rodada 3</h1>
<p class="lead">Um só sistema de marca: galo de perfil virado para a direita, com a mesma crista, o mesmo bico e o mesmo olho em lâmina, só três cores (grafite, branco e o vermelho do olho) e o mesmo desenho em todos os tamanhos. As variantes mudam o peso da linha, o fundo e o contorno. Cada cartão mostra 150, 48, 32 e 16 px, uma barra clara (32, 24 e 16 px) e uma versão desfocada (48, 32 e 16 px) para testar a leitura de longe. Nada aqui está aprovado; nenhum arquivo de <code>assets/</code> foi trocado.</p>
<h2>O que mudou desde a rodada 2</h2>
<ul>
<li>Sério e ameaçador: sobrancelha reta que desce sobre o olho, olho em lâmina, vértices vivos (sem cantos arredondados), linha de 20 a 26 unidades e um só detalhe interno.</li>
<li>Mais simples: crista de três pontas (duas em L7), sem pescoço e sem penas; a barbela só aparece em L8.</li>
<li>Sem azul e sem letras: a marca não depende do nome, vale para SEXO2 e SEXO3.</li>
</ul>
<h2>Traço, sério</h2>
<div class="row">@@L@@</div>
<h2>Angular, simples</h2>
<div class="row">@@R@@</div>
<h2>Recomendação</h2>
<ul>
<li><b>L7 · Crista simples</b>: é a família que você quer, com o menor número de vértices; é a que melhor sobrevive a 16 px e desfocada.</li>
<li><b>R1 · Silhueta</b>: a melhor da família angular, uma massa só com o olho vermelho; lê bem no menor tamanho e é a mais fácil de manter igual em todos os tamanhos.</li>
</ul>
</html>
"""
(AQUI.parent / "rodada3.html").write_text(
    PAGE.replace("@@L@@", secao("traço")).replace("@@R@@", secao("angular")), encoding="utf-8")
