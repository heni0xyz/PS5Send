import os
import re
import socket
import time
import threading
import math
import sys
from pathlib import Path
from tkinter import messagebox
import tkinter as tk
import asyncio
from desktop_notifier import DesktopNotifier
import customtkinter as ctk
from PIL import Image
import platform

appName = "PS5Send"
appVersion = "0.0.2"
appTheme = "system"
notifier = DesktopNotifier(app_name=appName)
ctk.set_appearance_mode(appTheme)
mainColor = "#4f8df6"
secondaryColor = "#7daaf8"
backgroundColor = ("#FFFFFF", "#1a1a1e")
timeoutValue = 4
realTimeoutValue = 4

PORTS = {
    "elf": 9021,
    "jar": 9025,
    "js": 50000,
    "lua": 9026,
}


def get_base_dir():
    if getattr(sys, "frozen", False): return Path(sys.executable).parent
    return Path(__file__).parent


def get_user_data_dir() -> Path:
    if platform.system() == "Windows":
        base_path = Path(os.environ.get("APPDATA", Path.home()))
    elif platform.system() == "Darwin":
        base_path = Path.home() / "Library" / "Application Support"
    else:
        base_path = Path.home() / ".config"

    app_dir = base_path / appName
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


dataFile = get_user_data_dir() / "data.config"


def resource_path(relative_path: str) -> str:
    try:
        base_path = Path(sys._MEIPASS)
    except Exception:
        base_path = get_base_dir()
    return str(base_path / relative_path)


def is_ipv4(ip):
    if not isinstance(ip, str) or not 7 <= len(ip) <= 15: return False
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)\.(\d+)$", ip)
    if not match: return False
    a, b, c, d = map(int, match.groups())
    return a <= 255 and b <= 255 and c <= 255 and d <= 255


class DataManager:

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)

    def _read_all(self) -> dict[str, str]:
        data = {}
        if not self.file_path.exists():
            return data
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and "=" in line:
                        k, v = line.split("=", 1)
                        data[k.strip()] = v.strip()
        except Exception:
            pass
        return data

    def saveValue(self, key: str, value: str) -> None:
        try:
            data = self._read_all()
            data[key.strip()] = value.strip()
            with open(self.file_path, "w", encoding="utf-8") as f:
                for k, v in data.items():
                    f.write(f"{k}={v}\n")
        except Exception:
            pass

    def loadValue(self, key: str, default: str = "") -> str:
        data = self._read_all()
        return data.get(key.strip(), default)

    def get_custom_files(self) -> list[str]:
        raw = self.loadValue("CUSTOM_FILES", "")
        if not raw:
            return []
        return [path for path in raw.split(";") if path.strip()]

    def save_custom_files(self, paths: list[str]) -> None:
        self.saveValue("CUSTOM_FILES", ";".join(paths))


