import sys
import os
import locale
import subprocess
import requests
from PIL import Image, ImageDraw, ImageFilter

from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QComboBox, 
                             QProgressBar, QTextEdit, QMessageBox, QSlider, 
                             QRadioButton, QButtonGroup, QGroupBox)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPalette, QBrush
import minecraft_launcher_lib

# Lokalizacja wykonywalna
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BG_PATH = os.path.join(BASE_DIR, "background.png")
ICON_PATH = os.path.join(BASE_DIR, "app_icon.ico")
MINECRAFT_DIR = minecraft_launcher_lib.utils.get_minecraft_directory()

# Słownik Tłumaczeń (PL / EN)
TRANSLATIONS = {
    "PL": {
        "title_sub": "N E X T - G E N   M I N E C R A F T   C L I E N T",
        "profile": "1. PROFIL GRACZA",
        "nick": "NICKNAME / NAZWA GRACZA",
        "engine": "2. SILNIK GRAFIKI / MODY",
        "mc_ver": "WERSJA MINECRAFT",
        "mod_loader": "TYP SILNIKA",
        "opt": "3. OPTYMALIZACJA & MODY",
        "ram": "PRZYDZIELONY RAM: {} GB",
        "mods": "MODRINTH MODS (SLUGS, SEPAROWANE PRZECINKIEM)",
        "status_ready": "STATUS: GOTOWY",
        "launch_btn": "URUCHOM GRAJ",
        "lang_label": "JĘZYK / LANGUAGE",
        "err_nick": "Podaj swój nick!",
        "log_start_mc": "[WERSJA] Pobieranie czystego Minecrafta {}...",
        "log_start_fabric": "[FABRIC] Pobieranie i instalacja Fabric dla {}...",
        "log_start_forge": "[FORGE] Pobieranie i instalacja Forge dla {}...",
        "log_download_mod": "[MODRINTH] Pobieranie moda: {}...",
        "log_game_start": "[GRA] Uruchamianie wersji: {}..."
    },
    "EN": {
        "title_sub": "N E X T - G E N   M I N E C R A F T   C L I E N T",
        "profile": "1. PLAYER PROFILE",
        "nick": "PLAYER NICKNAME",
        "engine": "2. GAME ENGINE / MODS",
        "mc_ver": "MINECRAFT VERSION",
        "mod_loader": "ENGINE TYPE",
        "opt": "3. OPTIMIZATION & MODS",
        "ram": "ALLOCATED RAM: {} GB",
        "mods": "MODRINTH MODS (SLUGS, SEPARATED BY COMMA)",
        "status_ready": "STATUS: READY",
        "launch_btn": "LAUNCH GAME",
        "lang_label": "LANGUAGE",
        "err_nick": "Please enter your username!",
        "log_start_mc": "[VERSION] Downloading vanilla Minecraft {}...",
        "log_start_fabric": "[FABRIC] Installing Fabric for {}...",
        "log_start_forge": "[FORGE] Installing Forge for {}...",
        "log_download_mod": "[MODRINTH] Downloading mod: {}...",
        "log_game_start": "[GAME] Launching version: {}..."
    }
}


def detect_system_language():
    """Wykrywa język systemu (Domyślnie PL jeśli język polski, inaczej EN)"""
    try:
        sys_lang, _ = locale.getdefaultlocale()
        if sys_lang and sys_lang.startswith("pl"):
            return "PL"
    except Exception:
        pass
    return "EN"


def generate_resources():
    if not os.path.exists(ICON_PATH):
        sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
        images = []
        for size in sizes:
            w, h = size
            img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            margin = int(w * 0.04)
            rect = [margin, margin, w - margin, h - margin]
            draw.rounded_rectangle(rect, radius=int(w * 0.25), fill=(13, 16, 27, 255), outline=(0, 240, 255, 255), width=max(1, int(w * 0.04)))
            stroke_w = max(2, int(w * 0.10))
            draw.line([(w * 0.5, h * 0.20), (w * 0.24, h * 0.78)], fill=(0, 240, 255, 255), width=stroke_w)
            draw.line([(w * 0.5, h * 0.20), (w * 0.76, h * 0.78)], fill=(255, 0, 127, 255), width=stroke_w)
            draw.line([(w * 0.35, h * 0.58), (w * 0.65, h * 0.58)], fill=(0, 240, 255, 255), width=max(1, int(stroke_w * 0.8)))
            images.append(img)
        images[0].save(ICON_PATH, format="ICO", sizes=[i.size for i in images], append_images=images[1:])

    if not os.path.exists(BG_PATH):
        w, h = 1280, 800
        img = Image.new("RGB", (w, h), (8, 10, 18))
        glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(glow)
        gdraw.ellipse([700, -100, 1300, 500], fill=(0, 180, 216, 80))
        gdraw.ellipse([-200, 300, 500, 900], fill=(114, 9, 183, 90))
        glow = glow.filter(ImageFilter.GaussianBlur(60))
        img.paste(glow, (0, 0), glow)
        draw = ImageDraw.Draw(img)
        for x in range(0, w, 30):
            draw.line([(x, 0), (x, h)], fill=(255, 255, 255, 8))
        for y in range(0, h, 30):
            draw.line([(0, y), (w, y)], fill=(255, 255, 255, 8))
        img.save(BG_PATH, "PNG")


