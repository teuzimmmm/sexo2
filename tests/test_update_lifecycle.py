import os,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import Mock,patch
import psutil
from sexo2.update.lifecycle import processes_for,stop_installed_app,reopen_app,start_shutdown_listener,request_shutdown,stop_owned_tools

class UpdateLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();(self.root/'SEXO2.exe').write_bytes(b'fixture')
    def process(self,name,path,pid=123):
        p=Mock();p.info={'name':name};p.exe.return_value=str(path);p.pid=pid;p.children.return_value=[];return p
    def test_only_selected_installation_is_targeted(self):
        selected=self.process('SEXO2.exe',self.root/'SEXO2.exe')
        other=self.process('SEXO2.exe',self.root/'other/SEXO2.exe')
        league=self.process('League of Legends.exe',self.root/'League of Legends.exe')
        with patch('sexo2.update.lifecycle.psutil.process_iter',return_value=[selected,other,league]):
            self.assertEqual(processes_for(self.root),[selected])
        other.terminate.assert_not_called();league.terminate.assert_not_called()
    def test_graceful_exit_never_terminates(self):
        p=self.process('SEXO2.exe',self.root/'SEXO2.exe')
        with patch('sexo2.update.lifecycle.psutil.process_iter',side_effect=[[p],[],[]]),patch('sexo2.update.lifecycle.request_shutdown',return_value=True):
            stop_installed_app(self.root)
        p.wait.assert_called_once_with(timeout=8);p.kill.assert_not_called();p.terminate.assert_not_called()
    def test_older_app_is_terminated_and_waited(self):
        p=self.process('SEXO2.exe',self.root/'SEXO2.exe')
        with patch('sexo2.update.lifecycle.psutil.process_iter',side_effect=[[p],[],[]]),patch('sexo2.update.lifecycle.request_shutdown',return_value=False):
            stop_installed_app(self.root)
        p.terminate.assert_called_once();p.wait.assert_called_once_with(timeout=4)
    def test_graceful_timeout_falls_back_to_termination(self):
        p=self.process('SEXO2.exe',self.root/'SEXO2.exe');p.wait.side_effect=[psutil.TimeoutExpired(8,pid=123),None]
        with patch('sexo2.update.lifecycle.psutil.process_iter',side_effect=[[p],[],[]]),patch('sexo2.update.lifecycle.request_shutdown',return_value=True):
            stop_installed_app(self.root)
        p.terminate.assert_called_once();p.kill.assert_not_called()
    def test_paused_game_is_resumed_never_closed(self):
        p=self.process('SEXO2.exe',self.root/'SEXO2.exe');game=self.process('League of Legends.exe',self.root/'Game/League of Legends.exe');game.status.return_value=psutil.STATUS_STOPPED
        with patch('sexo2.update.lifecycle.psutil.process_iter',side_effect=[[p],[game],[]]),patch('sexo2.update.lifecycle.request_shutdown',return_value=False):
            stop_installed_app(self.root)
        game.resume.assert_called_once();game.terminate.assert_not_called();game.kill.assert_not_called()
    def test_reopen_uses_updated_installation_and_no_shell(self):
        with patch('sexo2.update.lifecycle.processes_for',return_value=[]),patch('sexo2.update.lifecycle.subprocess.Popen')as launch:
            reopen_app(self.root)
        self.assertEqual(launch.call_args.args[0],[str(self.root/'SEXO2.exe')])
        self.assertEqual(launch.call_args.kwargs['cwd'],str(self.root))
        self.assertNotIn('shell',launch.call_args.kwargs)
    def test_running_app_not_started_twice(self):
        with patch('sexo2.update.lifecycle.processes_for',return_value=[Mock()]),patch('sexo2.update.lifecycle.subprocess.Popen')as launch:
            reopen_app(self.root)
        launch.assert_not_called()
    @unittest.skipUnless(os.name=='nt','Windows native event')
    def test_real_windows_event_requests_shutdown_without_polling(self):
        done=threading.Event();path=self.root/'SEXO2.exe'
        thread=start_shutdown_listener(done.set,path)
        p=Mock();p.exe.return_value=str(path);p.pid=os.getpid()
        self.assertTrue(request_shutdown(p));self.assertTrue(done.wait(2));thread.join(2)
        self.assertFalse(thread.is_alive())

    def test_forced_exit_only_stops_owned_tool_children(self):
        parent=self.process('SEXO2.exe',self.root/'SEXO2.exe')
        tool=self.process('mod-tools.exe',self.root/'_internal/injection/tools/mod-tools.exe');tool.name.return_value='mod-tools.exe'
        foreign=self.process('mod-tools.exe',self.root.parent/'other/mod-tools.exe');foreign.name.return_value='mod-tools.exe'
        game=self.process('League of Legends.exe',self.root/'Game/League of Legends.exe');game.name.return_value='League of Legends.exe'
        parent.children.return_value=[tool,foreign,game]
        with patch('sexo2.update.lifecycle.psutil.wait_procs',return_value=([],[])):
            stop_owned_tools(parent,self.root)
        tool.terminate.assert_called_once();foreign.terminate.assert_not_called();game.terminate.assert_not_called()
