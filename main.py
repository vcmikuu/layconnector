import os
import json
import webbrowser
import asyncio
import threading

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QMessageBox,
    QListWidget, QDialog, QFormLayout, QDialogButtonBox,
    QInputDialog, QListWidgetItem
)
from PySide6.QtCore import Qt

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
            "actions": []
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
            "actions": []
        }
        save_config(cfg)
        QMessageBox.information(self, "Saved", "Configuration saved!")
        self.close()
        self.main = MainWindow()
        self.main.show()

class ActionDialog(QDialog):
    def __init__(self, parent=None, action=None):
        super().__init__(parent)
        self.setWindowTitle("Add/Edit Action")
        self.resize(400,200)
        self.action = action or {"trigger": "", "responses": []}
        form = QFormLayout(self)
        self.trigger_input = QLineEdit(self.action["trigger"])
        form.addRow("Trigger (e.g. !bsr abc):", self.trigger_input)
        self.responses_input = QLineEdit(";".join(self.action["responses"]))
        self.responses_input.setPlaceholderText("Separate multiple responses with ';'")
        form.addRow("Response commands:", self.responses_input)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addWidget(buttons)

    def accept(self):
        trig = self.trigger_input.text().strip()
        resps = [r.strip() for r in self.responses_input.text().split(";") if r.strip()]
        if not trig or not resps:
            QMessageBox.warning(self, "Invalid", "Trigger and at least one response required")
            return
        self.action["trigger"] = trig
        self.action["responses"] = resps
        super().accept()


class SettingsWindow(QWidget):
    def __init__(self, config, on_update):
        super().__init__()
        self.setWindowTitle("Settings - Actions")
        self.cfg = config
        self.on_update = on_update
        layout = QVBoxLayout()
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        btn_layout = QHBoxLayout()
        add = QPushButton("Add")
        edit = QPushButton("Edit")
        delete = QPushButton("Delete")
        for w, slot in [(add, self.add), (edit, self.edit), (delete, self.delete)]:
            btn_layout.addWidget(w); w.clicked.connect(slot)
        layout.addLayout(btn_layout)
        save = QPushButton("Save & Close")
        save.clicked.connect(self.on_save)
        layout.addWidget(save)
        self.setLayout(layout)
        self.refresh_list()

    def refresh_list(self):
        self.list_widget.clear()
        for act in self.cfg["actions"]:
            item = QListWidgetItem(f'{act["trigger"]} → {len(act["responses"])} responses')
            item.setData(Qt.UserRole, act)
            self.list_widget.addItem(item)

    def add(self):
        dlg = ActionDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.cfg["actions"].append(dlg.action)
            self.refresh_list()

    def edit(self):
        item = self.list_widget.currentItem()
        if not item: return
        act = item.data(Qt.UserRole)
        dlg = ActionDialog(self, action=act.copy())
        if dlg.exec() == QDialog.Accepted:
            idx = self.list_widget.row(item)
            self.cfg["actions"][idx] = dlg.action
            self.refresh_list()

    def delete(self):
        item = self.list_widget.currentItem()
        if not item: return
        idx = self.list_widget.row(item)
        del self.cfg["actions"][idx]
        self.refresh_list()

    def on_save(self):
        save_config(self.cfg)
        self.on_update(self.cfg)
        self.close()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LayConnector Dashboard")
        self.cfg = ensure_config()
        layout = QVBoxLayout()
        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self.start_connectors)
        layout.addWidget(self.start_btn)
        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self.open_settings)
        layout.addWidget(settings_btn)
        exit_btn = QPushButton("Exit")
        exit_btn.clicked.connect(QApplication.instance().quit)
        layout.addWidget(exit_btn)
        self.setLayout(layout)

    def open_settings(self):
        self.settings = SettingsWindow(self.cfg, self.on_settings_updated)
        self.settings.show()

    def on_settings_updated(self, new_cfg):
        self.cfg = new_cfg

    def start_connectors(self):
        self.start_btn.setEnabled(False)
        self.thread = threading.Thread(target=lambda: asyncio.run(self.run_async()), daemon=True)
        self.thread.start()

    async def run_async(self):
        tik = TikTokLiveClient(unique_id=self.cfg["tiktok_username"])
        bot = Bot(
            token=self.cfg["twitch_token"],
            prefix="!",
            initial_channels=[self.cfg["twitch_username"]]
        )

        @tik.on(ConnectEvent)
        async def on_tik_connect(evt):
            print(f"Connected to TikTok @{evt.unique_id}")

        @tik.on(CommentEvent)
        async def on_comment(evt):
            msg = f"{evt.user.nickname}: {evt.comment}"
            channel = bot.get_channel(self.cfg["twitch_username"])
            if channel:
                await channel.send(msg)
            for act in self.cfg["actions"]:
                if evt.comment.startswith(act["trigger"]):
                    user_input = evt.comment[len(act["trigger"]):].strip()
                    for cmd in act["responses"]:
                        out = cmd.replace("{userinput}", user_input)\
                                 .replace("{username}", evt.user.nickname)
                        if channel:
                            await channel.send(out)

        await asyncio.gather(
            tik.start(),
            bot.start()
        )

if __name__ == "__main__":
    app = QApplication([])
    cfg = ensure_config()
    if not cfg["tiktok_username"] or not cfg["twitch_username"] or not cfg["twitch_token"]:
        win = SetupWizard()
    else:
        win = MainWindow()
    win.show()
    app.exec()
