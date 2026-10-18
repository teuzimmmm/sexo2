#!/usr/bin/env python3
"""Painel local de três frentes. Nenhuma chamada a modelos ou serviços."""
import argparse
import json
import os
import shutil
import unicodedata
from pathlib import Path
import sys
import time
from datetime import datetime, timezone

FRONTS = {'a': 'Proposta A', 'b': 'Proposta B', 'overlays': 'Overlays'}
STATES = ['aguardando', 'executando', 'validando', 'bloqueado', 'parcial', 'concluido', 'falhou']
HERE = Path(__file__).resolve().parent


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp.' + str(os.getpid()))
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)


def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0 else None


def clean(value, size=105):
    return ''.join(c for c in str(value) if c.isprintable())[:size]


def age(timestamp):
    try:
        seconds = max(0, int(time.time() - datetime.fromisoformat(timestamp.replace('Z', '+00:00')).timestamp()))
        return f'{seconds}s' if seconds < 60 else f'{seconds // 60}min'
    except (ValueError, TypeError, AttributeError):
        return 'n/d'


def fmt(value):
    return f'{value:,.0f}'.replace(',', '.') if number(value) is not None else 'n/d'


def money(value):
    return f'US$ {value:.4f}' if number(value) is not None else 'n/d'


def usage_fields(data):
    return {key: number(data.get(field)) for key, field in {
        'input': 'input_tokens', 'output': 'output_tokens',
        'cache_read': 'cache_read_input_tokens', 'cache_write': 'cache_creation_input_tokens'
    }.items()}


def ingest(data_dir, front, source, payload):
    path = data_dir / (front + '.usage.json')
    current = read(path)
    result = dict(current)
    if source == 'statusline':
        context = payload.get('context_window') or {}
        model = payload.get('model') or {}
        result.update(source='statusline', session_id=payload.get('session_id'),
                      model=model.get('display_name') or model.get('id'),
                      context_pct=number(context.get('used_percentage')),
                      cost_usd=number((payload.get('cost') or {}).get('total_cost_usd')),
                      rate_limits=payload.get('rate_limits') or {},
                      coverage='sessão; pode incluir subagentes',
                      context_tokens=number(context.get('total_input_tokens')))
        # Estes campos medem o contexto atual, não consumo acumulado.
        result['tokens'] = None
    elif source == 'result':
        if payload.get('type') != 'result' or not isinstance(payload.get('usage'), dict):
            raise ValueError('Esperado evento result com usage do Claude Code')
        result.update(source='stream-json result', session_id=payload.get('session_id'),
                      tokens=usage_fields(payload['usage']),
                      cost_usd=number(payload.get('total_cost_usd')),
                      context_pct=None, context_tokens=None,
                      coverage='resultado da sessão; pode incluir subagentes', rate_limits={})
    else:
        raise ValueError('Fonte não suportada')
    result['updated_at'] = now()
    write(path, result)


def cell_width(text):
    return sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in text)


def fit(text, width):
    text = clean(text, 10000)
    if cell_width(text) <= width:
        return text
    result = ''
    for char in text:
        if cell_width(result + char) > max(0, width - 1):
            break
        result += char
    return result + '…'


def stamp(value):
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone().strftime('%H:%M:%S')
    except (ValueError, TypeError, AttributeError):
        return 'n/d'


