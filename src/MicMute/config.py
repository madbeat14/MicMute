import os
import json

CONFIG_FILE = "mic_config.json"

class ConfigManager:
    """
    Manages loading and saving of application configuration.
    """
    def __init__(self):
        self.config_file = CONFIG_FILE
        self.device_id = None
        self.beep_enabled = True
        self.sync_ids = []
        
        self.beep_config = {
            'mute': {'freq': 650, 'duration': 180, 'count': 2},
            'unmute': {'freq': 700, 'duration': 200, 'count': 1}
        }
        self.sound_config = {
            'mute': None,
            'unmute': None
        }
        self.hotkey_config = {
            'mode': 'toggle',
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

    def load_config(self):
        """
        Loads application settings from the JSON configuration file.
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
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
        """
        Saves current application settings to the JSON configuration file.
        """
        try:
            with open(self.config_file, 'w') as f:
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
