import unittest


import io


import json


import subprocess


import tempfile


from pathlib import Path


from types import SimpleNamespace


from unittest.mock import Mock, patch


from injection import result_codes


from injection.core.injector import SkinInjector


from injection.game.match_recovery import MatchRecovery, game_pids


from injection.game.game_monitor import GameMonitor


from injection.overlay.overlay_manager import OverlayManager


from injection.overlay.match_context import MatchContext


from party.core.party_manager import (
    PartyManager,
    PERMANENT_PARTY_ROOM_KEY,
    PERMANENT_PARTY_NAME,
    get_party_room,
)


from utils.core.match_report import MatchReport


from utils.integration.tray_manager import TrayManager


from PIL import Image


class EmergencyStopTests(unittest.TestCase):
    """A parada vale para a partida atual, e só para ela."""

    def setUp(self):
        self.state = SimpleNamespace(phase="GameStart")
        self.recovery = MatchRecovery(self.state)

    def _manager(self):
        return SimpleNamespace(
            stop_injection_by_user=Mock(),
            resume_if_suspended=Mock(),
            game_monitor=SimpleNamespace(stop=Mock()),
        )

    def test_stop_uses_the_official_stop_path_and_releases_the_game(self):
        manager = self._manager()
        self.recovery.stop_current_match(manager)
        self.assertTrue(self.recovery.cancelled.is_set())
        # Caminho oficial do 1.3.1: derruba aplicador e mod-tools marcando que
        # a parada foi pedida, para não virar "falha".
        manager.stop_injection_by_user.assert_called_once()
        manager.resume_if_suspended.assert_called_once()
        manager.game_monitor.stop.assert_called_once()

    def test_stop_still_releases_the_game_when_the_official_path_fails(self):
        manager = self._manager()
        manager.stop_injection_by_user.side_effect = RuntimeError("boom")
        self.recovery.stop_current_match(manager)
        self.assertTrue(self.recovery.cancelled.is_set())
        manager.resume_if_suspended.assert_called_once()

    def test_stop_persists_until_the_next_match(self):
        self.recovery.cancelled.set()
        self.recovery.note_phase("Reconnect", "InProgress")
        self.assertTrue(self.recovery.cancelled.is_set())
        self.recovery.note_phase("InProgress", "Reconnect")
        self.assertTrue(self.recovery.cancelled.is_set())
        # Bug #255 do upstream era exatamente isto: o controle ficar preso
        # entre partidas. Uma seleção de campeões nova libera.
        self.recovery.note_phase("ChampSelect", "Lobby")
        self.assertFalse(self.recovery.cancelled.is_set())

    def test_new_match_clears_the_tray_warning(self):
        limpou = []
        self.recovery.clear_issue_callback = lambda: limpou.append(True)
        self.recovery.note_phase("ChampSelect", "Lobby")
        self.assertEqual(limpou, [True])

    def test_game_pids_survives_a_broken_psutil(self):
        with patch("injection.game.match_recovery.psutil", None):
            self.assertEqual(game_pids(), set())


class TrayIssueTests(unittest.TestCase):
    def test_emergency_stop_becomes_unavailable_for_current_match(self):
        tray = TrayManager()
        tray.icon = Mock()
        stopped = {"value": False}
        tray.stop_match_callback = lambda: stopped.update(value=True)
        tray.stop_match_available_callback = lambda: not stopped["value"]
        tray._on_stop_match(tray.icon, None)
        self.assertTrue(stopped["value"])
        self.assertFalse(tray._stop_match_enabled())
        tray.icon.update_menu.assert_called_once()

    def test_issue_is_persistent_deduplicated_and_cleared(self):
        tray = TrayManager()
        tray.icon = Mock()
        tray._base_icon_image = Image.new("RGBA", (128, 128))
        tray._locked_icon_image = tray._base_icon_image
        with patch("utils.integration.tray_manager.time.monotonic", side_effect=[100, 100.5, 104]):
            tray.report_match_issue("GAME_EXIT", "Rose perdeu o processo do LoL", "Causa desconhecida")
            tray.report_match_issue("GAME_EXIT", "Rose perdeu o processo do LoL", "Causa desconhecida")
            tray.report_match_issue("GAME_EXIT", "Rose perdeu o processo do LoL", "Causa desconhecida")
        self.assertEqual(tray._match_issue["count"], 2)
        self.assertIn("Rose perdeu", tray._issue_menu_label())
        tray.icon.notify.assert_called_once()
        tray.clear_match_issue()
        self.assertIsNone(tray._match_issue)
        self.assertIn("Nenhum problema", tray._issue_menu_label())