def send_payload_worker(ip, port, file_path_str, active_socket_container=None, cancel_flag=None):
    if cancel_flag and cancel_flag["canceled"]:
        return "canceled"

    if not is_ipv4(ip): return "invalid_ip"
    if file_path_str.startswith("⭐ "): file_path_str = file_path_str[2:]

    base_dir = get_base_dir()
    path_obj = Path(file_path_str)
    if not path_obj.is_absolute():
        path_obj = base_dir / file_path_str

    if path_obj.suffix.lower() == ".aelf":
        if not path_obj.exists(): return "file_not_found"
        try:
            with open(path_obj, "r", encoding="utf-8") as f:
                for line in f:
                    if cancel_flag and cancel_flag["canceled"]: return "canceled"
                    line = line.strip()
                    if not line: continue
                    if line.startswith(":"):
                        try:
                            ms = int(line[1:])
                            steps = max(1, ms // 100)
                            for _ in range(steps):
                                if cancel_flag and cancel_flag["canceled"]: return "canceled"
                                time.sleep((ms / 1000.0) / steps)
                        except ValueError:
                            pass
                    else:
                        result = send_payload_worker(ip, port, str(base_dir / line), active_socket_container, cancel_flag)
                        if result != "success": return result

            DataManager(dataFile).saveValue("IP", ip)
            return "success"
        except Exception:
            return "error"

    if not path_obj.exists(): return "file_not_found"

    try:
        with open(path_obj, "rb") as f: payload = f.read()

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            if active_socket_container is not None:
                active_socket_container["socket"] = client

            client.settimeout(realTimeoutValue)

            try:
                client.connect((ip, port))
            except (socket.timeout, TimeoutError):
                return "timeout"
            except ConnectionRefusedError:
                return "connection_refused"
            except OSError:
                return "canceled" if (cancel_flag and cancel_flag["canceled"]) else "connection_error"

            try:
                client.sendall(payload)
            except (socket.timeout, TimeoutError):
                return "timeout"
            except OSError:
                return "canceled" if (cancel_flag and cancel_flag["canceled"]) else "connection_error"

        DataManager(dataFile).saveValue("IP", ip)
        return "success"

    except FileNotFoundError:
        return "file_not_found"
    except Exception as e:
        print("Worker error:", e)
        return "error"


class PS5SendApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.active_socket_container = {"socket": None}
        self.cancel_flag = {"canceled": False}
        self.is_sending = False

        def changeTimeout(value):
            global timeoutValue, realTimeoutValue
            timeoutValue = math.floor(value)
            if timeoutValue == 4:
                self.timeout_label.configure(text="Timeout " + str(timeoutValue) + "s (default)")
                realTimeoutValue = 4
            elif timeoutValue == 16:
                self.timeout_label.configure(text="Disabled timeout")
                realTimeoutValue = None
            else:
                self.timeout_label.configure(text="Timeout " + str(timeoutValue) + "s")
                realTimeoutValue = timeoutValue

        self.custom_payloads = {}
        self.db = DataManager(dataFile)
        self.last_selected_payload = None

        def changeTheme():
            global appTheme
            if appTheme == "system":
                appTheme = "light"
                self.theme_image_button.configure(image=self.theme_image)
            elif appTheme == "light":
                appTheme = "dark"
            elif appTheme == "dark":
                appTheme = "system"
                self.theme_image_button.configure(image=self.autotheme_image)
            ctk.set_appearance_mode(appTheme)

        self.title(f"{appName} {appVersion}")
        self.geometry("400x550")
        self.configure(fg_color=backgroundColor)
        self.resizable(False, False)
        if platform.system() == "Windows":
            ico_path = resource_path("PS5Send.ico")
            if Path(ico_path).exists():
                self.iconbitmap(ico_path)

        self.ip_label = ctk.CTkLabel(self, text="PS5 IP", font=ctk.CTkFont(size=26, weight="bold"), anchor="w", width=300, height=50)
        self.ip_label.place(x=50, y=35)

        self.ip_entry = ctk.CTkEntry(self, font=ctk.CTkFont(size=16), width=300, height=40)
        self.ip_entry.place(x=50, y=85)
        lastIP = self.db.loadValue("IP")
        if lastIP: self.ip_entry.insert(0, lastIP)

        self.payload_label = ctk.CTkLabel(self, text="Payload", font=ctk.CTkFont(size=26, weight="bold"), anchor="w", width=300, height=50)
        self.payload_label.place(x=50, y=150)

        payloads = ["No payload selected"]
        target_dir = get_base_dir()

        if target_dir.exists():
            for file_path in target_dir.iterdir():
                if file_path.is_file():
                    filename = file_path.name
                    ext = file_path.suffix.lower()

                    if ext == ".aelf":
                        payloads.append("⭐ " + filename)
                    elif ext in [".elf", ".jar", ".js", ".lua"]:
                        payloads.append(filename)

        saved_paths = self.db.get_custom_files()
        valid_paths = []
        for path_str in saved_paths:
            p = Path(path_str)
            if p.exists() and p.is_file():
                display_name = f"📄 {p.name}" if p.suffix.lower() != ".aelf" else f"⭐ {p.name}"
                self.custom_payloads[display_name] = str(p)
                payloads.append(display_name)
                valid_paths.append(str(p))

        if len(saved_paths) != len(valid_paths):
            self.db.save_custom_files(valid_paths)

        payloads.append("📁 Browse files...")
        payloads.append("❌ Delete payload from list")

        self.autotheme_image = ctk.CTkImage(light_image=Image.open(resource_path("assets/auto.png")), dark_image=Image.open(resource_path("assets/auto.png")), size=(32, 32))
        self.theme_image = ctk.CTkImage(light_image=Image.open(resource_path("assets/sun.png")), dark_image=Image.open(resource_path("assets/sun.png")), size=(32, 32))

        if appTheme == "system":
            self.theme_image_button = ctk.CTkButton(self, width=32, height=32, fg_color="transparent", image=self.autotheme_image, text="", hover_color=mainColor, command=changeTheme)
        else:
            self.theme_image_button = ctk.CTkButton(self, width=32, height=32, fg_color="transparent", image=self.theme_image, text="", hover_color=mainColor, command=changeTheme)
        self.theme_image_button.place(x=0, y=508)

        self.combobox = ctk.CTkComboBox(self, values=payloads, font=ctk.CTkFont(size=14), width=300, height=40, button_color=mainColor, button_hover_color=secondaryColor, state="readonly", command=self.on_payload_select)
        self.combobox.place(x=50, y=200)
        self.combobox.set("No payload selected")

        self.timeout_label = ctk.CTkLabel(self, text="Timeout " + str(timeoutValue) + "s (default)", font=ctk.CTkFont(size=26, weight="bold"), anchor="w", width=300, height=50)
        self.timeout_label.place(x=50, y=265)

        self.slider = ctk.CTkSlider(self, width=300, height=16, from_=1, to=16, number_of_steps=15, progress_color=secondaryColor, button_color=mainColor, button_hover_color=secondaryColor, command=changeTimeout)
        self.slider.place(x=50, y=320)
        self.slider.set(4)

        self.github_label = ctk.CTkLabel(self, text="https://github.com/heni0xyz/PS5Send", font=ctk.CTkFont(size=14), cursor="hand2", width=300, height=20)
        self.github_label.place(x=50, y=380)
        self.github_label.bind("<Button-1>", self.openHyperlink)

        self.button = ctk.CTkButton(self, text="Send Payload", font=ctk.CTkFont(size=20, weight="bold"), command=self.on_send_click, width=220, height=64, fg_color=mainColor, hover_color=secondaryColor)
        self.button.place(x=90, y=440)

        self.progressbar = ctk.CTkProgressBar(self, width=220, height=10, mode="indeterminate", progress_color=mainColor, indeterminate_speed=2, fg_color=secondaryColor, orientation="horizontal")

        if platform.system() == "Darwin":
            self.createcommand("tk::mac::ReopenApplication", self.on_mac_reopen)
            self.createcommand("tk::mac::OpenDocument", self.on_mac_open_document)

        if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
            self.after(200, lambda: self.load_external_file(sys.argv[1]))

    def on_mac_reopen(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def on_mac_open_document(self, *args):
        for file_path in args:
            self.load_external_file(file_path)
        self.deiconify()
        self.lift()
        self.focus_force()

    def load_external_file(self, file_path: str):
        path_obj = Path(file_path)
        if not path_obj.exists() or not path_obj.is_file():
            return

        full_path_str = str(path_obj.resolve())
        display_name = f"📄 {path_obj.name}" if path_obj.suffix.lower() != ".aelf" else f"⭐ {path_obj.name}"

        self.custom_payloads[display_name] = full_path_str

        current_values = list(self.combobox._values)
        if display_name not in current_values:
            insert_idx = max(0, len(current_values) - 2)
            current_values.insert(insert_idx, display_name)
            self.combobox.configure(values=current_values)

        current_saved = self.db.get_custom_files()
        if full_path_str not in current_saved:
            current_saved.append(full_path_str)
            self.db.save_custom_files(current_saved)

        self.last_selected_payload = display_name
        self.combobox.set(display_name)

    def on_payload_select(self, choice):
        if choice == "❌ Delete payload from list":
            target = self.last_selected_payload
            
            if not target or target in ["📁 Browse files...", "❌ Delete payload from list", "No payload selected"]:
                self.combobox.set("No payload selected")
                self.last_selected_payload = None
                return

            current_values = list(self.combobox._values)
            if target in current_values:
                current_values.remove(target)
                self.combobox.configure(values=current_values)

            if target in self.custom_payloads:
                removed_path = self.custom_payloads.pop(target)
                saved_paths = self.db.get_custom_files()
                if removed_path in saved_paths:
                    saved_paths.remove(removed_path)
                    self.db.save_custom_files(saved_paths)

            self.last_selected_payload = None
            self.combobox.set("No payload selected")
            return

        if choice == "📁 Browse files...":
            file_path = ctk.filedialog.askopenfilename(
                title="Select Payload File",
                filetypes=[
                    ("Supported Payloads", "*.elf *.aelf *.jar *.js *.lua"),
                    ("ELF files", "*.elf"),
                    ("Automation ELF files", "*.aelf"),
                    ("JAR files", "*.jar"),
                    ("JS files", "*.js"),
                    ("Lua files", "*.lua"),
                    ("All files", "*.*")
                ]
            )
            if file_path:
                path_obj = Path(file_path)
                display_name = f"📄 {path_obj.name}" if path_obj.suffix.lower() != ".aelf" else f"⭐ {path_obj.name}"
                full_path_str = str(path_obj)

                self.custom_payloads[display_name] = full_path_str

                current_values = list(self.combobox._values)
                if display_name not in current_values:
                    insert_idx = len(current_values) - 2 if len(current_values) >= 2 else 0
                    current_values.insert(insert_idx, display_name)
                    self.combobox.configure(values=current_values)

                current_saved = self.db.get_custom_files()
                if full_path_str not in current_saved:
                    current_saved.append(full_path_str)
                    self.db.save_custom_files(current_saved)

                self.last_selected_payload = display_name
                self.combobox.set(display_name)
            else:
                fallback = self.last_selected_payload if self.last_selected_payload else "No payload selected"
                self.combobox.set(fallback)
            return

        if choice == "No payload selected":
            self.last_selected_payload = None
        else:
            self.last_selected_payload = choice

    def openHyperlink(self, event):
        self.clipboard_clear()
        self.clipboard_append("https://github.com/heni0xyz/PS5Send")

        asyncio.run(notifier.send(
            title="Copied to clipboard",
            message="https://github.com/heni0xyz/PS5Send"
        ))

    def on_cancel_click(self):
        self.cancel_flag["canceled"] = True
        sock = self.active_socket_container.get("socket")
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass

    def send_payload_thread(self, ip, port, selected_text):
        result = send_payload_worker(
            ip, port, selected_text, 
            active_socket_container=self.active_socket_container, 
            cancel_flag=self.cancel_flag
        )

        self.progressbar.stop()
        self.progressbar.place_forget()
        self.is_sending = False
        self.button.configure(text="Send Payload", command=self.on_send_click)

        if result == "canceled":
            title = "Canceled"
            message = "Payload transfer was canceled by user."
        elif result == "success":
            title = "Payload sent"
            message = f"{Path(selected_text).name} was sent to: {ip}"
        else:
            title = "Request failed"
            message = f"The connection to {ip}:{port} failed."

        asyncio.run(notifier.send(
            title=title,
            message=message
        ))

    def on_send_click(self):
        selected_text = self.combobox.get()

        if not selected_text or selected_text in ["No payload selected", "📁 Browse files...", "❌ Delete payload from list"]:
            return

        file_to_send = self.custom_payloads.get(selected_text, selected_text)

        ip = self.ip_entry.get().strip()
        port = PORTS["elf"]

        lower_text = file_to_send.lower()
        if ".jar" in lower_text: port = PORTS["jar"]
        elif ".js" in lower_text: port = PORTS["js"]
        elif ".lua" in lower_text: port = PORTS["lua"]
        elif ".elf" in lower_text or ".aelf" in lower_text: port = PORTS["elf"]

        self.cancel_flag["canceled"] = False
        self.active_socket_container["socket"] = None
        self.is_sending = True
        self.button.configure(text="Cancel", command=self.on_cancel_click)

        self.progressbar.place(x=90, y=525)
        self.progressbar.start()

        threading.Thread(
            target=self.send_payload_thread,
            args=(ip, port, file_to_send),
            daemon=True
        ).start()


if __name__ == "__main__":
    app = PS5SendApp()
    app.mainloop()