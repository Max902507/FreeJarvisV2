import base64
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'desktop'))
from desktop_speech import Speech,SpeechError
from linux_integration import write_with_backup, desktop_entries, suggestions, desktop_launch_args

class DesktopTests(unittest.TestCase):
    def test_bundle_loader_absolute_path(self):
        spec=importlib.util.spec_from_file_location('bundle_voice',ROOT/'scripts/bundle-voice.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        deps="""/lib64/ld-linux-x86-64.so.2 => /usr/lib64/ld-linux-x86-64.so.2 (0x0)
        libc.so.6 => /usr/lib/libc.so.6 (0x1)
        libespeak-ng.so.1 => /usr/lib/libespeak-ng.so.1 (0x2)
        """
        self.assertEqual(list(module.library_dependencies(deps)), [('libespeak-ng.so.1','/usr/lib/libespeak-ng.so.1')])
    def test_desktop_independent_discovery_and_visibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);apps=root/'applications';apps.mkdir()
            (apps/'a.desktop').write_text('[Desktop Entry]\nType=Application\nName=Editor\nExec=editor\nCategories=TextEditor;\n')
            (apps/'b.desktop').write_text('[Desktop Entry]\nType=Application\nName=Hidden\nExec=hidden\nHidden=true\nCategories=TextEditor;\n')
            (apps/'c.desktop').write_text('[Desktop Entry]\nType=Application\nName=Other\nExec=other\nOnlyShowIn=GNOME;\nCategories=TextEditor;\n')
            with patch.dict(os.environ,{'XDG_DATA_HOME':tmp,'XDG_DATA_DIRS':str(root/'none'),'XDG_CURRENT_DESKTOP':'Hyprland'}):
                with patch('linux_integration.shutil.which',side_effect=lambda name:'/usr/bin/gio' if name=='gio' else None):
                    self.assertEqual([p.name for p,d in desktop_entries()],['a.desktop'])
                    self.assertIn(['Editor',str(apps/'a.desktop')],suggestions())
                    self.assertEqual(desktop_launch_args(str(apps/'a.desktop')),['/usr/bin/gio','launch',str(apps/'a.desktop')])
                    outside=root/'outside.desktop';outside.write_text('not installed')
                    with self.assertRaises(OSError):desktop_launch_args(str(outside))
    def test_bundled_voice_without_host_path(self):
        assets=ROOT/'stage/assets'
        if not (assets/'desktop-voice/voice.json').is_file():self.skipTest('Stimme noch nicht gebündelt')
        with patch.dict(os.environ,{'PATH':'/nonexistent'}):
            voice=Speech(assets);self.assertTrue(voice.caps()['bundled_tts'])
            for lang in ('de-DE','en-US'):
                self.assertGreater(len(voice.synth({'text':'Hello Jarvis.','lang':lang})),1000)
    def test_atomic_write_backup(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'text.txt'
            self.assertFalse(write_with_backup(p,'first'))
            self.assertTrue(write_with_backup(p,'second'))
            self.assertEqual(p.read_text(),'second')
            self.assertEqual(Path(str(p)+'.bak').read_text(),'first')
    def test_backup_symlink_does_not_touch_external_file(self):
        with tempfile.TemporaryDirectory() as d,tempfile.TemporaryDirectory() as outside:
            p=Path(d)/'text.txt'; p.write_text('first')
            secret=Path(outside)/'secret';secret.write_text('unchanged')
            Path(str(p)+'.bak').symlink_to(secret)
            with self.assertRaises(OSError):write_with_backup(p,'second')
            self.assertEqual(secret.read_text(),'unchanged');self.assertEqual(p.read_text(),'first')
    def test_backup_hardlink_does_not_modify_external_inode(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'text.txt'; p.write_text('first')
            external=Path(d)/'outside.txt';external.write_text('unchanged');os.link(external,Path(str(p)+'.bak'))
            write_with_backup(p,'second');self.assertEqual(external.read_text(),'unchanged')
    def test_symlink_parent_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);actual=root/'actual';actual.mkdir();(root/'link').symlink_to(actual,target_is_directory=True)
            with self.assertRaises(OSError):write_with_backup(root/'link/text.txt','data')
            self.assertFalse((actual/'text.txt').exists())
    def test_invalid_audio_and_unknown_session(self):
        with tempfile.TemporaryDirectory() as d:
            s=Speech(d)
            with self.assertRaises(SpeechError):s.chunk('bad','not base64')
            with self.assertRaises(SpeechError):s.chunk('bad',base64.b64encode(b'\0\0').decode())
            with self.assertRaises(SpeechError):s.start('de-DE')
            self.assertEqual(s.close('bad'),{'ok':True})
    def test_real_local_tts_when_available(self):
        s=Speech(ROOT/'stage/assets')
        if not s.tts:self.skipTest('espeak(-ng) nicht installiert')
        data=s.synth({'text':'Guten Morgen.','lang':'de-DE'})
        self.assertTrue(data.startswith(b'RIFF'));self.assertIn(b'WAVE',data[:16]);self.assertGreater(len(data),1000)
    def test_real_vosk_load_and_pcm(self):
        s=Speech(ROOT/'stage/assets')
        if not s.caps()['stt']:self.skipTest('Sprachpakete noch nicht heruntergeladen')
        for lang in ('de-DE','en-US'):
            with self.subTest(lang=lang):
                key=s.start(lang)['id']
                try:
                    result=s.chunk(key,base64.b64encode(b'\0'*32000).decode())
                    self.assertIn('text',result);self.assertIn('final',result)
                finally:s.close(key)

if __name__=='__main__':unittest.main()