def render(data_dir, demo=False, width=118, height=40, color=False):
    width = max(24, min(width - 1, 138))
    detail = height >= 38
    shades = {'title': '38;5;222', 'dim': '90', 'executando': '38;5;222',
              'validando': '38;5;179', 'concluido': '38;5;114', 'bloqueado': '38;5;208',
              'falhou': '38;5;203', 'parcial': '38;5;208', 'aguardando': '90'}
    def ink(text, shade='dim'):
        return ('\033[' + shades.get(shade, '0') + 'm' + text + '\033[0m') if color else text
    def line(text, shade=None):
        text = fit(text, width)
        return ink(text, shade) if shade else text
    def row(text):
        text = fit(text, width - 4)
        return ink('│ ') + text + ' ' * (width - 4 - cell_width(text)) + ink(' │')
    lines = [line('SEXO2  /  TRÊS FRENTES' + ('  /  DEMONSTRAÇÃO FICTÍCIA' if demo else ''), 'title'),
             line('Acompanhamento local · a tela muda apenas quando chegam novos dados', 'dim')]
    for front, label in FRONTS.items():
        status = read(data_dir / (front + '.status.json'))
        usage = read(data_dir / (front + '.usage.json'))
        state = status.get('state', 'aguardando')
        heading = fit('─ ' + label.upper() + '  ·  ' + str(state).upper() + ' ', width - 2)
        lines.append(ink('╭' + heading + '─' * (width - 2 - cell_width(heading)) + '╮', state))
        done, total = status.get('done'), status.get('total')
        valid = isinstance(done, int) and isinstance(total, int) and 0 <= done <= total and total > 0
        count = f'{done}/{total} critérios' if valid else 'critérios n/d'
        bar = '█' * (int(12 * done / total) if valid else 0)
        bar += '░' * (12 - len(bar))
        model = status.get('model') or usage.get('model') or 'modelo n/d'
        task = status.get('task', 'Aguardando conexão com o Claude')
        if status.get('blocker') and not detail:
            task = 'BLOQUEIO · ' + status['blocker']
        tokens = usage.get('tokens') or {}
        pct = number(usage.get('context_pct'))
        context = f'{pct:.1f}%' if pct is not None else 'n/d'
        body = [str(task), f'{bar}  {count}  ·  {model}',
                'Tokens acumulados: entrada ' + fmt(tokens.get('input')) + ' | saída ' + fmt(tokens.get('output')),
                'Contexto ' + context + '  ·  Custo estimado ' + money(usage.get('cost_usd'))]
        if detail:
            body += ['Cache: lido ' + fmt(tokens.get('cache_read')) + ' | escrito ' + fmt(tokens.get('cache_write')),
                     ('Bloqueio: ' + status['blocker']) if status.get('blocker') else 'Evidência: ' + str(status.get('evidence') or 'aguardando'),
                     'Progresso ' + stamp(status.get('updated_at')) + ' | métricas ' + stamp(usage.get('updated_at')),
                     'Fonte: ' + str(usage.get('source') or 'não conectada') + ' · ' + str(usage.get('coverage') or 'cobertura n/d')]
        for index, text in enumerate(body):
            rendered = row(text)
            if color and index == 1:
                rendered = rendered.replace(bar, ink(bar, state))
            lines.append(rendered)
        lines.append(ink('╰' + '─' * (width - 2) + '╯'))
    control = read(data_dir / 'controle.usage.json')
    if control:
        summary = 'CONTROLE · custo estimado ' + money(control.get('cost_usd'))
        rates = control.get('rate_limits') or {}
        for key, label in [('five_hour', 'janela 5h'), ('seven_day', 'janela 7 dias')]:
            pct = number((rates.get(key) or {}).get('used_percentage'))
            if pct is not None:
                summary += f' · {label}: {pct:.0f}%'
        lines.append(line(summary, 'title'))
    lines += [line('n/d: não recebido · custos podem incluir subagentes; não são somados', 'dim'),
              line('Ctrl+C fecha só o painel · leitura local, sem chamadas a modelos', 'dim')]
    if detail:
        lines.append(line('Dados: ' + str(data_dir), 'dim'))
    if height < 22:
        return '\n'.join([line('SEXO2 · aumente a janela para ver os detalhes', 'title')] + [
            line(label + ': ' + str(read(data_dir / (front + '.status.json')).get('state', 'aguardando')))
            for front, label in FRONTS.items()] + [line('Ctrl+C fecha só o painel', 'dim')])
    return '\n'.join(lines)


class TerminalView:
    def __init__(self, stream):
        self.stream = stream
        self.previous = []

    def draw(self, frame, height):
        lines = frame.splitlines()[:height]
        updates = []
        for index in range(min(height, max(len(lines), len(self.previous)))):
            current = lines[index] if index < len(lines) else ''
            previous = self.previous[index] if index < len(self.previous) else None
            if current != previous:
                updates.append(f'\033[{index + 1};1H\033[2K' + current)
        if updates:
            self.stream.write(''.join(updates))
            self.stream.flush()
        self.previous = lines