class ResultCodeTests(unittest.TestCase):
    """A1: desfecho deliberado não pode virar alarme de falha."""

    def _bare_injector(self, overlay_result):
        """SkinInjector mínimo: só o suficiente para chegar ao ramo de relatório."""
        injector = object.__new__(SkinInjector)
        injector.zips_dir = Path("/tmp")
        injector.last_injection_timing = {"mkoverlay_duration": 0.1}
        injector.zip_resolver = Mock()
        injector.zip_resolver.resolve_zip.return_value = Path("/tmp/skin.zip")
        injector.game_dir = None
        injector.mods_dir = Path("/tmp/mods")
        injector._clean_mods_dir = Mock()
        injector._clean_overlay_dir = Mock()
        injector._extract_zip_to_mod = Mock(return_value=SimpleNamespace(name="mod_11116"))
        injector._mk_run_overlay = Mock(return_value=overlay_result)
        return injector

    def test_expected_stops_are_separated_from_real_failures(self):
        for code in (result_codes.SAFETY_RELEASE, result_codes.GAME_NEVER_SEEN, result_codes.EMERGENCY_STOP):
            self.assertTrue(result_codes.is_expected_stop(code), code)
        for code in (1, 7, result_codes.BUILD_TIMEOUT, result_codes.MISSING_PREREQUISITE):
            self.assertFalse(result_codes.is_expected_stop(code), code)
        self.assertFalse(result_codes.is_expected_stop(result_codes.OK))

    def test_emergency_stop_does_not_report_injection_failed(self):
        injector = self._bare_injector(result_codes.EMERGENCY_STOP)
        with patch("injection.core.injector.report_issue") as report:
            applied = SkinInjector.inject_skin(injector, "11116")
        self.assertFalse(applied, "a skin não ficou ativa, então o retorno é False")
        report.assert_not_called()

    def test_safety_release_does_not_report_injection_failed(self):
        injector = self._bare_injector(result_codes.SAFETY_RELEASE)
        with patch("injection.core.injector.report_issue") as report:
            SkinInjector.inject_skin(injector, "11116")
        report.assert_not_called()

    def test_real_failure_still_reports(self):
        injector = self._bare_injector(7)
        with patch("injection.core.injector.report_issue") as report:
            SkinInjector.inject_skin(injector, "11116")
        report.assert_called_once()
        self.assertEqual(report.call_args[0][0], "INJECTION_FAILED")
        self.assertEqual(report.call_args.kwargs["details"]["result_code"], "7")


class MatchContextTests(unittest.TestCase):
    """A4: a fronteira entre overlay e manager precisa ser declarada e barulhenta."""

    def test_missing_attribute_warns_once_instead_of_silently_degrading(self):
        ctx = MatchContext(SimpleNamespace())  # manager sem nada
        with patch("injection.overlay.match_context.log") as logger:
            self.assertFalse(ctx.safety_released)
            self.assertFalse(ctx.safety_released)  # segunda vez não repete o aviso
        self.assertEqual(logger.warning.call_count, 1)

    def test_absent_manager_is_legitimate_and_silent(self):
        ctx = MatchContext(None)
        with patch("injection.overlay.match_context.log") as logger:
            self.assertIsNone(ctx.recovery)
            self.assertIsNone(ctx.phase)
            self.assertFalse(ctx.safety_released)
            self.assertFalse(ctx.cancelled)
            ctx.report_issue("X", "y", "z")
            ctx.start_monitor()
            ctx.stop_monitor()
        logger.warning.assert_not_called()

    def test_phase_and_cancellation_come_from_the_manager(self):
        recovery = MatchRecovery(SimpleNamespace(phase="InProgress"))
        ctx = MatchContext(
            SimpleNamespace(
                recovery=recovery,
                shared_state=SimpleNamespace(phase="InProgress"),
                safety_resume_triggered=False,
                report_match_issue=Mock(),
            )
        )
        self.assertEqual(ctx.phase, "InProgress")
        self.assertTrue(ctx.in_active_phase)
        self.assertFalse(ctx.cancelled)
        recovery.cancelled.set()
        self.assertTrue(ctx.cancelled)

    def test_monitor_control_prefers_public_api_but_accepts_legacy(self):
        modern = SimpleNamespace(start_monitor=Mock(), stop_monitor=Mock())
        MatchContext(modern).start_monitor()
        MatchContext(modern).stop_monitor()
        modern.start_monitor.assert_called_once()
        modern.stop_monitor.assert_called_once()

        legacy = SimpleNamespace(_start_monitor=Mock(), _stop_monitor=Mock())
        MatchContext(legacy).start_monitor()
        MatchContext(legacy).stop_monitor()
        legacy._start_monitor.assert_called_once()
        legacy._stop_monitor.assert_called_once()

    def test_report_issue_survives_a_broken_callback(self):
        ctx = MatchContext(SimpleNamespace(report_match_issue=Mock(side_effect=RuntimeError("boom"))))
        ctx.report_issue("CODE", "resumo", "detalhe")  # não pode propagar


