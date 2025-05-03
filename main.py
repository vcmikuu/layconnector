import os
import json
import webbrowser
import asyncio
import threading
import requests
import websockets
import aiohttp
import time

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QMessageBox,
    QListWidget, QDialog, QFormLayout, QDialogButtonBox,
    QInputDialog, QListWidgetItem, QTabWidget, QCheckBox,
    QComboBox, QGroupBox, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QObject

from TikTokLive import TikTokLiveClient
from TikTokLive.events import ConnectEvent, CommentEvent
from twitchio.ext.commands import Bot

CONFIG_DIR = os.path.join(os.getenv("APPDATA"), "layconnector")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

def ensure_config():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_FILE):
        cfg = {
            "tiktok_username": "",
            "twitch_username": "",
            "twitch_token": "",
            "actions": [],
            "mod_enabled": False,
            "mod_settings": {
                "http_url": "http://localhost:13337",
                "websocket_url": "ws://localhost:13338"
            }
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=4)
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)


class SetupWizard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LayConnector Setup")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Enter your TikTok username (without @):"))
        self.tik_tok_input = QLineEdit()
        layout.addWidget(self.tik_tok_input)
        layout.addWidget(QLabel("Enter your Twitch username:"))
        self.twitch_input = QLineEdit()
        layout.addWidget(self.twitch_input)
        row = QHBoxLayout()
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Paste your Twitch OAuth token here")
        row.addWidget(self.token_input)
        btn = QPushButton("Generate a new twitch token")
        btn.clicked.connect(lambda: webbrowser.open("https://antiscuff.com/oauth/"))
        row.addWidget(btn)
        layout.addLayout(row)
        save_btn = QPushButton("Save Configuration")
        save_btn.clicked.connect(self.on_save)
        layout.addWidget(save_btn)
        self.setLayout(layout)

    def on_save(self):
        tik = self.tik_tok_input.text().strip()
        tw = self.twitch_input.text().strip()
        tok = self.token_input.text().strip()
        if not tik or not tw or not tok:
            QMessageBox.warning(self, "Missing data", "Please fill all fields!")
            return
        cfg = {
            "tiktok_username": tik,
            "twitch_username": tw,
            "twitch_token": tok,
            "actions": [],
            "mod_enabled": False,
            "mod_settings": {
                "http_url": "http://localhost:13337",
                "websocket_url": "ws://localhost:13338"
            }
        }
        save_config(cfg)
        QMessageBox.information(self, "Saved", "Configuration saved!")
        self.close()
        self.main = MainWindow()
        self.main.show()

