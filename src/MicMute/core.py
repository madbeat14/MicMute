import os
import json
import gc
from winsound import Beep
from PySide6.QtCore import QObject, Signal
from pycaw.pycaw import AudioUtilities

# --- CONFIGURATION ---
CONFIG_FILE = "mic_config.json"

# --- WORKER SIGNAL CLASS ---
class MuteSignals(QObject):
    update_icon = Signal(bool)
    theme_changed = Signal()
    toggle_mute = Signal() # Signal to trigger mute from hook
    key_recorded = Signal(int) # Signal when a key is captured in recording mode
    exit_app = Signal()

signals = MuteSignals()

# --- AUDIO CONTROL ---
class AudioController:
    def __init__(self):
        self.volume = None
        self.device = None
        self.device_id = None
        self.beep_enabled = True
        self.beep_config = {
            'mute': {'freq': 650, 'duration': 180, 'count': 2},
            'unmute': {'freq': 700, 'duration': 200, 'count': 1}
        }
        self.hotkey_config = {'vk': 0xB3, 'name': 'Media Play/Pause'}
        self.afk_config = {'enabled': False, 'timeout': 60}
        self.BEEP_ERROR = (200, 500)
        self.load_config()

    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.device_id = data.get('device_id')
                    self.beep_enabled = data.get('beep_enabled', True)
                    
                    saved_beeps = data.get('beep_config')
                    if saved_beeps: self.beep_config.update(saved_beeps)
                    
                    saved_hotkey = data.get('hotkey')
                    if saved_hotkey: self.hotkey_config = saved_hotkey

                    saved_afk = data.get('afk')
                    if saved_afk: self.afk_config.update(saved_afk)
        except: pass

    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump({
                    'device_id': self.device_id,
                    'beep_enabled': self.beep_enabled,
                    'beep_config': self.beep_config,
                    'hotkey': self.hotkey_config,
                    'afk': self.afk_config
                }, f)
        except: pass

    def set_beep_enabled(self, enabled):
        self.beep_enabled = enabled
        self.save_config()

    def update_beep_config(self, new_config):
        self.beep_config = new_config
        self.save_config()

    def update_hotkey_config(self, new_config):
        self.hotkey_config = new_config
        self.save_config()

    def update_afk_config(self, new_config):
        self.afk_config = new_config
        self.save_config()

    def find_device(self):
        try:
            all_devices = AudioUtilities.GetAllDevices()
            if self.device_id:
                for dev in all_devices:
                    if dev.id == self.device_id:
                        print(f"✓ Found saved device: {dev.FriendlyName}")
                        self.set_device_object(dev)
                        return True
                print("Saved device not found, falling back to default...")
            try:
                enumerator = AudioUtilities.GetDeviceEnumerator()
                default_dev = enumerator.GetDefaultAudioEndpoint(1, 0)
                default_id = default_dev.GetId()
                for dev in all_devices:
                    if dev.id == default_id:
                        print(f"✓ Using system default: {dev.FriendlyName}")
                        self.device_id = dev.id
                        self.set_device_object(dev)
                        return True
            except: pass
            return False
        except Exception as e:
            print(f"Error finding device: {e}")
            return False
        finally: gc.collect()

    def set_device_object(self, dev):
        self.device = dev
        self.volume = dev.EndpointVolume
        signals.update_icon.emit(self.get_mute_state())

    def set_device_by_id(self, dev_id):
        self.device_id = dev_id
        self.save_config()
        return self.find_device()

    def toggle_mute(self):
        if not self.volume: return
        try:
            current = self.volume.GetMute()
            self.volume.SetMute(not current, None)
            new_state = self.volume.GetMute()
            
            if self.beep_enabled:
                cfg = self.beep_config['mute'] if new_state else self.beep_config['unmute']
                for _ in range(cfg['count']):
                    Beep(cfg['freq'], cfg['duration'])
            
            signals.update_icon.emit(new_state)
        except Exception:
            if self.beep_enabled:
                Beep(*self.BEEP_ERROR)

    def get_mute_state(self):
        if self.volume:
            try: return self.volume.GetMute()
            except: return False
        return False

audio = AudioController()