class MatchReportTests(unittest.TestCase):
    """O registro por partida é o que transforma associação em evidência."""

    def _report_em(self, pasta):
        return patch("utils.core.paths.get_user_data_dir", return_value=Path(pasta))

    def test_timeline_records_what_the_11116_case_was_missing(self):
        with tempfile.TemporaryDirectory() as d, self._report_em(d):
            r = MatchReport(["11116"])
            r.preparo_s = 7.26
            r.evento("skin_iniciada", tentativa=1)
            r.jogo_visto([4242])
            r.aviso("GAME_EXIT")
            r.jogo_perdido()
            r.encerrar(result_codes.GAME_NEVER_SEEN, "processo do LoL não foi observado")

            arquivos = list((Path(d) / "logs" / "matches").glob("*.json"))
            self.assertEqual(len(arquivos), 1)
            dados = json.loads(arquivos[0].read_text(encoding="utf-8"))
            self.assertEqual(dados["skins"], ["11116"])
            self.assertEqual(dados["resultado"], result_codes.GAME_NEVER_SEEN)
            self.assertEqual(dados["preparo_s"], 7.26)
            self.assertEqual(dados["jogo"]["pids"], [4242])
            self.assertIn("perdido-apos", dados["jogo"]["estado"])
            self.assertEqual(dados["avisos"], ["GAME_EXIT"])
            nomes = [e["evento"] for e in dados["linha_do_tempo"]]
            self.assertEqual(nomes[0], "skin_iniciada")
            self.assertIn("jogo_perdido", nomes)

    def test_game_never_seen_is_distinguishable_from_game_lost(self):
        with tempfile.TemporaryDirectory() as d, self._report_em(d):
            r = MatchReport(["skin_1"])
            r.encerrar(result_codes.GAME_NEVER_SEEN, "x")
            dados = json.loads(next((Path(d) / "logs" / "matches").glob("*.json")).read_text(encoding="utf-8"))
            self.assertEqual(dados["jogo"]["estado"], "nunca-visto")
            self.assertIsNone(dados["jogo"]["vida_s"])

    def test_closing_twice_writes_one_report(self):
        with tempfile.TemporaryDirectory() as d, self._report_em(d):
            r = MatchReport(["skin_1"])
            r.encerrar(0, "ok")
            r.encerrar(1, "erro")
            self.assertEqual(len(list((Path(d) / "logs" / "matches").glob("*.json"))), 1)

    def test_reporting_never_raises_even_when_disk_fails(self):
        r = MatchReport(["skin_1"])
        with patch("utils.core.paths.get_user_data_dir", side_effect=OSError("sem disco")):
            r.encerrar(0, "ok")  # não pode propagar
        with patch.object(r, "_lock", side_effect=RuntimeError("boom")):
            r.evento("qualquer")  # idem

    def test_context_feeds_the_report_when_it_warns_the_user(self):
        ctx = MatchContext(SimpleNamespace(report_match_issue=Mock()), skins=["11116"])
        ctx.report_issue("GAME_EXIT", "resumo", "detalhe")
        ctx.report_issue("GAME_EXIT", "resumo", "detalhe")
        self.assertEqual(ctx.report.avisos, ["GAME_EXIT"])