class ModrinthManager:
    @staticmethod
    def download_mod(mod_slug, mc_version, mod_loader, mods_folder):
        os.makedirs(mods_folder, exist_ok=True)
        url = f"https://api.modrinth.com/v2/project/{mod_slug}/version"
        if mod_loader.lower() == "vanilla":
            return False, "N/A"

        params = {"game_versions": f'["{mc_version}"]', "loaders": f'["{mod_loader.lower()}"]'}
        headers = {'User-Agent': 'AetherLauncher/3.0'}

        try:
            response = requests.get(url, params=params, headers=headers)
            if response.status_code == 200 and response.json():
                primary_file = response.json()[0]['files'][0]
                file_path = os.path.join(mods_folder, primary_file['filename'])
                if os.path.exists(file_path):
                    return True, f"Mod {primary_file['filename']} exists."
                mod_data = requests.get(primary_file['url'], headers=headers).content
                with open(file_path, 'wb') as f:
                    f.write(mod_data)
                return True, f"Downloaded: {primary_file['filename']}"
            return False, f"Mod '{mod_slug}' not found."
        except Exception as e:
            return False, str(e)


class WorkerThread(QThread):
    progress_max = pyqtSignal(int)
    progress_value = pyqtSignal(int)
    status_text = pyqtSignal(str)
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, version, username, mod_loader, ram_gb, auto_mods, lang_code):
        super().__init__()
        self.version = version
        self.username = username
        self.mod_loader = mod_loader
        self.ram_gb = ram_gb
        self.auto_mods = auto_mods
        self.lang = TRANSLATIONS[lang_code]

    def run(self):
        callback = {
            "setStatus": lambda t: (self.status_text.emit(t), self.log_signal.emit(f"[STATUS] {t}")),
            "setProgress": lambda v: self.progress_value.emit(v),
            "setMax": lambda m: self.progress_max.emit(m)
        }

        try:
            target_version = self.version
            self.log_signal.emit(self.lang["log_start_mc"].format(self.version))
            minecraft_launcher_lib.install.install_minecraft_version(self.version, MINECRAFT_DIR, callback=callback)

            if self.mod_loader == "Fabric":
                self.log_signal.emit(self.lang["log_start_fabric"].format(self.version))
                minecraft_launcher_lib.fabric.install_fabric(self.version, MINECRAFT_DIR, callback=callback)
                installed = minecraft_launcher_lib.utils.get_installed_versions(MINECRAFT_DIR)
                fabric_versions = [v["id"] for v in installed if "fabric" in v["id"].lower() and self.version in v["id"]]
                if fabric_versions:
                    target_version = fabric_versions[0]

            elif self.mod_loader == "Forge":
                self.log_signal.emit(self.lang["log_start_forge"].format(self.version))
                forge_version = minecraft_launcher_lib.forge.find_forge_version(self.version)
                if forge_version:
                    minecraft_launcher_lib.forge.install_forge_version(forge_version, MINECRAFT_DIR, callback=callback)
                    installed = minecraft_launcher_lib.utils.get_installed_versions(MINECRAFT_DIR)
                    forge_versions = [v["id"] for v in installed if "forge" in v["id"].lower() and self.version in v["id"]]
                    if forge_versions:
                        target_version = forge_versions[0]

            if self.mod_loader in ["Fabric", "Forge"]:
                mods_folder = os.path.join(MINECRAFT_DIR, "mods")
                user_mods = [m.strip() for m in self.auto_mods.split(",") if m.strip()]
                if self.mod_loader == "Fabric" and "fabric-api" not in user_mods:
                    user_mods.insert(0, "fabric-api")

                for mod_slug in user_mods:
                    self.log_signal.emit(self.lang["log_download_mod"].format(mod_slug))
                    _, msg = ModrinthManager.download_mod(mod_slug, self.version, self.mod_loader, mods_folder)
                    self.log_signal.emit(f"[MOD] {msg}")

            options = {
                "username": self.username,
                "uuid": "",
                "token": "",
                "jvmArguments": [f"-Xmx{self.ram_gb}G", f"-Xms{self.ram_gb}G"]
            }

            self.log_signal.emit(self.lang["log_game_start"].format(target_version))
            command = minecraft_launcher_lib.command.get_minecraft_command(target_version, MINECRAFT_DIR, options)
            subprocess.run(command)

        except Exception as e:
            self.log_signal.emit(f"[ERROR] {str(e)}")

        self.finished_signal.emit()


