#!/usr/bin/env python3
import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLabel, QRadioButton, QButtonGroup, 
                             QHeaderView, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# Ensure we can import the core logic
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)
import vpngate_cli as vpncore

class Worker(QThread):
    finished = pyqtSignal(bool, str)
    
    def __init__(self, action, server=None):
        super().__init__()
        self.action = action
        self.server = server
        
    def run(self):
        try:
            if self.action == "connect":
                success, msg = vpncore.connect_vpn(self.server)
            else:
                success, msg = vpncore.disconnect_vpn()
            self.finished.emit(success, msg)
        except Exception as e:
            self.finished.emit(False, str(e))

class VPNWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VPN Gate GUI (Qt/Wayland)")
        self.setMinimumSize(900, 600)
        self.all_servers = []
        self.filtered_servers = []
        
        # Central Widget & Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        
        # 1. TOP: Server List (Scrollable)
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Idx", "Proto", "Country", "IP", "Score", "Ping"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.main_layout.addWidget(self.table)
        
        # 2. MIDDLE: Status Display
        self.status_label = QLabel("Status: Idle")
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px; border: 1px solid #ccc; border-radius: 5px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.status_label)
        
        # 3. BOTTOM: Controls
        controls_layout = QHBoxLayout()
        
        # Protocol Radio Buttons
        self.radio_group = QButtonGroup(self)
        self.radio_udp = QRadioButton("UDP (Fast)")
        self.radio_tcp = QRadioButton("TCP (Stable)")
        self.radio_all = QRadioButton("Show All")
        self.radio_udp.setChecked(True)
        
        self.radio_group.addButton(self.radio_udp)
        self.radio_group.addButton(self.radio_tcp)
        self.radio_group.addButton(self.radio_all)
        self.radio_group.buttonClicked.connect(self.apply_filter)
        
        controls_layout.addWidget(self.radio_udp)
        controls_layout.addWidget(self.radio_tcp)
        controls_layout.addWidget(self.radio_all)
        controls_layout.addStretch()
        
        # Action Buttons
        self.btn_refresh = QPushButton("Refresh List")
        self.btn_refresh.clicked.connect(self.load_servers)
        
        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold;")
        self.btn_connect.setMinimumHeight(40)
        self.btn_connect.clicked.connect(self.start_connect)
        
        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_disconnect.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold;")
        self.btn_disconnect.setMinimumHeight(40)
        self.btn_disconnect.clicked.connect(self.start_disconnect)
        
        controls_layout.addWidget(self.btn_refresh)
        controls_layout.addWidget(self.btn_connect)
        controls_layout.addWidget(self.btn_disconnect)
        
        self.main_layout.addLayout(controls_layout)
        
        # Initialization
        self.load_servers()
        self.check_initial_state()

    def update_ui_state(self, is_busy=False):
        # Check actual system state via nmcli
        active = vpncore.is_active()
        
        # Update Status Label
        if active:
            self.status_label.setText("Status: VPN IS ACTIVE")
            self.status_label.setStyleSheet("color: #27ae60; font-size: 14px; font-weight: bold; padding: 10px; border: 2px solid #27ae60; border-radius: 5px;")
        else:
            self.status_label.setText("Status: DISCONNECTED")
            self.status_label.setStyleSheet("color: #c0392b; font-size: 14px; font-weight: bold; padding: 10px; border: 2px solid #c0392b; border-radius: 5px;")

        # Enable/Disable logic
        if is_busy:
            # Disable everything while working
            self.table.setEnabled(False)
            self.btn_connect.setEnabled(False)
            self.btn_disconnect.setEnabled(False)
            self.btn_refresh.setEnabled(False)
            self.radio_udp.setEnabled(False)
            self.radio_tcp.setEnabled(False)
            self.radio_all.setEnabled(False)
        else:
            # Normal logic based on active state
            self.table.setEnabled(not active)
            self.btn_connect.setEnabled(not active)
            self.radio_udp.setEnabled(not active)
            self.radio_tcp.setEnabled(not active)
            self.radio_all.setEnabled(not active)
            self.btn_refresh.setEnabled(not active)
            
            # Disconnect only enabled if active
            self.btn_disconnect.setEnabled(active)

    def check_initial_state(self):
        self.update_ui_state()

    def load_servers(self):
        self.status_label.setText("Fetching servers from VPN Gate API...")
        QApplication.processEvents()
        self.all_servers = vpncore.get_servers()
        if not self.all_servers:
            QMessageBox.warning(self, "API Error", "Could not fetch server list. Check your internet connection.")
        self.apply_filter()

    def apply_filter(self):
        self.filtered_servers = []
        pref_udp = self.radio_udp.isChecked()
        pref_tcp = self.radio_tcp.isChecked()
        pref_all = self.radio_all.isChecked()
        
        for s in self.all_servers:
            if pref_all: self.filtered_servers.append(s)
            elif pref_udp and s['is_udp']: self.filtered_servers.append(s)
            elif pref_tcp and not s['is_udp']: self.filtered_servers.append(s)
            
        self.filtered_servers.sort(key=lambda x: int(x['Score']), reverse=True)
        self.update_table()
        self.update_ui_state()

    def update_table(self):
        self.table.setRowCount(0)
        for i, s in enumerate(self.filtered_servers[:100]):
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(str(i)))
            self.table.setItem(i, 1, QTableWidgetItem("UDP" if s['is_udp'] else "TCP"))
            self.table.setItem(i, 2, QTableWidgetItem(s['CountryShort']))
            self.table.setItem(i, 3, QTableWidgetItem(s['IP']))
            self.table.setItem(i, 4, QTableWidgetItem(s['Score']))
            self.table.setItem(i, 5, QTableWidgetItem(s['Ping']))

    def start_connect(self):
        # Edge case: Already connected
        if vpncore.is_active():
            QMessageBox.critical(self, "Error", "A VPN is already running. Please disconnect first.")
            self.update_ui_state()
            return

        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Selection Required", "Please select a server from the list.")
            return
            
        server = self.filtered_servers[row]
        self.status_label.setText(f"CONNECTING to {server['IP']} (10s timeout)...")
        self.update_ui_state(is_busy=True)
        
        self.worker = Worker("connect", server)
        self.worker.finished.connect(self.on_action_finished)
        self.worker.start()

    def start_disconnect(self):
        # Edge case: Not connected
        if not vpncore.is_active():
            QMessageBox.information(self, "Info", "No active connection to disconnect.")
            self.update_ui_state()
            return

        self.status_label.setText("DISCONNECTING and cleaning up...")
        self.update_ui_state(is_busy=True)
        
        self.worker = Worker("disconnect")
        self.worker.finished.connect(self.on_action_finished)
        self.worker.start()

    def on_action_finished(self, success, message):
        if not success:
            QMessageBox.critical(self, "VPN Error", message)
        self.status_label.setText(f"Status: {message}")
        self.update_ui_state(is_busy=False)

if __name__ == "__main__":
    # Force Wayland for Qt if possible
    os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"
    app = QApplication(sys.argv)
    window = VPNWindow()
    window.show()
    sys.exit(app.exec())