def demo_data(path):
    for i, (front, label) in enumerate(FRONTS.items()):
        write(path / (front + '.status.json'), {'state': ['executando', 'validando', 'bloqueado'][i],
              'task': ['Ajustando o Hub com Oswald e Inter', 'Testando retorno das configurações', 'Aguardando navegador autorizado'][i],
              'done': i + 2, 'total': 8, 'model': 'Sonnet · exemplo', 'updated_at': now(),
              'blocker': 'Exemplo de bloqueio' if i == 2 else None, 'evidence': 'DADOS FICTÍCIOS'})
        write(path / (front + '.usage.json'), {'source': 'exemplo fictício', 'coverage': 'demonstração',
              'updated_at': now(), 'tokens': {'input': 1200 * (i+1), 'output': 800, 'cache_read': 20000, 'cache_write': 5000},
              'context_pct': 12 + i*4, 'cost_usd': 0.08 + i*0.03})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=HERE / 'estado')
    sub = parser.add_subparsers(dest='command')
    view = sub.add_parser('ver')
    view.add_argument('--once', action='store_true')
    view.add_argument('--demo', action='store_true')
    view.add_argument('--no-color', action='store_true', help='Desativa cores ANSI')
    status = sub.add_parser('status')
    status.add_argument('front', choices=FRONTS)
    status.add_argument('--state', choices=STATES, required=True)
    status.add_argument('--task', required=True)
    status.add_argument('--done', type=int)
    status.add_argument('--total', type=int)
    status.add_argument('--model')
    status.add_argument('--blocker')
    status.add_argument('--evidence')
    collect = sub.add_parser('coletar')
    collect.add_argument('front', choices=[*FRONTS, 'controle'])
    collect.add_argument('--source', choices=['statusline', 'result'], required=True)
    collect.add_argument('--input', type=Path, help='Sem esta opção, lê stdin; result aceita JSONL')
    args = parser.parse_args()
    if args.command == 'status':
        if (args.done is None) != (args.total is None) or (args.total is not None and not 0 <= args.done <= args.total):
            parser.error('--done e --total precisam ser válidos e usados juntos')
        if args.state == 'concluido' and (not args.total or args.done != args.total or not args.evidence):
            parser.error('concluido exige todos os critérios e --evidence')
        write(args.data / (args.front + '.status.json'), {k: getattr(args, k) for k in ['state', 'task', 'done', 'total', 'model', 'blocker', 'evidence']} | {'updated_at': now()})
    elif args.command == 'coletar':
        raw = args.input.read_text() if args.input else sys.stdin.read()
        if args.source == 'result':
            events = [json.loads(line) for line in raw.splitlines() if line.strip()]
            payload = next((e for e in reversed(events) if e.get('type') == 'result'), None)
            if payload is None:
                parser.error('Nenhum result recebido; métricas não foram alteradas')
        else:
            payload = json.loads(raw)
        ingest(args.data, args.front, args.source, payload)
    else:
        demo = getattr(args, 'demo', False)
        data = args.data
        if demo:
            import tempfile
            data = Path(tempfile.mkdtemp(prefix='sexo2-painel-demo-'))
            demo_data(data)
        once = getattr(args, 'once', False) or not sys.stdout.isatty()
        colors = sys.stdout.isatty() and not getattr(args, 'no_color', False) and 'NO_COLOR' not in os.environ
        screen = TerminalView(sys.stdout)
        if not once:
            sys.stdout.write('\033[?1049h\033[?25l')
            sys.stdout.flush()
        try:
            while True:
                size = shutil.get_terminal_size((120, 40))
                frame = render(data, demo, size.columns, size.lines, colors)
                if once:
                    print(frame)
                    break
                screen.draw(frame, size.lines)
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            if not once:
                sys.stdout.write('\033[0m\033[?25h\033[?1049l')
                sys.stdout.flush()
                print('Painel fechado. As tarefas continuam.')
            if demo:
                shutil.rmtree(data)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as exc:
        print('Erro: ' + str(exc), file=sys.stderr)
        sys.exit(1)
