import os
import gc
import threading
from winsound import Beep
from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtMultimedia import QSoundEffect
from pycaw.pycaw import AudioUtilities

from .config import ConfigManager, CONFIG_FILE

# --- WORKER SIGNAL CLASS ---
class MuteSignals(QObject):
    """
    Defines PySide6 signals for application-wide events.
    """
    # Signal to update the tray icon state
    update_icon = Signal(bool)
    # Signal when the system or app theme changes
    theme_changed = Signal()
    # Signal to trigger mute from hook
    toggle_mute = Signal()
    # Signal to trigger explicit mute state from hook
    set_mute = Signal(bool)
    # Signal when a key is captured in recording mode
    key_recorded = Signal(int)
    # Signal when default device changes
    device_changed = Signal(str)
    # Signal to exit the application
    exit_app = Signal()

signals = MuteSignals()

# --- AUDIO CONTROL ---
class AudioController:
    """
    Manages audio devices, volume control, and configuration.
    Handles interaction with Windows Core Audio APIs via pycaw.
    """
    __slots__ = [
        'volume', 'device', 'config_manager', 'BEEP_ERROR', 'player',
        'device_listener', 'enumerator',
        '__weakref__'
    ]

    def __init__(self):
        """
        Initializes the AudioController with default settings and loads configuration.
        """
        self.volume = None
        self.device = None
        self.config_manager = ConfigManager()
        self.BEEP_ERROR = (200, 500)
        
        # Audio Player
        self.player = None
        
        self.device_listener = None
        self.enumerator = None
        
        self.config_manager.load_config()
        self.start_device_watcher()

    # Property proxies for backward compatibility and ease of use
    @property
    def device_id(self): return self.config_manager.device_id
    @device_id.setter
    def device_id(self, value): self.config_manager.device_id = value
    
    @property
    def beep_enabled(self): return self.config_manager.beep_enabled
    @beep_enabled.setter
    def beep_enabled(self, value): self.config_manager.beep_enabled = value
    
    @property
    def sync_ids(self): return self.config_manager.sync_ids
    @sync_ids.setter
    def sync_ids(self, value): self.config_manager.sync_ids = value
    
    @property
    def beep_config(self): return self.config_manager.beep_config
    @beep_config.setter
    def beep_config(self, value): self.config_manager.beep_config = value
    
    @property
    def sound_config(self): return self.config_manager.sound_config
    @sound_config.setter
    def sound_config(self, value): self.config_manager.sound_config = value
    
    @property
    def hotkey_config(self): return self.config_manager.hotkey_config
    @hotkey_config.setter
    def hotkey_config(self, value): self.config_manager.hotkey_config = value
    
    @property
    def afk_config(self): return self.config_manager.afk_config
    @afk_config.setter
    def afk_config(self, value): self.config_manager.afk_config = value
    
    @property
    def osd_config(self): return self.config_manager.osd_config
    @osd_config.setter
    def osd_config(self, value): self.config_manager.osd_config = value
    
    @property
    def persistent_overlay(self): return self.config_manager.persistent_overlay
    @persistent_overlay.setter
    def persistent_overlay(self, value): self.config_manager.persistent_overlay = value

    def start_device_watcher(self):
        """
        Starts the background thread for monitoring audio device changes.
        """
        try:
            from .utils import DeviceChangeListener, CLSID_MMDeviceEnumerator, IMMDeviceEnumerator
            from comtypes import client
            
            self.enumerator = client.CreateObject(CLSID_MMDeviceEnumerator, interface=IMMDeviceEnumerator)
            self.device_listener = DeviceChangeListener(self.on_device_changed_callback)
            self.enumerator.RegisterEndpointNotificationCallback(self.device_listener)
            print("Background device watcher started.")
        except Exception as e:
            print(f"Failed to start device watcher: {e}")

    def on_device_changed_callback(self, new_device_id):
        """
        Callback triggered when the default audio device changes.
        
        Args:
            new_device_id (str): The ID of the new default device.
        """
        # Called from COM thread
        signals.device_changed.emit(new_device_id)

    def save_config(self):
        """
        Saves current application settings to the JSON configuration file.
        """
        self.config_manager.save_config()

    def set_beep_enabled(self, enabled):
        """
        Enables or disables the beep sound effect.
        
        Args:
            enabled (bool): True to enable, False to disable.
        """
        self.beep_enabled = enabled
        self.save_config()

    def update_beep_config(self, new_config):
        """
        Updates the configuration for beep sounds.
        
        Args:
            new_config (dict): New beep configuration dictionary.
        """
        self.beep_config = new_config
        self.save_config()

    def update_hotkey_config(self, new_config):
        """
        Updates the global hotkey configuration.
        
        Args:
            new_config (dict): New hotkey configuration dictionary.
        """
        self.hotkey_config = new_config
        self.save_config()

    def update_afk_config(self, new_config):
        """
        Updates the AFK (Away From Keyboard) feature configuration.
        
        Args:
            new_config (dict): New AFK configuration dictionary.
        """
        self.afk_config = new_config
        self.save_config()

    def update_osd_config(self, new_config):
        """
        Updates the On-Screen Display (OSD) configuration.
        
        Args:
            new_config (dict): New OSD configuration dictionary.
        """
        self.osd_config = new_config
        self.save_config()
        
    def update_persistent_overlay(self, new_config):
        """
        Updates the persistent overlay configuration.
        
        Args:
            new_config (dict): New overlay configuration dictionary.
        """
        self.persistent_overlay = new_config
        self.save_config()
        
    def update_sync_ids(self, ids):
        """
        Updates the list of synchronized device IDs.
        
        Args:
            ids (list): List of device IDs to sync with the main device.
        """
        self.sync_ids = ids
        self.save_config()

    def find_device(self):
        """
        Locates and initializes the target audio device.
        
        Returns:
            bool: True if a device was found and set, False otherwise.
        """
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
        """
        Sets the active audio device object and initializes volume control.
        
        Args:
            dev (AudioUtilities.device): The pycaw device object.
        """
        self.device = dev
        self.volume = dev.EndpointVolume
        signals.update_icon.emit(self.get_mute_state())

    def set_device_by_id(self, dev_id):
        """
        Sets the active device by its ID and saves the preference.
        
        Args:
            dev_id (str): The ID of the device to set.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        self.device_id = dev_id
        self.save_config()
        return self.find_device()

    def toggle_mute(self):
        """
        Toggles the mute state of the current device.
        """
        if not self.volume: return
        try:
            current = self.volume.GetMute()
            self.set_mute_state(not current)
        except Exception:
            if self.beep_enabled:
                Beep(*self.BEEP_ERROR)

    def set_device_mute(self, dev_id, state):
        """
        Helper to mute a specific device by ID.
        
        Args:
            dev_id (str): The ID of the device to mute.
            state (bool): True to mute, False to unmute.
        """
        try:
            all_devices = AudioUtilities.GetAllDevices()
            for dev in all_devices:
                if dev.id == dev_id:
                    dev.EndpointVolume.SetMute(state, None)
                    return
        except: pass

    def set_mute_state(self, new_state):
        """
        Sets the mute state of the current device and synchronized devices.
        
        Args:
            new_state (bool): True to mute, False to unmute.
        """
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
                # Avoid self
                if slave_id != self.device_id:
                    self.set_device_mute(slave_id, new_state)
            
            # Emit signal AFTER syncing so UI reads correct states
            if current != new_state:
                signals.update_icon.emit(new_state)
            
        except Exception as e:
            print(f"Error setting mute state: {e}")
            
    def update_sound_config(self, new_config):
        """
        Updates the configuration for custom sound files.
        
        Args:
            new_config (dict): New sound configuration dictionary.
        """
        self.sound_config = new_config
        self.save_config()

    def play_sound(self, sound_type):
        """
        Plays custom sound if set, else fallback to beep.
        
        Args:
            sound_type (str): 'mute' or 'unmute'.
        """
        if not self.beep_enabled: return
        
        if self.player is None:
            self.player = QSoundEffect()
        
        custom_path = self.sound_config.get(sound_type)
        if custom_path and os.path.exists(custom_path):
            try:
                self.player.setSource(QUrl.fromLocalFile(custom_path))
                # Default volume
                self.player.setVolume(0.5)
                self.player.play()
                return
            except: pass
            
        # Fallback to Beep
        def run_beep():
            cfg = self.beep_config[sound_type]
            for _ in range(cfg['count']):
                Beep(cfg['freq'], cfg['duration'])
        
        threading.Thread(target=run_beep, daemon=True).start()

    def get_mute_state(self):
        """
        Retrieves the current mute state of the active device.
        
        Returns:
            bool: True if muted, False otherwise.
        """
        if self.volume:
            try: return self.volume.GetMute()
            except: return False
        return False

audio = AudioController()