class AetherLauncher(QWidget):
    def __init__(self):
        super().__init__()
        generate_resources()
        self.current_lang = detect_system_language()
        self.initUI()

    def apply_background_and_icon(self):
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))
        if os.path.exists(BG_PATH):
            pixmap = QPixmap(BG_PATH)
            if not pixmap.isNull():
                palette = QPalette()
                palette.setBrush(QPalette.ColorRole.Window, QBrush(pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)))
                self.setPalette(palette)
                self.setAutoFillBackground(True)

    def initUI(self):
        self.setWindowTitle("Aether Launcher • Next-Gen Client")
        self.setFixedSize(620, 800)
        self.apply_background_and_icon()

        self.setStyleSheet("""
            QGroupBox {
                background-color: rgba(14, 18, 30, 0.85);
                border: 1px solid rgba(0, 240, 255, 0.3);
                border-radius: 14px;
                margin-top: 15px;
                padding-top: 15px;
                font-size: 11px;
                font-weight: 800;
                color: #00f0ff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 3px 10px;
                background-color: rgba(6, 9, 15, 0.95);
                border: 1px solid rgba(0, 240, 255, 0.5);
                border-radius: 6px;
                color: #00f0ff;
            }
            QLabel { font-size: 10px; font-weight: 700; color: #a0aabe; background: transparent; }
            QLineEdit, QComboBox {
                background-color: rgba(8, 11, 18, 0.9);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 8px;
                color: #e0e6ed;
            }
            QRadioButton { color: #d1d5db; font-size: 12px; font-weight: 700; background: transparent; }
            QTextEdit { background-color: rgba(5, 7, 12, 0.95); border: 1px solid rgba(0, 240, 255, 0.25); color: #00ffaa; }
            QProgressBar { border-radius: 6px; text-align: center; background-color: rgba(8, 10, 16, 0.85); color: #fff; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00f0ff, stop:1 #ff007f); }
            QPushButton#playBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00f0ff, stop:1 #ff007f);
                color: #05070c; font-size: 16px; font-weight: 900; border-radius: 12px; padding: 12px;
            }
        """)

        layout = QVBoxLayout()

        # Wybór Języka w nagłówku
        lang_layout = QHBoxLayout()
        self.lang_label = QLabel()
        self.lang_select = QComboBox()
        self.lang_select.addItems(["PL", "EN"])
        self.lang_select.setCurrentText(self.current_lang)
        self.lang_select.currentTextChanged.connect(self.change_language)
        lang_layout.addStretch()
        lang_layout.addWidget(self.lang_label)
        lang_layout.addWidget(self.lang_select)
        layout.addLayout(lang_layout)

        # Sekcja Profilu
        self.acc_box = QGroupBox()
        acc_layout = QVBoxLayout()
        self.nickname_input = QLineEdit("AetherPlayer")
        self.lbl_nick = QLabel()
        acc_layout.addWidget(self.lbl_nick)
        acc_layout.addWidget(self.nickname_input)
        self.acc_box.setLayout(acc_layout)
        layout.addWidget(self.acc_box)

        # Sekcja Silnika
        self.game_box = QGroupBox()
        game_layout = QVBoxLayout()
        self.version_select = QComboBox()
        self.load_versions()
        
        loader_layout = QHBoxLayout()
        self.radio_vanilla = QRadioButton("Vanilla")
        self.radio_fabric = QRadioButton("Fabric")
        self.radio_forge = QRadioButton("Forge")
        self.radio_fabric.setChecked(True)
        
        self.loader_group = QButtonGroup(self)
        self.loader_group.addButton(self.radio_vanilla)
        self.loader_group.addButton(self.radio_fabric)
        self.loader_group.addButton(self.radio_forge)

        loader_layout.addWidget(self.radio_vanilla)
        loader_layout.addWidget(self.radio_fabric)
        loader_layout.addWidget(self.radio_forge)

        self.lbl_mc_ver = QLabel()
        self.lbl_mod_loader = QLabel()
        game_layout.addWidget(self.lbl_mc_ver)
        game_layout.addWidget(self.version_select)
        game_layout.addWidget(self.lbl_mod_loader)
        game_layout.addLayout(loader_layout)
        self.game_box.setLayout(game_layout)
        layout.addWidget(self.game_box)

        # Sekcja Optymalizacji i Modów
        self.adv_box = QGroupBox()
        adv_layout = QVBoxLayout()
        self.ram_label = QLabel()
        self.ram_slider = QSlider(Qt.Orientation.Horizontal)
        self.ram_slider.setMinimum(2)
        self.ram_slider.setMaximum(16)
        self.ram_slider.setValue(4)
        self.ram_slider.valueChanged.connect(self.update_ram_label)

        self.mods_input = QLineEdit("sodium, lithium")
        self.lbl_mods = QLabel()

        adv_layout.addWidget(self.ram_label)
        adv_layout.addWidget(self.ram_slider)
        adv_layout.addWidget(self.lbl_mods)
        adv_layout.addWidget(self.mods_input)
        self.adv_box.setLayout(adv_layout)
        layout.addWidget(self.adv_box)

        # Konsola i Przycisk
        self.status_label = QLabel()
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setFixedHeight(100)
        layout.addWidget(self.log_box)

        self.play_button = QPushButton()
        self.play_button.setObjectName("playBtn")
        self.play_button.clicked.connect(self.launch_game)
        layout.addWidget(self.play_button)

        self.setLayout(layout)
        self.retranslate_ui()

    def update_ram_label(self):
        lang = TRANSLATIONS[self.current_lang]
        self.ram_label.setText(lang["ram"].format(self.ram_slider.value()))

    def change_language(self, lang_code):
        self.current_lang = lang_code
        self.retranslate_ui()

    def retranslate_ui(self):
        lang = TRANSLATIONS[self.current_lang]
        self.lang_label.setText(lang["lang_label"])
        self.acc_box.setTitle(lang["profile"])
        self.lbl_nick.setText(lang["nick"])
        self.game_box.setTitle(lang["engine"])
        self.lbl_mc_ver.setText(lang["mc_ver"])
        self.lbl_mod_loader.setText(lang["mod_loader"])
        self.adv_box.setTitle(lang["opt"])
        self.lbl_mods.setText(lang["mods"])
        self.status_label.setText(lang["status_ready"])
        self.play_button.setText(lang["launch_btn"])
        self.update_ram_label()

    def load_versions(self):
        try:
            available = minecraft_launcher_lib.utils.get_available_versions(MINECRAFT_DIR)
            releases = [v['id'] for v in available if v['type'] == 'release']
            self.version_select.addItems(releases[:20])
        except Exception:
            self.version_select.addItem("1.20.1")

    def launch_game(self):
        username = self.nickname_input.text().strip()
        version = self.version_select.currentText()
        auto_mods = self.mods_input.text().strip()
        ram_gb = self.ram_slider.value()
        
        mod_loader = "Vanilla"
        if self.radio_fabric.isChecked():
            mod_loader = "Fabric"
        elif self.radio_forge.isChecked():
            mod_loader = "Forge"

        if not username:
            QMessageBox.warning(self, "Error", TRANSLATIONS[self.current_lang]["err_nick"])
            return

        self.play_button.setEnabled(False)
        self.worker = WorkerThread(version, username, mod_loader, ram_gb, auto_mods, self.current_lang)
        self.worker.progress_max.connect(self.progress_bar.setMaximum)
        self.worker.progress_value.connect(self.progress_bar.setValue)
        self.worker.status_text.connect(lambda t: self.status_label.setText(f"STATUS: {t.upper()}"))
        self.worker.log_signal.connect(self.log_box.append)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def on_finished(self):
        self.play_button.setEnabled(True)
        self.status_label.setText(TRANSLATIONS[self.current_lang]["status_ready"])
        self.progress_bar.setValue(0)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    launcher = AetherLauncher()
    launcher.show()
    sys.exit(app.exec())