class ActionDialog(QDialog):
    def __init__(self, parent=None, action=None, mod_enabled=False):
        super().__init__(parent)
        self.setWindowTitle("Add/Edit Action")
        self.resize(500, 400)
        self.mod_enabled = mod_enabled
        
        self.action = action or {
            "trigger": "", 
            "responses": [],
            "use_mod": False,
            "mod_action": {
                "type": "queue",
                "params": {}
            }
        }
        
        if "use_mod" not in self.action:
            self.action["use_mod"] = False
            self.action["mod_action"] = {"type": "queue", "params": {}}
        
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        self.trigger_input = QLineEdit(self.action["trigger"])
        form.addRow("Trigger (e.g. !bsr abc):", self.trigger_input)
        layout.addLayout(form)
        
        tabs = QTabWidget()
        
        standard_tab = QWidget()
        std_layout = QVBoxLayout(standard_tab)
        std_layout.addWidget(QLabel("Response Commands:"))
        self.responses_list = QListWidget()
        for resp in self.action["responses"]:
            self.responses_list.addItem(resp)
        std_layout.addWidget(self.responses_list)
        
        resp_btns = QHBoxLayout()
        add_resp = QPushButton("Add")
        edit_resp = QPushButton("Edit")
        delete_resp = QPushButton("Delete")
        add_resp.clicked.connect(self.add_response)
        edit_resp.clicked.connect(self.edit_response)
        delete_resp.clicked.connect(self.delete_response)
        resp_btns.addWidget(add_resp)
        resp_btns.addWidget(edit_resp)
        resp_btns.addWidget(delete_resp)
        std_layout.addLayout(resp_btns)
        
        std_layout.addWidget(QLabel("Available variables: {userinput}, {username}"))
        tabs.addTab(standard_tab, "Standard Responses")
        
        mod_tab = QWidget()
        mod_layout = QVBoxLayout(mod_tab)
        
        self.mod_checkbox = QCheckBox("Enable DumbRequestManager integration")
        self.mod_checkbox.setChecked(self.action["use_mod"])
        self.mod_checkbox.setEnabled(self.mod_enabled)
        self.mod_checkbox.toggled.connect(self.toggle_mod_options)
        mod_layout.addWidget(self.mod_checkbox)
        
        if not self.mod_enabled:
            mod_layout.addWidget(QLabel("DumbRequestManager integration is disabled. Enable it in Settings first."))
        
        self.mod_group = QGroupBox("Mod Actions")
        mod_group_layout = QFormLayout(self.mod_group)
        
        self.action_type = QComboBox()
        self.action_type.addItems(["Query Map", "Add to Queue", "Check Queue", "Clear Queue", 
                                  "Open/Close Queue", "Move in Queue", "Shuffle Queue", "View History"])
        
        self.action_map = {
            "query": 0,
            "addKey": 1,
            "queue": 2,
            "clear": 3,
            "open": 4,
            "move": 5,
            "shuffle": 6,
            "history": 7
        }
        
        current_type = self.action["mod_action"]["type"]
        if current_type in self.action_map:
            self.action_type.setCurrentIndex(self.action_map[current_type])
        
        mod_group_layout.addRow("Action Type:", self.action_type)
        
        self.param_widget = QWidget()
        self.param_layout = QFormLayout(self.param_widget)
        self.update_params_ui()
        
        self.action_type.currentIndexChanged.connect(self.update_params_ui)
        mod_group_layout.addRow("Parameters:", self.param_widget)
        
        mod_layout.addWidget(self.mod_group)
        self.mod_group.setEnabled(self.action["use_mod"] and self.mod_enabled)
        
        tabs.addTab(mod_tab, "DumbRequestManager Integration")
        layout.addWidget(tabs)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def toggle_mod_options(self, enabled):
        self.mod_group.setEnabled(enabled and self.mod_enabled)

    def update_params_ui(self):
        while self.param_layout.count():
            item = self.param_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        idx = self.action_type.currentIndex()
        action_types = ["query", "addKey", "queue", "clear", "open", "move", "shuffle", "history"]
        
        if idx < len(action_types):
            action_type = action_types[idx]
            
            params = self.action["mod_action"].get("params", {})
            
            if action_type in ["query", "addKey"]:
                self.map_key = QLineEdit(params.get("map_key", "{userinput}"))
                self.param_layout.addRow("Map Key:", self.map_key)
                
                if action_type == "addKey":
                    self.user_input = QLineEdit(params.get("user", "{username}"))
                    self.param_layout.addRow("User:", self.user_input)
                    
                    self.prepend_check = QCheckBox()
                    self.prepend_check.setChecked(params.get("prepend", False))
                    self.param_layout.addRow("Prepend to queue:", self.prepend_check)
            
            elif action_type == "where":
                self.user_param = QLineEdit(params.get("user", "{username}"))
                self.param_layout.addRow("User to check:", self.user_param)
                
            elif action_type == "open":
                self.open_value = QComboBox()
                self.open_value.addItems(["Open", "Close"])
                self.open_value.setCurrentIndex(0 if params.get("open", True) else 1)
                self.param_layout.addRow("Queue state:", self.open_value)
                
            elif action_type == "move":
                self.from_pos = QLineEdit(str(params.get("from", "1")))
                self.param_layout.addRow("From position:", self.from_pos)
                
                self.to_pos = QLineEdit(str(params.get("to", "1")))
                self.param_layout.addRow("To position:", self.to_pos)
                
            elif action_type == "history":
                self.limit_value = QLineEdit(str(params.get("limit", "5")))
                self.param_layout.addRow("Limit results:", self.limit_value)
                
    def add_response(self):
        text, ok = QInputDialog.getText(self, "Add Response", "Enter response command:")
        if ok and text.strip():
            self.responses_list.addItem(text.strip())
    
    def edit_response(self):
        current = self.responses_list.currentItem()
        if current:
            text, ok = QInputDialog.getText(self, "Edit Response", 
                                          "Edit response command:", 
                                          text=current.text())
            if ok and text.strip():
                current.setText(text.strip())
    
    def delete_response(self):
        current = self.responses_list.currentRow()
        if current >= 0:
            self.responses_list.takeItem(current)

    def gather_params(self):
        idx = self.action_type.currentIndex()
        action_types = ["query", "addKey", "queue", "clear", "open", "move", "shuffle", "history"]
        
        params = {}
        if idx < len(action_types):
            action_type = action_types[idx]
            
            if action_type in ["query", "addKey"]:
                params["map_key"] = self.map_key.text()
                
                if action_type == "addKey":
                    params["user"] = self.user_input.text()
                    params["prepend"] = self.prepend_check.isChecked()
            
            elif action_type == "where":
                params["user"] = self.user_param.text()
                
            elif action_type == "open":
                params["open"] = self.open_value.currentIndex() == 0
                
            elif action_type == "move":
                try:
                    params["from"] = int(self.from_pos.text())
                    params["to"] = int(self.to_pos.text())
                except ValueError:
                    params["from"] = 1
                    params["to"] = 1
                
            elif action_type == "history":
                try:
                    params["limit"] = int(self.limit_value.text())
                except ValueError:
                    params["limit"] = 5
        
        return action_types[idx], params

    def accept(self):
        trigger = self.trigger_input.text().strip()
        
        responses = []
        for i in range(self.responses_list.count()):
            responses.append(self.responses_list.item(i).text())
        
        if not trigger or (not responses and not self.mod_checkbox.isChecked()):
            QMessageBox.warning(self, "Invalid Input", 
                             "Please provide a trigger and either responses or enable mod action.")
            return
        
        self.action["trigger"] = trigger
        self.action["responses"] = responses
        self.action["use_mod"] = self.mod_checkbox.isChecked() and self.mod_enabled
        
        if self.action["use_mod"]:
            action_type, params = self.gather_params()
            self.action["mod_action"] = {
                "type": action_type,
                "params": params
            }
            
        super().accept()


