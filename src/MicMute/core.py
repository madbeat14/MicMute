import os
import json
import gc
from winsound import Beep
from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtMultimedia import QSoundEffect
from pycaw.pycaw import AudioUtilities

# --- CONFIGURATION ---
CONFIG_FILE = "mic_config.json"

# --- WORKER SIGNAL CLASS ---
class MuteSignals(QObject):
    update_icon = Signal(bool)
    theme_changed = Signal()
    toggle_mute = Signal() # Signal to trigger mute from hook
    set_mute = Signal(bool) # Signal to trigger explicit mute state from hook
    key_recorded = Signal(int) # Signal when a key is captured in recording mode
    exit_app = Signal()

signals = MuteSignals()

# --- AUDIO CONTROL ---
class AudioController:
    __slots__ = [
        'volume', 'device', 'device_id', 'beep_enabled', 'beep_config',
        'sound_config', 'hotkey_config', 'afk_config', 'osd_config',
        'persistent_overlay', 'sync_ids', 'BEEP_ERROR', 'player',
        '__weakref__'
    ]

    def __init__(self):
        self.volume = None
        self.device = None
        self.device_id = None
        self.beep_enabled = True
        self.beep_config = {
            'mute': {'freq': 650, 'duration': 180, 'count': 2},
            'unmute': {'freq': 700, 'duration': 200, 'count': 1}
        }
        self.sound_config = {
            'mute': None,
            'unmute': None
        }
        # New Hotkey Config Structure
        self.hotkey_config = {
            'mode': 'toggle', # 'toggle' or 'separate'
            'toggle': {'vk': 0xB3, 'name': 'Media Play/Pause'},
            'mute': {'vk': 0, 'name': 'None'},
            'unmute': {'vk': 0, 'name': 'None'}
        }
        self.afk_config = {'enabled': False, 'timeout': 60}
        self.osd_config = {'enabled': False, 'duration': 1500, 'position': 'Bottom-Center', 'size': 150}
        self.persistent_overlay = {
            'enabled': False,
            'show_vu': False,
            'opacity': 80,
            'x': 100,
            'y': 100,
            'position_mode': 'Custom',
            'locked': False,
            'sensitivity': 5
        }
        self.sync_ids = []
        self.BEEP_ERROR = (200, 500)
        
        # Audio Player
        self.player = None
        
        self.load_config()

    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.device_id = data.get('device_id')
                    self.beep_enabled = data.get('beep_enabled', True)
                    self.sync_ids = data.get('sync_ids', [])
                    
                    saved_beeps = data.get('beep_config')
                    if saved_beeps: self.beep_config.update(saved_beeps)
                    
                    saved_sounds = data.get('sound_config')
                    if saved_sounds: self.sound_config.update(saved_sounds)
                    
                    saved_hotkey = data.get('hotkey')
                    if saved_hotkey:
                        # Migration from old format {'vk': ..., 'name': ...}
                        if 'vk' in saved_hotkey:
                            self.hotkey_config['toggle'] = saved_hotkey
                        else:
                            self.hotkey_config.update(saved_hotkey)

                    saved_afk = data.get('afk')
                    if saved_afk: self.afk_config.update(saved_afk)

                    saved_osd = data.get('osd')
                    if saved_osd: self.osd_config.update(saved_osd)
                    
                    saved_overlay = data.get('persistent_overlay')
                    if saved_overlay: self.persistent_overlay.update(saved_overlay)
        except: pass

    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump({
                    'device_id': self.device_id,
                    'sync_ids': self.sync_ids,
                    'beep_enabled': self.beep_enabled,
                    'beep_config': self.beep_config,
                    'sound_config': self.sound_config,
                    'hotkey': self.hotkey_config,
                    'afk': self.afk_config,
                    'osd': self.osd_config,
                    'persistent_overlay': self.persistent_overlay
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

    def update_osd_config(self, new_config):
        self.osd_config = new_config
        self.save_config()
        
    def update_persistent_overlay(self, new_config):
        self.persistent_overlay = new_config
        self.save_config()
        
    def update_sync_ids(self, ids):
        self.sync_ids = ids
        self.save_config()

    def find_device(self):
        try:
            # Use generator to avoid creating full list if possible, though GetAllDevices returns list
            # We iterate efficiently
            all_devices = AudioUtilities.GetAllDevices()
            
            if self.device_id:
                # Generator expression for finding device
                found_dev = next((d for d in all_devices if d.id == self.device_id), None)
                if found_dev:
                    print(f"✓ Found saved device: {found_dev.FriendlyName}")
                    self.set_device_object(found_dev)
                    return True
                    
                print("Saved device not found, falling back to default...")
            
            try:
                enumerator = AudioUtilities.GetDeviceEnumerator()
                default_dev = enumerator.GetDefaultAudioEndpoint(1, 0)
                default_id = default_dev.GetId()
                
                found_default = next((d for d in all_devices if d.id == default_id), None)
                if found_default:
                    print(f"✓ Using system default: {found_default.FriendlyName}")
                    self.device_id = found_default.id
                    self.set_device_object(found_default)
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
            self.set_mute_state(not current)
        except Exception:
            if self.beep_enabled:
                Beep(*self.BEEP_ERROR)

    def set_device_mute(self, dev_id, state):
        """Helper to mute a specific device by ID."""
        try:
            all_devices = AudioUtilities.GetAllDevices()
            for dev in all_devices:
                if dev.id == dev_id:
                    dev.EndpointVolume.SetMute(state, None)
                    return
        except: pass

    def set_mute_state(self, new_state):
        if not self.volume: return
        try:
            current = self.volume.GetMute()
            if current != new_state:
                self.volume.SetMute(new_state, None)
                
                # Play Sound (Custom or Beep)
                sound_type = 'mute' if new_state else 'unmute'
                self.play_sound(sound_type)
            
            # Sync Slaves (Always force to match target state)
            for slave_id in self.sync_ids:
                self.set_device_mute(slave_id, new_state)
                
            signals.update_icon.emit(new_state)
            
        except Exception as e:
            print(f"Error setting mute state: {e}")
            
    def update_sound_config(self, new_config):
        self.sound_config = new_config
        self.save_config()

    def play_sound(self, sound_type):
        """Plays custom sound if set, else fallback to beep."""
        if not self.beep_enabled: return
        
        if self.player is None:
            self.player = QSoundEffect()
        
        custom_path = self.sound_config.get(sound_type)
        if custom_path and os.path.exists(custom_path):
            try:
                self.player.setSource(QUrl.fromLocalFile(custom_path))
                self.player.setVolume(0.5) # Default volume
                self.player.play()
                return
            except: pass
            
        # Fallback to Beep
        cfg = self.beep_config[sound_type]
        for _ in range(cfg['count']):
            Beep(cfg['freq'], cfg['duration'])

    # ... existing methods ...

    def set_mute_state(self, new_state):
        if not self.volume: return
        try:
            current = self.volume.GetMute()
            
            if current != new_state:
                self.volume.SetMute(new_state, None)
                
                # Play Sound (Custom or Beep)
                sound_type = 'mute' if new_state else 'unmute'
                self.play_sound(sound_type)
            
            # Sync Slaves (Always force to match target state)
            for slave_id in self.sync_ids:
                if slave_id != self.device_id: # Avoid self
                    self.set_device_mute(slave_id, new_state)
            
            # Emit signal AFTER syncing so UI reads correct states
            if current != new_state:
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
