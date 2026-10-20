import importlib.util
import io
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('painel', Path(__file__).with_name('painel.py'))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class PanelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_empty_is_unavailable_not_zero(self):
        text = p.render(self.data)
        self.assertEqual(text.count('Tokens acumulados: entrada n/d'), 3)
        self.assertIn('aguardando', text)

    def test_statusline_context_is_not_accumulated_usage(self):
        p.ingest(self.data, 'a', 'statusline', {'session_id': 's1', 'model': {'display_name': 'Sonnet'},
            'context_window': {'used_percentage': 25, 'total_input_tokens': 50000},
            'cost': {'total_cost_usd': 0.5}})
        value = p.read(self.data / 'a.usage.json')
        self.assertIsNone(value['tokens'])
        self.assertEqual(value['context_pct'], 25)
        self.assertIn('entrada n/d', p.render(self.data))

    def test_repeated_result_replaces_snapshot(self):
        payload = {'type': 'result', 'session_id': 's1', 'total_cost_usd': 0.25,
            'usage': {'input_tokens': 100, 'output_tokens': 50, 'cache_read_input_tokens': 1000}}
        p.ingest(self.data, 'a', 'result', payload)
        p.ingest(self.data, 'a', 'result', payload)
        result = p.read(self.data / 'a.usage.json')
        self.assertEqual(result['tokens']['input'], 100)
        self.assertEqual(result['cost_usd'], 0.25)

    def test_zero_is_preserved(self):
        self.assertEqual(p.fmt(0), '0')
        self.assertEqual(p.money(0), 'US$ 0.0000')
        self.assertIsNone(p.number(None))

    def test_three_independent_fronts(self):
        for front in p.FRONTS:
            p.write(self.data / (front + '.status.json'), {'state': 'executando', 'task': front, 'done': 1, 'total': 8})
        text = p.render(self.data)
        self.assertEqual(text.count('1/8 critérios'), 3)

    def test_reject_incomplete_completion(self):
        cmd = [sys.executable, str(Path(p.__file__)), '--data', str(self.data), 'status', 'a',
               '--state', 'concluido', '--task', 'Tarefa', '--done', '2', '--total', '8']
        self.assertNotEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
        self.assertFalse((self.data / 'a.status.json').exists())

    def test_account_limits_only_once(self):
        p.ingest(self.data, 'controle', 'statusline', {'rate_limits': {'five_hour': {'used_percentage': 20}}})
        self.assertEqual(p.render(self.data).count('janela 5h'), 1)

    def test_invalid_result_does_not_overwrite(self):
        with self.assertRaises(ValueError):
            p.ingest(self.data, 'a', 'result', {'type': 'assistant'})
        self.assertFalse((self.data / 'a.usage.json').exists())

    def test_terminal_controls_removed(self):
        self.assertNotIn('\033', p.clean('hello\033[2J'))

    def test_unchanged_frame_writes_nothing(self):
        output = io.StringIO()
        screen = p.TerminalView(output)
        screen.draw('one\ntwo', 24)
        output.seek(0)
        output.truncate()
        screen.draw('one\ntwo', 24)
        self.assertEqual(output.getvalue(), '')

    def test_only_modified_line_is_updated(self):
        output = io.StringIO()
        screen = p.TerminalView(output)
        screen.draw('one\ntwo', 24)
        output.seek(0)
        output.truncate()
        screen.draw('one\nchanged', 24)
        self.assertEqual(output.getvalue(), '\033[2;1H\033[2Kchanged')
        self.assertNotIn('\033[2J', output.getvalue())

    def test_layout_fits_terminal_sizes(self):
        p.demo_data(self.data)
        p.ingest(self.data, 'controle', 'statusline', {'cost': {'total_cost_usd': 0.2}})
        for width, height in [(40, 18), (60, 24), (80, 24), (120, 40), (160, 50)]:
            frame = p.render(self.data, True, width, height, color=True)
            lines = re.sub(r'\x1b\[[0-9;]*m', '', frame).splitlines()
            self.assertLessEqual(len(lines), height)
            self.assertTrue(all(p.cell_width(line) < width for line in lines))

    def test_compact_mode_keeps_blocker_visible(self):
        p.demo_data(self.data)
        self.assertIn('BLOQUEIO', p.render(self.data, width=80, height=24))

    def test_color_is_optional_and_semantic(self):
        p.demo_data(self.data)
        self.assertNotIn('\033', p.render(self.data, color=False))
        frame = p.render(self.data, color=True)
        for shade in ['38;5;222', '38;5;179', '38;5;208']:
            self.assertIn('\033[' + shade + 'm', frame)

    def test_no_clock_only_refresh(self):
        p.demo_data(self.data)
        before = p.render(self.data)
        self.assertEqual(before, p.render(self.data))

    def test_removed_lines_are_erased(self):
        output = io.StringIO()
        screen = p.TerminalView(output)
        screen.draw('one\ntwo', 24)
        output.seek(0)
        output.truncate()
        screen.draw('one', 24)
        self.assertEqual(output.getvalue(), '\033[2;1H\033[2K')


if __name__ == '__main__':
    unittest.main()