class SettingsWindow(QWidget):
    def __init__(self, config, on_update):
        super().__init__()
        self.setWindowTitle("LayConnector Settings")
        self.cfg = config
        self.on_update = on_update
        
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        
        self.actions_tab = QWidget()
        self.setup_actions_tab()
        self.tabs.addTab(self.actions_tab, "Actions")
        
        self.mod_tab = QWidget()
        self.setup_mod_tab()
        self.tabs.addTab(self.mod_tab, "DumbRequestManager")
        
        layout.addWidget(self.tabs)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save & Close")
        save_btn.clicked.connect(self.on_save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)
        
        self.resize(700, 500)
    
    def setup_actions_tab(self):
        layout = QVBoxLayout(self.actions_tab)
        
        self.list_widget = QListWidget()
        layout.addWidget(QLabel("Configured Actions:"))
        layout.addWidget(self.list_widget)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Action")
        edit_btn = QPushButton("Edit Action")
        delete_btn = QPushButton("Delete Action")
        add_btn.clicked.connect(self.add_action)
        edit_btn.clicked.connect(self.edit_action)
        delete_btn.clicked.connect(self.delete_action)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)
        layout.addLayout(btn_layout)
        
        self.refresh_action_list()
    
    def setup_mod_tab(self):
        layout = QVBoxLayout(self.mod_tab)
        
        self.mod_enabled_check = QCheckBox("Enable DumbRequestManager integration")
        self.mod_enabled_check.setChecked(self.cfg.get("mod_enabled", False))
        layout.addWidget(self.mod_enabled_check)
        
        self.mod_group = QGroupBox("DumbRequestManager Connection Settings")
        mod_group_layout = QFormLayout(self.mod_group)
        
        self.http_url = QLineEdit(self.cfg.get("mod_settings", {}).get("http_url", "http://localhost:13337"))
        mod_group_layout.addRow("HTTP API URL:", self.http_url)
        
        self.websocket_url = QLineEdit(self.cfg.get("mod_settings", {}).get("websocket_url", "ws://localhost:13338"))
        mod_group_layout.addRow("WebSocket API URL:", self.websocket_url)
        
        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(self.test_mod_connection)
        mod_group_layout.addRow("", test_btn)
        
        layout.addWidget(self.mod_group)
        
        info_group = QGroupBox("About DumbRequestManager Integration")
        info_layout = QVBoxLayout(info_group)
        
        info_text = """
        <p><b>DumbRequestManager Integration</b> allows you to interact with the game's song request system 
        through this connector.</p>
        
        <p>Features include:</p>
        <ul>
        <li>Querying maps with /query endpoint</li>
        <li>Adding maps to the request queue with /addKey</li>
        <li>Managing the song request queue</li>
        <li>Viewing play history</li>
        </ul>
        
        <p>Before enabling, make sure the game is running with the mod installed. 
        The mod runs HTTP and WebSocket servers by default on ports 13337 and 13338.</p>
        """
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        
        layout.addWidget(info_group)
        layout.addStretch(1)
    
    def refresh_action_list(self):
        self.list_widget.clear()
        for act in self.cfg["actions"]:
            mod_indicator = "[MOD] " if act.get("use_mod", False) else ""
            item_text = f"{mod_indicator}{act['trigger']} → "
            
            if act.get("use_mod", False):
                mod_type = act.get("mod_action", {}).get("type", "queue")
                item_text += f"Beat Saber: {mod_type}"
            else:
                item_text += f"{len(act['responses'])} responses"
                
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, act)
            self.list_widget.addItem(item)
    
    def add_action(self):
        dlg = ActionDialog(self, mod_enabled=self.cfg.get("mod_enabled", False))
        if dlg.exec() == QDialog.Accepted:
            self.cfg["actions"].append(dlg.action)
            self.refresh_action_list()
    
    def edit_action(self):
        item = self.list_widget.currentItem()
        if not item: 
            QMessageBox.information(self, "No Selection", "Please select an action to edit.")
            return
            
        act = item.data(Qt.UserRole)
        dlg = ActionDialog(self, action=act.copy(), mod_enabled=self.cfg.get("mod_enabled", False))
        if dlg.exec() == QDialog.Accepted:
            idx = self.list_widget.row(item)
            self.cfg["actions"][idx] = dlg.action
            self.refresh_action_list()
    
    def delete_action(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.information(self, "No Selection", "Please select an action to delete.")
            return
            
        idx = self.list_widget.row(item)
        if QMessageBox.question(self, "Confirm Delete", 
                             f"Delete action '{self.cfg['actions'][idx]['trigger']}'?") == QMessageBox.Yes:
            del self.cfg["actions"][idx]
            self.refresh_action_list()
    
    def test_mod_connection(self):
        http_url = self.http_url.text().strip()
        
        try:
            response = requests.get(f"{http_url}/queue", timeout=3)
            if response.status_code == 200:
                QMessageBox.information(self, "Connection Success", 
                                    "Successfully connected to DumbRequestManager API!")
            else:
                QMessageBox.warning(self, "Connection Issue", 
                                 f"Received status code {response.status_code} from the API.")
        except Exception as e:
            QMessageBox.warning(self, "Connection Failed", 
                             f"Could not connect to the DumbRequestManager API.\n\nError: {str(e)}\n\n"
                             "Make sure the game is running with the mod installed.")
    
    def on_save(self):
        self.cfg["mod_enabled"] = self.mod_enabled_check.isChecked()
        self.cfg["mod_settings"] = {
            "http_url": self.http_url.text().strip(),
            "websocket_url": self.websocket_url.text().strip()
        }
        
        if not self.cfg["mod_enabled"]:
            for act in self.cfg["actions"]:
                if act.get("use_mod", False):
                    act["use_mod"] = False
        
        save_config(self.cfg)
        self.on_update(self.cfg)
        self.close()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LayConnector Dashboard")
        self.cfg = ensure_config()
        self.running = False
        self.mod_ws = None
        
        layout = QVBoxLayout(self)
        
        status_group = QGroupBox("Connection Status")
        status_layout = QFormLayout(status_group)
        
        self.tiktok_status = QLabel("Disconnected")
        self.tiktok_status.setStyleSheet("color: red;")
        status_layout.addRow("TikTok:", self.tiktok_status)
        
        self.twitch_status = QLabel("Disconnected")
        self.twitch_status.setStyleSheet("color: red;")
        status_layout.addRow("Twitch:", self.twitch_status)
        
        self.mod_status = QLabel("Disabled")
        self.mod_status.setStyleSheet("color: gray;")
        status_layout.addRow("DumbRequestManager:", self.mod_status)
        
        layout.addWidget(status_group)
        
        config_group = QGroupBox("Configuration Summary")
        config_layout = QFormLayout(config_group)
        
        self.tiktok_user = QLabel(self.cfg["tiktok_username"] or "Not configured")
        config_layout.addRow("TikTok Username:", self.tiktok_user)
        
        self.twitch_user = QLabel(self.cfg["twitch_username"] or "Not configured")
        config_layout.addRow("Twitch Channel:", self.twitch_user)
        
        self.actions_count = QLabel(f"{len(self.cfg['actions'])} actions configured")
        config_layout.addRow("Actions:", self.actions_count)
        
        self.mod_enabled = QLabel("Enabled" if self.cfg.get("mod_enabled", False) else "Disabled")
        config_layout.addRow("DumbRequestManager:", self.mod_enabled)
        
        layout.addWidget(config_group)
        
        control_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("Start Connector")
        self.start_btn.clicked.connect(self.start_connectors)
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop Connector")
        self.stop_btn.clicked.connect(self.stop_connectors)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)
        
        layout.addLayout(control_layout)
        
        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self.open_settings)
        layout.addWidget(settings_btn)
        
        exit_btn = QPushButton("Exit")
        exit_btn.clicked.connect(QApplication.instance().quit)
        layout.addWidget(exit_btn)
        
        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_widget = QListWidget()
        log_layout.addWidget(self.log_widget)
        
        layout.addWidget(log_group)
        
        self.resize(500, 600)
        
    def log_message(self, message):
        self.log_widget.addItem(time.strftime("%H:%M:%S") + " - " + message)
        self.log_widget.scrollToBottom()

    def open_settings(self):
        self.settings = SettingsWindow(self.cfg, self.on_settings_updated)
        self.settings.show()

    def on_settings_updated(self, new_cfg):
        self.cfg = new_cfg
        
        self.tiktok_user.setText(self.cfg["tiktok_username"] or "Not configured")
        self.twitch_user.setText(self.cfg["twitch_username"] or "Not configured")
        self.actions_count.setText(f"{len(self.cfg['actions'])} actions configured")
        self.mod_enabled.setText("Enabled" if self.cfg.get("mod_enabled", False) else "Disabled")
        
        if self.running:
            QMessageBox.information(self, "Settings Changed", 
                                  "Please restart the connector to apply new settings.")

    def start_connectors(self):
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.running = True
        
        self.thread = threading.Thread(target=lambda: asyncio.run(self.run_async()), daemon=True)
        self.thread.start()
        
        self.log_message("Starting connections...")

    def stop_connectors(self):
        self.log_message("Stopping connections...")
        self.running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        self.tiktok_status.setText("Disconnected")
        self.tiktok_status.setStyleSheet("color: red;")
        self.twitch_status.setText("Disconnected")
        self.twitch_status.setStyleSheet("color: red;")
        self.mod_status.setText("Disabled")
        self.mod_status.setStyleSheet("color: gray;")

    async def run_async(self):
        try:
            def update_ui(func):
                QApplication.instance().callAfter(func)
                
            tik = TikTokLiveClient(unique_id=self.cfg["tiktok_username"])
            
            bot = Bot(
                token=self.cfg["twitch_token"],
                prefix="!",
                initial_channels=[self.cfg["twitch_username"]]
            )
            
            mod_connected = False
            
            if self.cfg.get("mod_enabled", False):
                self.mod_ws = None
                try:
                    self.log_message("Testing DumbRequestManager HTTP connection...")
                    response = await aiohttp.ClientSession().get(
                        f"{self.cfg['mod_settings']['http_url']}/queue", 
                        timeout=aiohttp.ClientTimeout(total=3)
                    )
                    if response.status == 200:
                        self.log_message("DumbRequestManager HTTP connection successful")
                        mod_connected = True
                        
                        QApplication.instance().callAfter(lambda: self.update_mod_status("HTTP Connected", "green"))
                    else:
                        self.log_message(f"DumbRequestManager HTTP connection failed: Status {response.status}")
                        QApplication.instance().callAfter(lambda: self.update_mod_status("HTTP Error", "orange"))
                except Exception as e:
                    self.log_message(f"DumbRequestManager HTTP connection failed: {str(e)}")
                    QApplication.instance().callAfter(lambda: self.update_mod_status("Connection Error", "red"))
            
            @tik.on(ConnectEvent)
            async def on_tik_connect(evt):
                self.log_message(f"Connected to TikTok @{evt.unique_id}")
                QApplication.instance().callAfter(lambda: self.update_tiktok_status("Connected", "green"))

            @tik.on(CommentEvent)
            async def on_comment(evt):
                msg = f"{evt.user.nickname}: {evt.comment}"
                username = evt.user.nickname
                comment = evt.comment
                
                channel = bot.get_channel(self.cfg["twitch_username"])
                if channel:
                    await channel.send(msg)
                
                for act in self.cfg["actions"]:
                    if comment.startswith(act["trigger"]):
                        user_input = comment[len(act["trigger"]):].strip()
                        
                        for cmd in act["responses"]:
                            out = cmd.replace("{userinput}", user_input).replace("{username}", username)
                            if channel:
                                await channel.send(out)
                        
                        if act.get("use_mod", False) and mod_connected and self.cfg.get("mod_enabled", False):
                            await self.execute_mod_action(act["mod_action"], user_input, username, channel)

            tasks = [tik.start(), bot.start()]
            
            if self.cfg.get("mod_enabled", False):
                tasks.append(self.connect_mod_websocket())
                
            await asyncio.gather(*tasks)
            
        except Exception as e:
            self.log_message(f"Error in connector: {str(e)}")
            QApplication.instance().callAfter(lambda: self.stop_connectors())

    def update_tiktok_status(self, status, color):
        self.tiktok_status.setText(status)
        self.tiktok_status.setStyleSheet(f"color: {color};")
        
    def update_twitch_status(self, status, color):
        self.twitch_status.setText(status)
        self.twitch_status.setStyleSheet(f"color: {color};")
        
    def update_mod_status(self, status, color):
        self.mod_status.setText(status)
        self.mod_status.setStyleSheet(f"color: {color};")
        
    async def connect_mod_websocket(self):
        try:
            ws_url = self.cfg["mod_settings"]["websocket_url"]
            self.log_message(f"Connecting to DumbRequestManager WebSocket at {ws_url}")
            
            while self.running:
                try:
                    async with websockets.connect(ws_url) as websocket:
                        self.mod_ws = websocket
                        self.log_message("Connected to DumbRequestManager WebSocket API")
                        QApplication.instance().callAfter(lambda: self.update_mod_status("Connected", "green"))
                        
                        while self.running:
                            try:
                                message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                                event_data = json.loads(message)
                                await self.handle_mod_event(event_data)
                            except asyncio.TimeoutError:
                                continue
                            except websockets.ConnectionClosed:
                                self.log_message("WebSocket connection closed")
                                break
                            except Exception as e:
                                self.log_message(f"Error processing WebSocket message: {str(e)}")
                                
                        self.mod_ws = None
                        if not self.running:
                            break
                except (ConnectionRefusedError, OSError) as e:
                    if not self.running:
                        break
                    self.log_message(f"WebSocket connection failed: {str(e)}. Retrying in 5 seconds...")
                    QApplication.instance().callAfter(lambda: self.update_mod_status("Reconnecting...", "orange"))
                    await asyncio.sleep(5)
                
        except Exception as e:
            self.log_message(f"WebSocket error: {str(e)}")
            QApplication.instance().callAfter(lambda: self.update_mod_status("Error", "red"))
            
    async def handle_mod_event(self, event_data):
        event_type = event_data.get("EventType")
        timestamp = event_data.get("Timestamp")
        data = event_data.get("Data")
        
        self.log_message(f"Received mod event: {event_type}")
        
        if event_type == "pressedPlay":
            if isinstance(data, dict) and "Title" in data and "Mapper" in data:
                self.log_message(f"Now playing: {data['Title']} by {data['Mapper']}")
        
        elif event_type == "queueOpen":
            state = "opened" if data else "closed"
            self.log_message(f"Song request queue was {state}")
            
    async def execute_mod_action(self, mod_action, user_input, username, twitch_channel):
        if not self.cfg.get("mod_enabled", False):
            return
            
        action_type = mod_action.get("type", "query")
        params = mod_action.get("params", {})
        http_url = self.cfg["mod_settings"]["http_url"]
        
        try:
            processed_params = {}
            for key, value in params.items():
                if isinstance(value, str):
                    processed_params[key] = value.replace("{userinput}", user_input).replace("{username}", username)
                else:
                    processed_params[key] = value
            
            response_text = None
            
            if action_type == "query":
                map_key = processed_params.get("map_key", user_input)
                if map_key:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"{http_url}/query/{map_key}") as response:
                            if response.status == 200:
                                data = await response.json()
                                if "Title" in data and "Mapper" in data:
                                    response_text = f"Map found: {data['Title']} by {data['Mapper']}"
                            else:
                                response_text = "Map not found or error occurred."
                                
            elif action_type == "addKey":
                map_key = processed_params.get("map_key", user_input)
                user = processed_params.get("user", username)
                prepend = processed_params.get("prepend", False)
                
                if map_key:
                    url = f"{http_url}/addKey/{map_key}?user={user}"
                    if prepend:
                        url += "&prepend=true"
                        
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url) as response:
                            if response.status == 200:
                                data = await response.json()
                                if "Title" in data:
                                    response_text = f"Added to queue: {data['Title']}"
                                else:
                                    response_text = "Song added to queue."
                            else:
                                response_text = "Failed to add song to queue."
                                
            elif action_type == "queue":
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{http_url}/queue") as response:
                        if response.status == 200:
                            data = await response.json()
                            if isinstance(data, list):
                                if len(data) == 0:
                                    response_text = "The queue is currently empty."
                                else:
                                    response_text = f"Queue has {len(data)} songs."
                        else:
                            response_text = "Failed to get queue information."
                            
            elif action_type == "where":
                user = processed_params.get("user", username)
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{http_url}/queue/where/{user}") as response:
                        if response.status == 200:
                            data = await response.json()
                            if isinstance(data, list) and len(data) > 0:
                                response_text = f"{user} has {len(data)} songs in queue. Next position: {data[0].get('Spot')}"
                            else:
                                response_text = f"{user} has no songs in queue."
                        else:
                            response_text = "Failed to check queue position."
                            
            elif action_type == "clear":
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{http_url}/queue/clear") as response:
                        if response.status == 200:
                            response_text = "Queue has been cleared."
                        else:
                            response_text = "Failed to clear the queue."
                            
            elif action_type == "open":
                open_value = processed_params.get("open", True)
                status = "true" if open_value else "false"
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{http_url}/queue/open/{status}") as response:
                        if response.status == 200:
                            response_text = f"Queue is now {'open' if open_value else 'closed'}."
                        else:
                            response_text = "Failed to change queue status."
                            
            elif action_type == "move":
                from_pos = processed_params.get("from", 1)
                to_pos = processed_params.get("to", 1)
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{http_url}/queue/move/{from_pos}/{to_pos}") as response:
                        if response.status == 200:
                            response_text = f"Moved queue entry from position {from_pos} to {to_pos}."
                        else:
                            response_text = "Failed to move queue entry."
                            
            elif action_type == "shuffle":
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{http_url}/queue/shuffle") as response:
                        if response.status == 200:
                            response_text = "Queue has been shuffled."
                        else:
                            response_text = "Failed to shuffle the queue."
                            
            elif action_type == "history":
                limit = processed_params.get("limit", 5)
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{http_url}/history?limit={limit}") as response:
                        if response.status == 200:
                            data = await response.json()
                            if isinstance(data, list) and len(data) > 0:
                                response_text = f"Last played: {data[0].get('HistoryItem', {}).get('Title', 'Unknown')}"
                            else:
                                response_text = "No play history available."
                        else:
                            response_text = "Failed to get play history."
            
            if response_text and twitch_channel:
                await twitch_channel.send(response_text)
                self.log_message(f"Mod action response: {response_text}")
                
        except Exception as e:
            self.log_message(f"Error executing mod action: {str(e)}")
            if twitch_channel:
                await twitch_channel.send(f"Error executing DumbRequestManager action: {str(e)}")


if __name__ == "__main__":
    app = QApplication([])
    cfg = ensure_config()
    if not cfg["tiktok_username"] or not cfg["twitch_username"] or not cfg["twitch_token"]:
        win = SetupWizard()
    else:
        win = MainWindow()
    win.show()
    app.exec()
