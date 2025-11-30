import gc
from PySide6.QtGui import QColor, QAction
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QMessageBox, QCheckBox, QMenu, QStyle)
from PySide6.QtCore import Qt
from pycaw.pycaw import AudioUtilities

from ..core import signals, audio
from ..utils import set_default_device

class DeviceSelectionWidget(QWidget):
    """
    Widget for listing and selecting audio devices.
    """
    def __init__(self, parent=None):
        """
        Initializes the device selection widget.
        
        Args:
            parent (QWidget, optional): Parent widget.
        """
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # Table Setup
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Def", "Device Name", "Status", "Link Mute"])
        
        # Column Resizing
        header = self.table.horizontalHeader()
        # Default Indicator
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        # Name
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        # Status
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        # Sync
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh List")
        self.refresh_btn.clicked.connect(self.refresh_devices)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Row -> Device ID
        self.devices_map = {}
        # ID -> Device Object (for status updates)
        self.device_objects = {}
        
        # Listen for external updates
        signals.update_icon.connect(self.update_status_ui)
        signals.device_changed.connect(lambda _: self.refresh_devices())
        
        self.refresh_devices()

    def refresh_devices(self):
        """
        Refreshes the list of available audio devices.
        """
        self.table.setRowCount(0)
        self.devices_map.clear()
        self.device_objects.clear()
        
        try:
            # 1. Get All Devices (Wrappers)
            all_devices_raw = AudioUtilities.GetAllDevices()
            
            # 2. Get Capture IDs for filtering
            enumerator = AudioUtilities.GetDeviceEnumerator()
            # eCapture, eAll
            collection = enumerator.EnumAudioEndpoints(1, 1)
            count = collection.GetCount()
            capture_ids = set()
            for i in range(count):
                dev = collection.Item(i)
                capture_ids.add(dev.GetId())
            
            # Filter
            all_devices = []
            for dev in all_devices_raw:
                if dev.id in capture_ids:
                    all_devices.append(dev)
                    self.device_objects[dev.id] = dev
            
            # 3. Identify Default/Master
            # Always prioritize the actual Windows System Default
            try:
                # eCapture, eConsole
                default_dev = enumerator.GetDefaultAudioEndpoint(1, 0)
                windows_default_id = default_dev.GetId()
                
                # Update App Master to match Windows Default
                # This ensures we always control/sync the actual system default
                if windows_default_id:
                    audio.set_device_by_id(windows_default_id)
                    master_id = windows_default_id
                else:
                    master_id = audio.device_id
            except:
                master_id = audio.device_id

            # Fallback if still no master
            if not master_id and all_devices:
                master_id = all_devices[0].id
                audio.set_device_by_id(master_id)
            
            # 4. Sort: Master first, then others
            master_dev = None
            other_devs = []
            
            for dev in all_devices:
                if dev.id == master_id:
                    master_dev = dev
                else:
                    other_devs.append(dev)
            
            sorted_devices = []
            if master_dev: sorted_devices.append(master_dev)
            sorted_devices.extend(other_devs)
            
            # 5. Populate Table
            for row, dev in enumerate(sorted_devices):
                dev_id = dev.id
                self.table.insertRow(row)
                self.devices_map[row] = dev_id
                
                is_master = (dev_id == master_id)
                
                # Col 0: Default Indicator
                def_item = QTableWidgetItem()
                if is_master:
                    # Checkmark icon for default
                    def_item.setIcon(self.style().standardIcon(QStyle.SP_DialogApplyButton))
                    def_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 0, def_item)
                
                # Col 1: Name
                name = dev.FriendlyName
                name_item = QTableWidgetItem(name)
                if is_master:
                    font = name_item.font()
                    font.setBold(True)
                    name_item.setFont(font)
                    name_item.setForeground(QColor("green"))
                self.table.setItem(row, 1, name_item)
                
                # Col 2: Status
                try:
                    is_muted = dev.EndpointVolume.GetMute()
                    status_str = "Muted" if is_muted else "Unmuted"
                except: status_str = "?"
                status_item = QTableWidgetItem(status_str)
                status_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 2, status_item)

                # Col 3: Sync Checkbox
                chk_widget = QWidget()
                chk_layout = QHBoxLayout(chk_widget)
                chk_layout.setContentsMargins(0,0,0,0)
                chk_layout.setAlignment(Qt.AlignCenter)
                chk = QCheckBox()
                
                if is_master:
                    chk.setChecked(True)
                    chk.setEnabled(False)
                else:
                    chk.setChecked(dev_id in audio.sync_ids)
                    chk.toggled.connect(lambda checked, did=dev_id: self.on_sync_toggled(did, checked))
                
                chk_layout.addWidget(chk)
                self.table.setCellWidget(row, 3, chk_widget)
                
        except Exception as e:
            if self.isVisible():
                QMessageBox.critical(self, "Error", f"Failed to list devices: {e}")
        finally:
            gc.collect()

    def on_sync_toggled(self, dev_id, checked):
        """
        Handles toggling of device synchronization.
        
        Args:
            dev_id (str): The ID of the device.
            checked (bool): New checked state.
        """
        if checked:
            if dev_id not in audio.sync_ids:
                audio.sync_ids.append(dev_id)
                audio.set_device_mute(dev_id, audio.get_mute_state())
        else:
            if dev_id in audio.sync_ids:
                audio.sync_ids.remove(dev_id)

    def show_context_menu(self, pos):
        """
        Shows context menu for device table items.
        
        Args:
            pos (QPoint): Position of the click.
        """
        item = self.table.itemAt(pos)
        if not item: return
        
        row = item.row()
        dev_id = self.devices_map.get(row)
        if not dev_id: return
        
        if row == 0: return
        
        menu = QMenu(self)
        action_default = QAction("Set as Default Device", self)
        action_default.triggered.connect(lambda: self.set_as_default(dev_id))
        menu.addAction(action_default)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def set_as_default(self, dev_id):
        """
        Sets the specified device as the system default.
        
        Args:
            dev_id (str): The ID of the device to set as default.
        """
        if set_default_device(dev_id):
            if audio.set_device_by_id(dev_id):
                self.refresh_devices()
            else:
                QMessageBox.warning(self, "Error", "Failed to set application device.")
        else:
            QMessageBox.warning(self, "Error", "Failed to set Windows default device.")

    def update_status_ui(self, is_muted):
        """
        Updates the mute status in the UI for all devices.
        
        Args:
            is_muted (bool): Global mute state (unused, checks individual devices).
        """
        for row in range(self.table.rowCount()):
            dev_id = self.devices_map.get(row)
            if not dev_id: continue
            
            dev = self.device_objects.get(dev_id)
            if dev:
                try:
                    muted = dev.EndpointVolume.GetMute()
                    status_str = "Muted" if muted else "Unmuted"
                    self.table.item(row, 2).setText(status_str)
                except: pass

    def get_sync_ids(self):
        """
        Retrieves the list of device IDs selected for synchronization.
        
        Returns:
            list: List of device ID strings.
        """
        ids = []
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 3)
            if widget:
                chk = widget.findChild(QCheckBox)
                if chk and chk.isChecked():
                    dev_id = self.devices_map.get(row)
                    if dev_id:
                        ids.append(dev_id)
        return ids
    
    def get_selected_device_id(self):
        """
        Placeholder for compatibility.
        
        Returns:
            None
        """
        return None
