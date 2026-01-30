import os
import sys
import customtkinter as ctk

import customtkinter as ctk
import json
import tkinter as tk
import soundcard as sc
import subprocess
import threading
import io
import pyperclip
import sys
import os
import main, FuncLib
import zipfile
import urllib.request
from urllib.error import URLError, HTTPError
import shutil

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from FuncLib import speak

    USE_FUNCLIB_SPEAK = True
except ImportError as error:
    print(f"Ошибка импорта FuncLib: {error}")
    USE_FUNCLIB_SPEAK = False
    from gtts import gTTS
    import pygame

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.configure(fg_color="#783518")
root.title("AudioAssistant")
root.geometry('400x600')
root.resizable(False, False)

BGColorForFirstButtoms = "#1A1A1A"
BGcolorForSettings = "#262626"

settings_visible = False
commands_visible = False
show_animation_id = None
hide_animation_id = None
current_panel = None

assistant_process = None
assistant_thread = None
is_assistant_running = False
assistant_status = "stopped"
waiting_for_keyword = False


settings_panel = ctk.CTkFrame(root,
                              fg_color="#2b2b2b",
                              width=400,
                              height=600,
                              corner_radius=0)

commands_panel = ctk.CTkFrame(root,
                              fg_color="#2b2b2b",
                              width=400,
                              height=600,
                              corner_radius=0)

settings_panel.place(x=-400, y=0)
commands_panel.place(x=-400, y=0)
settings_panel.lower()
commands_panel.lower()


class CircularAssistantButton(ctk.CTkFrame):
    def __init__(self, parent, command=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.command = command
        self.status = "stopped"
        self.is_pressed = False

        self.configure(fg_color="transparent", width=160, height=160)
        self.pack_propagate(False)

        self.canvas = tk.Canvas(self, width=160, height=160,
                                highlightthickness=0, bg="#783518")
        self.canvas.pack()

        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        self.draw_button()

    def draw_button(self):
        self.canvas.delete("all")

        if self.status == "stopped":
            outer_color = "#4682B4"
            inner_color = "#F0F0F0"
            text_color = "white"
            text = "ЗАПУСК"
        elif self.status == "starting":
            outer_color = "#FF8C00"
            inner_color = "#FFD700"
            text_color = "white"
            text = "ЗАГРУЗКА"
        elif self.status == "running":
            outer_color = "#32CD32"
            inner_color = "#00FF00"
            text_color = "white"
            text = "РАБОТАЕТ"
        elif self.status == "stopping":
            outer_color = "#FF4500"
            inner_color = "#FF0000"
            text_color = "white"
            text = "ОСТАНОВКА"
        else:
            outer_color = "#4682B4"
            inner_color = "#F0F0F0"
            text_color = "white"
            text = "ЗАПУСК"

        if self.is_pressed:
            offset = 2
        else:
            offset = 0

        self.canvas.create_oval(10 + offset, 10 + offset, 150 + offset, 150 + offset,
                                fill=outer_color, outline="#1E1E1E", width=3)

        self.canvas.create_oval(40 + offset, 40 + offset, 120 + offset, 120 + offset,
                                fill=inner_color, outline="")

        self.canvas.create_text(80 + offset, 80 + offset, text=text,
                                fill=text_color, font=("Arial", 12, "bold"))

    def on_click(self, event):
        self.is_pressed = True
        self.draw_button()

    def on_release(self, event):
        self.is_pressed = False
        self.draw_button()
        if self.command:
            self.command()

    def set_status(self, status):
        self.status = status
        self.draw_button()


class ConsoleOutput(io.StringIO):
    def __init__(self, text_widget, original_stdout, status_callback):
        super().__init__()
        self.text_widget = text_widget
        self.original_stdout = original_stdout
        self.status_callback = status_callback

    def write(self, text):
        self.original_stdout.write(text)

        self.text_widget.insert("end", text)
        self.text_widget.see("end")
        self.text_widget.update_idletasks()

        if "Ожидание ключевого слова:" in text or "ожидание ключевого слова:" in text:
            self.status_callback("running")

    def flush(self):
        self.original_stdout.flush()


def test_voice(voice_id, voice_name):
    if USE_FUNCLIB_SPEAK:
        try:
            if voice_id == 0:
                text = f"Я {voice_name} и это первый голос"
            elif voice_id == 1:
                text = f"Я {voice_name} и это второй голос"
            elif voice_id == 2:
                text = f"Я {voice_name} и это третий голос"
            elif voice_id == 3:
                text = f"Я {voice_name} и это четвёртый голос"
            else:
                text = f"Я {voice_name} и это голос номер {voice_id + 1}"
            speak(text, voice=voice_id)

        except Exception as error:
            print(f"Ошибка воспроизведения голоса через FuncLib: {error}")
            fallback_voice_test(voice_id, voice_name)
    else:
        fallback_voice_test(voice_id, voice_name)


def fallback_voice_test(voice_id, voice_name):
    try:
        if voice_id == 0:
            text = f"Я {voice_name} и это первый голос"
        elif voice_id == 1:
            text = f"Я {voice_name} и это второй голос"
        elif voice_id == 2:
            text = f"Я {voice_name} и это третий голос"
        elif voice_id == 3:
            text = f"Я {voice_name} и это четвёртый голос"
        else:
            text = f"Я {voice_name} и это голос номер {voice_id + 1}"

        tts = gTTS(text=text, lang='ru')
        tts.save("test_voice.mp3")

        pygame.mixer.init()
        pygame.mixer.music.load("test_voice.mp3")
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            pass

        os.remove("test_voice.mp3")

    except Exception as error:
        print(f"Ошибка воспроизведения голоса (fallback): {error}")


def download_large_model():
    try:
        model_url = "https://alphacephei.com/vosk/models/vosk-model-ru-0.42.zip"

        models_dir = "models"
        zip_path = os.path.join(models_dir, "vosk-model-ru-0.42.zip")

        if not os.path.exists(models_dir):
            os.makedirs(models_dir, exist_ok=True)
            console_text.insert("end", f"Создана папка: {models_dir}\n")

        expected_dir = os.path.join(models_dir, "vosk-model-ru-0.42")
        if os.path.exists(expected_dir):
            console_text.insert("end", "Большая модель уже установлена!\n")
            return

        console_text.insert("end", "Начинаю загрузку большой модели...\n")
        console_text.insert("end", f"Ссылка: {model_url}\n")
        console_text.insert("end", f"Сохраняю в: {zip_path}\n")

        def show_progress(block_num, block_size, total_size):
            downloaded = block_num * block_size

            downloaded_mb = downloaded / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)

            percent = min(100, int(downloaded * 100 / total_size))

            if block_num % 10 == 0:
                downloaded_str = f"{downloaded_mb:.2f}"
                total_str = f"{total_mb:.2f}"

                console_text.insert("end", f"Загружено: {percent}% ({downloaded_str}/{total_str} МБ)\n")
                console_text.see("end")

        urllib.request.urlretrieve(model_url, zip_path, show_progress)
        console_text.insert("end", "Файл успешно скачан!\n")

        console_text.insert("end", "Распаковываю архив...\n")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(models_dir)
        console_text.insert("end", "Архив успешно распакован!\n")

        os.remove(zip_path)
        console_text.insert("end", "Архив удален\n")

        if os.path.exists(expected_dir):
            console_text.insert("end", f"Модель успешно установлена в: {expected_dir}\n")
        else:
            extracted_items = os.listdir(models_dir)
            console_text.insert("end", f"В папке models теперь: {extracted_items}\n")

        console_text.insert("end", "Готово! Модель установлена.\n")

        refresh_models_list()

    except HTTPError as error:
        console_text.insert("end", f"Ошибка HTTP при скачивании: {error.code} {error.reason}\n")
    except URLError as error:
        console_text.insert("end", f"Ошибка сети: {error.reason}\n")
    except zipfile.BadZipFile:
        console_text.insert("end", "Ошибка: поврежденный zip файл\n")
    except Exception as error:
        console_text.insert("end", f"Неожиданная ошибка: {str(error)}\n")

def start_assistant():
    global is_assistant_running, assistant_status, assistant_process, assistant_thread, waiting_for_keyword

    if is_assistant_running:
        return

    assistant_status = "starting"
    waiting_for_keyword = False
    circular_btn.set_status("starting")
    status_label.configure(text="Статус: Загрузка...")

    console_text.delete("1.0", "end")
    console_text.insert("end", "=== Запуск Audio Assistant ===\n")

    assistant_thread = threading.Thread(target=run_assistant, daemon=True)
    assistant_thread.start()


def stop_assistant():
    global is_assistant_running, assistant_status, waiting_for_keyword

    if not is_assistant_running:
        return

    assistant_status = "stopping"
    waiting_for_keyword = False
    circular_btn.set_status("stopping")
    status_label.configure(text="Статус: Останавливается...")
    console_text.insert("end", "\nОстановка Audio Assistant\n")

    if assistant_process:
        assistant_process.terminate()
        try:
            assistant_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            assistant_process.kill()


def restart_assistant():
    global is_assistant_running

    if is_assistant_running:
        stop_assistant()
        root.after(1000, start_assistant)
    else:
        start_assistant()


def run_assistant():
    global is_assistant_running, assistant_status, assistant_process, waiting_for_keyword

    try:
        if not os.path.exists("main.py"):
            update_status("stopped", "Ошибка: main.py не найден!")
            console_text.insert("end", "ОШИБКА: файл main.py не найден!\n")
            return

        console_text.insert("end", "Запуск main.py...\n")

        assistant_process = subprocess.Popen(
            [sys.executable, "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            encoding='utf-8'
        )

        is_assistant_running = True

        for line in iter(assistant_process.stdout.readline, ''):
            if line:
                console_text.insert("end", line)
                console_text.see("end")
                console_text.update_idletasks()

                if "Ожидание ключевого слова:" in line or "ожидание ключевого слова:" in line:
                    waiting_for_keyword = True
                    assistant_status = "running"
                    update_status("running", "Статус: Работает")
                    console_text.insert("end", "Audio Assistant запущен и ожидает команды\n")

        return_code = assistant_process.wait()

        is_assistant_running = False
        waiting_for_keyword = False

        if return_code == 0 or return_code == 1:
            assistant_status = "stopped"
            update_status("stopped", "Статус: Остановлен")
            console_text.insert("end", "Работа остановлена\n")
        else:
            assistant_status = "stopped"
            update_status("stopped", "Статус: Остановлен")
            console_text.insert("end", f"Работа остановлена (код завершения: {return_code})\n")

    except Exception as error:
        is_assistant_running = False
        waiting_for_keyword = False
        assistant_status = "stopped"
        error_msg = f"Работа остановлена: {str(error)}\n"
        update_status("stopped", f"Статус: Остановлен")
        console_text.insert("end", error_msg)
        console_text.insert("end", "Готов к запуску\n")


def update_status(status, message):
    circular_btn.set_status(status)
    status_label.configure(text=message)


def on_circular_button_click():
    global assistant_status

    if assistant_status == "stopped":
        start_assistant()
    elif assistant_status == "running":
        stop_assistant()
    else:
        stop_assistant()


def handle_status_change(new_status):
    global assistant_status
    if new_status == "running" and assistant_status == "starting":
        assistant_status = "running"
        update_status("running", "Статус: Работает")


def load_cfg_variables():
    try:
        cfg_path = "cfg.json"

        if not os.path.exists(cfg_path):
            with open(cfg_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
            return {}

        if os.path.getsize(cfg_path) == 0:
            return {}

        with open(cfg_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return data

    except Exception as error:
        print(f"Ошибка загрузки cfg.json: {error}")
        return {}


def save_cfg_variables(variables):
    try:
        cfg_path = "cfg.json"

        directory = os.path.dirname(cfg_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        with open(cfg_path, 'w', encoding='utf-8') as f:
            json.dump(variables, f, ensure_ascii=False, indent=2)

        print("Переменные сохранены в cfg.json")
        return True

    except Exception as error:
        print(f"Ошибка сохранения cfg.json: {error}")
        return False






def load_config():
    try:
        config_path = "config.json"
        default_config = {
            "selected_voice": 1,
            "selected_lib": "models/vosk-model-small-ru-0.22"
        }

        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                for key in default_config:
                    if key not in config:
                        config[key] = default_config[key]
                return config
        else:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            print(f"Создан файл конфигурации: {config_path}")
            return default_config
    except Exception as error:
        print(f"Ошибка загрузки конфигурации: {error}")
        return default_config


def save_config(config):
    try:
        config_path = "config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print("Конфигурация сохранена")
        return True
    except Exception as error:
        print(f"Ошибка сохранения конфигурации: {error}")
        return False


def get_available_recognition_models():
    models_dir = "models"
    available_models = []

    if not os.path.exists(models_dir):
        print(f"Папка {models_dir} не найдена. Создаю...")
        os.makedirs(models_dir, exist_ok=True)
        return available_models

    try:
        for item in os.listdir(models_dir):
            item_path = os.path.join(models_dir, item)
            if os.path.isdir(item_path):
                relative_path = f"models/{item}"
                available_models.append({
                    "name": item,
                    "path": relative_path,
                    "full_path": item_path
                })

        available_models.sort(key=lambda x: x["name"])
        return available_models
    except Exception as error:
        print(f"Ошибка получения списка моделей: {error}")
        return available_models

available_models_global = []


def refresh_models_list():
    global available_models_global
    available_models_global = get_available_recognition_models()



def get_variable_display_value(var_name, var_value):
    if var_value is None or var_value == "":
        return f"{var_name}: Тут пусто"
    else:
        return f"{var_name}: {var_value.strip()}"


def get_protection_status(is_protected):
    if is_protected:
        return "Эта переменная защищена"
    else:
        return "Эта переменная не защищена"

def lose_focus_on_background(event):
    """Функция для потери фокуса при клике на фон"""
    widget = event.widget

    if isinstance(widget, (ctk.CTkFrame, tk.Canvas, tk.Frame)):
        root.focus()

def wrap_text(text, max_chars=25):
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        if len(current_line) + len(word) + 1 > max_chars:
            if current_line:
                lines.append(current_line)
            current_line = word
        else:
            if current_line:
                current_line += " " + word
            else:
                current_line = word

    if current_line:
        lines.append(current_line)

    return '\n'.join(lines)


def clipboard_select_all(widget):
    try:
        if isinstance(widget, (ctk.CTkTextbox, tk.Text)):
            widget.tag_add("sel", "1.0", "end")
        elif isinstance(widget, (ctk.CTkEntry, tk.Entry)):
            widget.select_range(0, 'end')
            widget.icursor('end')
        return True
    except Exception as error:
        print(f"Ошибка выделения текста: {error}")
        return False


def clipboard_copy(widget):
    try:
        if isinstance(widget, (ctk.CTkTextbox, tk.Text)):
            selected_text = widget.get("sel.first", "sel.last")
        elif isinstance(widget, (ctk.CTkEntry, tk.Entry)):
            selected_text = widget.get()
        else:
            return False

        if selected_text:
            pyperclip.copy(selected_text)
            return True
    except Exception:
        try:
            if isinstance(widget, (ctk.CTkTextbox, tk.Text)):
                full_text = widget.get("1.0", "end-1c")
            elif isinstance(widget, (ctk.CTkEntry, tk.Entry)):
                full_text = widget.get()
            else:
                return False

            if full_text:
                pyperclip.copy(full_text)
                return True
        except Exception as error:
            print(f"Ошибка копирования: {error}")
    return False


def clipboard_paste(widget):
    try:
        clipboard_text = pyperclip.paste()
        if not clipboard_text:
            return False

        if isinstance(widget, (ctk.CTkTextbox, tk.Text)):
            try:
                widget.delete("sel.first", "sel.last")
                widget.insert("insert", clipboard_text)
            except Exception:
                widget.insert("insert", clipboard_text)
        elif isinstance(widget, (ctk.CTkEntry, tk.Entry)):
            try:
                widget.delete(0, 'end')
                widget.insert(0, clipboard_text)
            except Exception:
                widget.insert(tk.INSERT, clipboard_text)
        else:
            return False

        return True
    except Exception as error:
        print(f"Ошибка вставки: {error}")
        return False

def create_wrapped_label(parent, text, max_chars_per_line=40, **kwargs):
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        current_line.append(word)
        current_text = ' '.join(current_line)

        if len(current_text) > max_chars_per_line:
            if len(current_line) > 1:
                lines.append(' '.join(current_line[:-1]))
                current_line = [word]
            else:
                if len(word) > max_chars_per_line:
                    for i in range(0, len(word), max_chars_per_line):
                        lines.append(word[i:i + max_chars_per_line])
                    current_line = []
                else:
                    lines.append(' '.join(current_line))
                    current_line = []

    if current_line:
        lines.append(' '.join(current_line))

    wrapped_text = '\n'.join(lines)

    defaults = {
        'text_color': "white",
        'font': ctk.CTkFont(size=12),
        'justify': "left"
    }
    settings = {**defaults, **kwargs}

    label = ctk.CTkLabel(parent, text=wrapped_text, **settings)
    return label

def create_multiline_label(parent, text, max_lines=2, **kwargs):
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        current_line.append(word)
        current_text = ' '.join(current_line)

        if len(current_text) > 35:
            if len(current_line) > 1:
                lines.append(' '.join(current_line[:-1]))
                current_line = [word]
            else:
                lines.append(word)
                current_line = []

        if len(lines) >= max_lines:
            if current_line:
                last_line = ' '.join(current_line)
                if len(lines) == max_lines - 1:
                    if len(last_line) > 32:
                        lines.append(last_line[:32] + "...")
                    else:
                        lines.append(last_line)
                else:
                    if len(lines[-1]) > 32:
                        lines[-1] = lines[-1][:32] + "..."
            break

    if len(lines) < max_lines and current_line:
        lines.append(' '.join(current_line))

    wrapped_text = '\n'.join(lines)

    defaults = {
        'text_color': "white",
        'font': ctk.CTkFont(size=12),
        'justify': "left"
    }
    settings = {**defaults, **kwargs}

    label = ctk.CTkLabel(parent, text=wrapped_text, **settings)
    return label

def enable_text_shortcuts(widget):

    def select_all(event=None):
        clipboard_select_all(widget)
        return "break"

    def copy_text(event=None):
        clipboard_copy(widget)
        return "break"

    def paste_text(event=None):
        clipboard_paste(widget)
        return "break"

    widget.bind("<Control-a>", select_all)
    widget.bind("<Control-A>", select_all)
    widget.bind("<Control-c>", copy_text)
    widget.bind("<Control-C>", copy_text)
    widget.bind("<Control-v>", paste_text)
    widget.bind("<Control-V>", paste_text)

def load_commands_from_json():
    try:
        json_path = "commands.json"

        if not os.path.exists(json_path):
            print("Json файл не подгружен")
            return []

        if os.path.getsize(json_path) == 0:
            print("Json файл не подгружен")
            return []

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        commands = data.get("commands", [])
        if not commands:
            print("Json файл не подгружен")
            return []

        return commands

    except Exception as error:
        print(f"Json файл не подгружен: {error}")
        return []


def toggle_settings():
    global settings_visible, commands_visible, current_panel

    if commands_visible:
        hide_commands_with_animation()
        root.after(250, show_settings_with_animation)
    elif settings_visible:
        hide_settings_with_animation()
    else:
        show_settings_with_animation()


def toggle_commands():
    global settings_visible, commands_visible, current_panel

    if settings_visible:
        hide_settings_with_animation()
        root.after(250, show_commands_with_animation)
    elif commands_visible:
        hide_commands_with_animation()
    else:
        show_commands_with_animation()


def show_settings_with_animation():
    global settings_visible, show_animation_id, hide_animation_id, current_panel

    if hide_animation_id:
        root.after_cancel(hide_animation_id)
        hide_animation_id = None

    settings_panel.lift()
    current_panel = settings_panel

    def animate_show(frame=0):
        global show_animation_id
        current_x = -400 + (frame * 20)
        settings_panel.place(x=current_x, y=0)

        if frame < 20:
            show_animation_id = root.after(16, lambda: animate_show(frame + 1))
        else:
            settings_panel.place(x=0, y=0)
            settings_visible = True
            show_animation_id = None

    animate_show()


def hide_settings_with_animation():
    global settings_visible, hide_animation_id, show_animation_id

    if show_animation_id:
        root.after_cancel(show_animation_id)
        show_animation_id = None

    def animate_hide(frame=0):
        global hide_animation_id
        current_x = 0 - (frame * 20)
        settings_panel.place(x=current_x, y=0)

        if frame < 20:
            hide_animation_id = root.after(16, lambda: animate_hide(frame + 1))
        else:
            settings_panel.place(x=-400, y=0)
            settings_panel.lower()
            settings_visible = False
            hide_animation_id = None

    animate_hide()


def show_commands_with_animation():
    global commands_visible, show_animation_id, hide_animation_id, current_panel

    if hide_animation_id:
        root.after_cancel(hide_animation_id)
        hide_animation_id = None

    commands_panel.lift()
    current_panel = commands_panel

    def animate_show(frame=0):
        global show_animation_id
        current_x = -400 + (frame * 20)
        commands_panel.place(x=current_x, y=0)

        if frame < 20:
            show_animation_id = root.after(16, lambda: animate_show(frame + 1))
        else:
            commands_panel.place(x=0, y=0)
            commands_visible = True
            show_animation_id = None

    animate_show()


def hide_commands_with_animation():
    global commands_visible, hide_animation_id, show_animation_id

    if show_animation_id:
        root.after_cancel(show_animation_id)
        show_animation_id = None

    def animate_hide(frame=0):
        global hide_animation_id
        current_x = 0 - (frame * 20)
        commands_panel.place(x=current_x, y=0)

        if frame < 20:
            hide_animation_id = root.after(16, lambda: animate_hide(frame + 1))
        else:
            commands_panel.place(x=-400, y=0)
            commands_panel.lower()
            commands_visible = False
            hide_animation_id = None

    animate_hide()

def back_to_main_from_settings():
    hide_settings_with_animation()


def back_to_main_from_commands():
    hide_commands_with_animation()

def create_settings_content():
    settings_title_bar = ctk.CTkFrame(settings_panel,
                                      fg_color=BGColorForFirstButtoms,
                                      height=30,
                                      corner_radius=0)
    settings_title_bar.pack(fill="x", padx=0, pady=0)

    settings_title = create_multiline_label(settings_title_bar,
                                            text="Настройки AudioAssistant",
                                            max_lines=1,
                                            text_color="white",
                                            fg_color=BGColorForFirstButtoms,
                                            font=ctk.CTkFont(size=12, weight="bold"))
    settings_title.pack(side="left", padx=10)

    settings_back_btn = ctk.CTkButton(settings_title_bar,
                                      text="Назад",
                                      command=back_to_main_from_settings,
                                      fg_color=BGColorForFirstButtoms,
                                      hover_color="#444444",
                                      text_color="white",
                                      height=25,
                                      corner_radius=0)
    settings_back_btn.pack(side="right", padx=10)

    settings_scroll_container = ctk.CTkFrame(settings_panel,
                                             fg_color="#2b2b2b",
                                             corner_radius=0)
    settings_scroll_container.pack(fill="both", expand=True, padx=0, pady=0)

    settings_canvas = tk.Canvas(settings_scroll_container,
                                bg="#2b2b2b",
                                width=365,
                                height=550)
    settings_canvas.pack(side="left", fill="both", expand=True)

    settings_v_scrollbar = ctk.CTkScrollbar(settings_scroll_container,
                                            orientation="vertical",
                                            command=settings_canvas.yview)
    settings_v_scrollbar.pack(side="right", fill="y")

    settings_canvas.configure(yscrollcommand=settings_v_scrollbar.set)

    settings_content = ctk.CTkFrame(settings_canvas,
                                    fg_color="#2b2b2b",
                                    corner_radius=0)

    settings_canvas.create_window((0, 0), window=settings_content, anchor="nw")

    def on_settings_frame_configure(event):
        settings_canvas.configure(scrollregion=settings_canvas.bbox("all"))

    def on_settings_canvas_configure(event):
        settings_canvas.itemconfig(settings_canvas.find_all()[0], width=event.width)

    settings_content.bind("<Configure>", on_settings_frame_configure)
    settings_canvas.bind("<Configure>", on_settings_canvas_configure)

    main_title = create_multiline_label(settings_content,
                                        "Настройки приложения",
                                        max_lines=2,
                                        text_color="white",
                                        font=ctk.CTkFont(size=24, weight="bold"))
    main_title.pack(pady=(20, 30))

    functions_frame = ctk.CTkFrame(settings_content, fg_color="#333333")
    functions_frame.pack(fill="x", padx=20, pady=(0, 20))

    functions_title_frame = ctk.CTkFrame(functions_frame, fg_color="transparent")
    functions_title_frame.pack(anchor="w", padx=15, pady=10, fill="x")

    functions_label_line1 = ctk.CTkLabel(functions_title_frame,
                                         text="Создание",
                                         text_color="white",
                                         font=ctk.CTkFont(size=18, weight="bold"),
                                         anchor="w")
    functions_label_line1.pack(anchor="w")

    functions_label_line2 = ctk.CTkLabel(functions_title_frame,
                                         text="пользовательской функции",
                                         text_color="white",
                                         font=ctk.CTkFont(size=18, weight="bold"),
                                         anchor="w")
    functions_label_line2.pack(anchor="w")

    create_function_frame = ctk.CTkFrame(functions_frame, fg_color="#444444")
    create_function_frame.pack(fill="x", padx=15, pady=(0, 15))

    func_name_frame = ctk.CTkFrame(create_function_frame, fg_color="transparent")
    func_name_frame.pack(fill="x", padx=10, pady=(10, 5))

    func_name_label = create_multiline_label(func_name_frame,
                                             "(1) Имя функции:",
                                             max_lines=1,
                                             text_color="white")
    func_name_label.pack(anchor="w")

    func_name_input_frame = ctk.CTkFrame(func_name_frame, fg_color="transparent")
    func_name_input_frame.pack(fill="x", pady=(5, 0))

    func_name_entry = ctk.CTkEntry(func_name_input_frame,
                                   placeholder_text="Например: Открой нарды",
                                   width=300)
    func_name_entry.pack(side="left", fill="x", expand=True)
    enable_text_shortcuts(func_name_entry)

    file_path_frame = ctk.CTkFrame(create_function_frame, fg_color="transparent")
    file_path_frame.pack(fill="x", padx=10, pady=5)

    file_path_label = create_multiline_label(file_path_frame,
                                             "(2) Путь к файлу:",
                                             max_lines=1,
                                             text_color="white")
    file_path_label.pack(anchor="w")

    file_path_input_frame = ctk.CTkFrame(file_path_frame, fg_color="transparent")
    file_path_input_frame.pack(fill="x", pady=(5, 0))

    file_path_entry = ctk.CTkEntry(file_path_input_frame,
                                   placeholder_text="C:\\Program Files\\app.exe",
                                   width=300)
    file_path_entry.pack(side="left", fill="x", expand=True)
    enable_text_shortcuts(file_path_entry)

    def insert_variable_to_path():
        selected_var = var_combobox.get()
        if selected_var != "None" and selected_var != "Нет доступных переменных":
            current_text = file_path_entry.get()
            if current_text:
                file_path_entry.delete(0, 'end')
            file_path_entry.insert(0, f"cfg_vars['{selected_var}']")

    insert_var_btn = ctk.CTkButton(file_path_input_frame,
                                   text="{ }",
                                   width=40,
                                   command=insert_variable_to_path,
                                   fg_color="#555555",
                                   hover_color="#666666")
    insert_var_btn.pack(side="right", padx=(5, 0))

    keywords_frame = ctk.CTkFrame(create_function_frame, fg_color="transparent")
    keywords_frame.pack(fill="x", padx=10, pady=5)

    keywords_label = create_multiline_label(keywords_frame,
                                            "(3) Ключевые слова (через запятую):",
                                            max_lines=2,
                                            text_color="white")
    keywords_label.pack(anchor="w")

    keywords_input_frame = ctk.CTkFrame(keywords_frame, fg_color="transparent")
    keywords_input_frame.pack(fill="x", pady=(5, 0))

    keywords_entry = ctk.CTkEntry(keywords_input_frame,
                                  placeholder_text="открой, запусти, программа",
                                  width=300)
    keywords_entry.pack(side="left", fill="x", expand=True)
    enable_text_shortcuts(keywords_entry)

    variables_frame = ctk.CTkFrame(create_function_frame, fg_color="transparent")
    variables_frame.pack(fill="x", padx=10, pady=5)

    variables_label = create_multiline_label(variables_frame,
                                             "(4) Используй готовую переменную:",
                                             max_lines=2,
                                             text_color="white")
    variables_label.pack(anchor="w")

    cfg_vars_for_func = load_cfg_variables()
    variable_names = list(cfg_vars_for_func.keys())

    if not variable_names:
        variable_names = ["Нет доступных переменных"]

    variable_names_with_none = ["None"] + variable_names
    var_combobox = ctk.CTkComboBox(variables_frame,
                                   values=variable_names_with_none,
                                   state="readonly",
                                   width=350)
    var_combobox.pack(fill="x", pady=(5, 0))
    var_combobox.set("None")

    functionality_frame = ctk.CTkFrame(create_function_frame, fg_color="transparent")
    functionality_frame.pack(fill="x", padx=10, pady=5)

    functionality_label = create_multiline_label(functionality_frame,
                                                 "(5) Функционал:",
                                                 max_lines=1,
                                                 text_color="white")
    functionality_label.pack(anchor="w")

    functionality_options = ["None", "Открыть", "Закрыть"]
    functionality_combobox = ctk.CTkComboBox(functionality_frame,
                                             values=functionality_options,
                                             state="readonly",
                                             width=350)
    functionality_combobox.pack(fill="x", pady=(5, 0))
    functionality_combobox.set("None")


    buttons_frame = ctk.CTkFrame(create_function_frame, fg_color="transparent")
    buttons_frame.pack(fill="x", padx=10, pady=10)


    def show_error_message(message):
        error_frame = ctk.CTkFrame(create_function_frame, fg_color="#442222")
        error_frame.pack(fill="x", pady=5, padx=0)

        error_label = create_multiline_label(error_frame, message,
                                             max_lines=3,
                                             text_color="#ff8888",
                                             font=ctk.CTkFont(size=11, weight="bold"))
        error_label.pack(padx=10, pady=8)

        def remove_error():
            error_frame.destroy()

        root.after(3000, remove_error)

    def show_success_message(message):
        success_label = create_multiline_label(create_function_frame,
                                               message,
                                               max_lines=3,
                                               text_color="#00ff00",
                                               font=ctk.CTkFont(size=12, weight="bold"))
        success_label.pack(pady=5)
        root.after(3000, success_label.destroy)

    def create_custom_function():
        func_name = func_name_entry.get().strip()
        file_path = file_path_entry.get().strip()
        keywords_text = keywords_entry.get().strip()
        selected_var = var_combobox.get()
        selected_functionality = functionality_combobox.get()

        if not func_name:
            show_error_message("Введите имя функции")
            return

        if not file_path and (selected_var == "None" or selected_var == "Нет доступных переменных"):
            show_error_message("Укажите путь к файлу или выберите переменную")
            return

        if not keywords_text:
            show_error_message("Введите ключевые слова")
            return

        if selected_functionality == "None":
            show_error_message("Выберите функционал (Открыть или Закрыть)")
            return

        keywords = [kw.strip() for kw in keywords_text.split(",") if kw.strip()]

        if len(keywords) == 0:
            show_error_message("Введите хотя бы одно ключевое слово")
            return

        final_file_path = file_path
        use_variable = False

        if selected_var != "None" and selected_var != "Нет доступных переменных" and selected_var in cfg_vars_for_func:
            final_file_path = f"cfg_vars['{selected_var}']"
            use_variable = True
        elif not file_path:
            show_error_message("Укажите путь к файлу")
            return

        if selected_functionality == "Открыть":
            function_name = "AbsolutStarter"
            name_prefix = "custom_open"
        elif selected_functionality == "Закрыть":
            function_name = "AbsolutCloser"
            name_prefix = "custom_close"
        else:
            show_error_message("Неизвестный функционал")
            return

        command = {
            "nameForGUI": func_name,
            "name": f"{name_prefix}_{func_name.lower().replace(' ', '_')}",
            "keywords": keywords,
            "function": function_name,
            "args": [final_file_path],
            "protected": False
        }

        commands = load_commands_from_json()

        existing_names = [cmd.get('name', '') for cmd in commands]
        if command['name'] in existing_names:
            show_error_message(f"Функция с именем '{command['name']}' уже существует")
            return

        commands.append(command)

        try:
            with open('commands.json', 'w', encoding='utf-8') as f:
                json.dump({"commands": commands}, f, ensure_ascii=False, indent=2)

            success_msg = f"Функция '{func_name}' ({selected_functionality}) создана!"
            show_success_message(success_msg)

            func_name_entry.delete(0, 'end')
            file_path_entry.delete(0, 'end')
            keywords_entry.delete(0, 'end')
            var_combobox.set("None")
            functionality_combobox.set("None")

            if assistant_status == "running":
                console_text.insert("end", "Обнаружены новые команды, перезапуск ассистента...\n")
                restart_assistant()

        except Exception as error:
            show_error_message(f"Ошибка сохранения: {error}")

    def suggest_variable_creation():
        file_path = file_path_entry.get().strip()
        if not file_path:
            show_error_message("Сначала укажите путь к файлу")
            return

        dialog = ctk.CTkInputDialog(
            text=f"Создать переменную для пути:\n{file_path}\n\nВведите имя переменной:",
            title="Создание переменной"
        )
        var_name = dialog.get_input()

        if var_name and var_name.strip():
            var_name = var_name.strip()

            cfg_vars = load_cfg_variables()
            cfg_vars[var_name] = {
                'value': file_path,
                'protected': False
            }

            if save_cfg_variables(cfg_vars):
                updated_vars = list(cfg_vars.keys())
                var_combobox.configure(values=["None"] + updated_vars)
                var_combobox.set(var_name)

                file_path_entry.delete(0, 'end')

                show_success_message(f"Переменная '{var_name}' создана!")
            else:
                show_error_message("Ошибка создания переменной")

    create_buttons_frame = ctk.CTkFrame(buttons_frame, fg_color="transparent")
    create_buttons_frame.pack(fill="x")

    create_func_btn = ctk.CTkButton(create_buttons_frame,
                                    text="Добавить функцию",
                                    command=create_custom_function,
                                    fg_color="#444444",
                                    hover_color="#555555",
                                    height=30)
    create_func_btn.pack(side="left", padx=(0, 5))

    save_func_btn = ctk.CTkButton(create_buttons_frame,
                                  text="Сохранить",
                                  command=create_custom_function,
                                  fg_color="#00aa00",
                                  hover_color="#008800",
                                  height=30,
                                  width=120)
    save_func_btn.pack(side="left", padx=3)

    suggest_var_btn = ctk.CTkButton(create_buttons_frame,
                                    text="Создать переменную",
                                    command=suggest_variable_creation,
                                    fg_color="#444444",
                                    hover_color="#555555",
                                    height=30)
    suggest_var_btn.pack(side="left", padx=5)

    def clear_all_fields():
        func_name_entry.delete(0, 'end')
        file_path_entry.delete(0, 'end')
        keywords_entry.delete(0, 'end')
        var_combobox.set("None")
        functionality_combobox.set("None")
        show_success_message("Все поля очищены")

    clear_btn = ctk.CTkButton(create_buttons_frame,
                              text="Очистить все",
                              command=clear_all_fields,
                              fg_color="#aa0000",
                              hover_color="#880000",
                              height=30)
    clear_btn.pack(side="left", padx=5)

    functions_clipboard_frame = ctk.CTkFrame(create_function_frame, fg_color="transparent")
    functions_clipboard_frame.pack(fill="x", padx=10, pady=(10, 5))

    function_fields = [
        ("(1) Имя функции", func_name_entry),
        ("(2) Путь к файлу", file_path_entry),
        ("(3) Ключевые слова", keywords_entry),
    ]

    field_options = ["None"] + [f"({i + 1})" for i in range(len(function_fields))]
    clipboard_combobox = ctk.CTkComboBox(functions_clipboard_frame,
                                         values=field_options,
                                         state="readonly",
                                         width=100)
    clipboard_combobox.set("None")

    def get_selected_function_field():
        selected = clipboard_combobox.get()
        if selected == "None":
            return None
        try:
            field_index = int(selected.strip('()')) - 1
            if 0 <= field_index < len(function_fields):
                return function_fields[field_index][1]
        except:
            return None
        return None

    def paste_to_selected_function_field():
        selected_field = get_selected_function_field()
        if selected_field:
            if isinstance(selected_field, ctk.CTkComboBox):
                return
            else:
                clipboard_paste(selected_field)

    ctrl_v_btn = ctk.CTkButton(functions_clipboard_frame,
                               text="Ctrl + V",
                               command=paste_to_selected_function_field,
                               fg_color="#333333",
                               hover_color="#444444",
                               width=80,
                               height=25)
    ctrl_v_btn.pack(side="left", padx=(0, 5))

    def clear_selected_field():
        selected_field = get_selected_function_field()
        if selected_field:
            if isinstance(selected_field, ctk.CTkComboBox):
                selected_field.set("None")
            else:
                selected_field.delete(0, 'end')

    del_btn = ctk.CTkButton(functions_clipboard_frame,
                            text="Del",
                            command=clear_selected_field,
                            fg_color="#333333",
                            hover_color="#555555",
                            width=50,
                            height=25)
    del_btn.pack(side="left", padx=(0, 10))

    clipboard_combobox.pack(side="right")

    variables_section_frame = ctk.CTkFrame(settings_content, fg_color="#333333")
    variables_section_frame.pack(fill="x", padx=20, pady=(0, 0))

    variables_label = create_multiline_label(variables_section_frame,
                                             text="Переменные конфигурации",
                                             max_lines=2,
                                             text_color="white",
                                             font=ctk.CTkFont(size=18, weight="bold"))
    variables_label.pack(anchor="w", padx=15, pady=10)

    cfg_variables = load_cfg_variables()
    variable_entries = {}
    variable_frames = {}

    variables_display_frame = ctk.CTkFrame(variables_section_frame, fg_color="#333333")
    variables_display_frame.pack(fill="x", padx=15, pady=(0, 15))

    variables_clipboard_container = ctk.CTkFrame(variables_section_frame, fg_color="transparent")
    variables_clipboard_container.pack(fill="x", padx=15, pady=(0, 10))

    def sort_variables(variables_dict):
        protected_vars = {}
        unprotected_vars = {}

        for var_name, var_data in variables_dict.items():
            if var_data.get('protected', False):
                protected_vars[var_name] = var_data
            else:
                unprotected_vars[var_name] = var_data

        protected_sorted = dict(sorted(protected_vars.items()))
        unprotected_sorted = dict(sorted(unprotected_vars.items()))

        return {**protected_sorted, **unprotected_sorted}

    def create_variable_fields():
        nonlocal cfg_variables, variable_entries, variable_frames

        for widget in variables_display_frame.winfo_children():
            widget.destroy()

        variable_entries = {}
        variable_frames = {}

        if not cfg_variables:
            no_vars_label = ctk.CTkLabel(variables_display_frame,
                                         text="Переменные не добавлены",
                                         text_color="#888888",
                                         font=ctk.CTkFont(size=12))
            no_vars_label.pack(pady=20)
            return

        sorted_variables = sort_variables(cfg_variables)

        for idx, (var_name, var_data) in enumerate(sorted_variables.items(), 1):
            var_value = var_data.get('value', '')
            is_protected = var_data.get('protected', False)

            cleaned_value = var_value.strip() if var_value else ""

            var_frame = ctk.CTkFrame(variables_display_frame, fg_color="#444444")
            var_frame.pack(fill="x", pady=5, padx=0)
            variable_frames[var_name] = var_frame

            top_frame = ctk.CTkFrame(var_frame, fg_color="transparent")
            top_frame.pack(fill="x", padx=12, pady=(8, 5))

            top_frame.grid_columnconfigure(0, weight=1)
            top_frame.grid_columnconfigure(1, weight=0)

            value_label_text = get_variable_display_value(var_name, cleaned_value)
            if is_protected:
                display_text = f"({idx}) {value_label_text}"
            else:
                display_text = f"({idx}) {value_label_text}"

            def wrap_text_for_label(text, max_chars=30):
                words = text.split()
                lines = []
                current_line = []

                for word in words:
                    current_line.append(word)
                    current_text = ' '.join(current_line)

                    if len(current_text) > max_chars:
                        if len(current_line) > 1:
                            lines.append(' '.join(current_line[:-1]))
                            current_line = [word]
                        else:
                            lines.append(word)
                            current_line = []

                if current_line:
                    lines.append(' '.join(current_line))

                return '\n'.join(lines)

            wrapped_text = wrap_text_for_label(display_text, max_chars=25)

            value_label = ctk.CTkLabel(top_frame,
                                       text=wrapped_text,
                                       text_color="white",
                                       font=ctk.CTkFont(size=12),
                                       anchor="w",
                                       justify="left",
                                       wraplength=250)
            value_label.grid(row=0, column=0, sticky="w", padx=(0, 10))

            if is_protected:
                delete_btn = ctk.CTkButton(top_frame,
                                           text="✕",
                                           width=25,
                                           height=25,
                                           fg_color="#666666",
                                           hover_color="#666666",
                                           text_color="#999999",
                                           state="disabled")
            else:
                delete_btn = ctk.CTkButton(top_frame,
                                           text="✕",
                                           width=25,
                                           height=25,
                                           fg_color="#aa0000",
                                           hover_color="#cc0000",
                                           text_color="white",
                                           command=lambda name=var_name: delete_variable(name))
            delete_btn.grid(row=0, column=1, sticky="e")

            input_frame = ctk.CTkFrame(var_frame, fg_color="transparent")
            input_frame.pack(fill="x", padx=12, pady=(0, 8))

            entry = ctk.CTkEntry(input_frame,
                                 placeholder_text=get_protection_status(is_protected),
                                 width=300)
            entry.pack(side="left", fill="x", expand=True)
            enable_text_shortcuts(entry)

            if cleaned_value and cleaned_value != "":
                entry.insert(0, cleaned_value)

            variable_entries[var_name] = entry

    def delete_variable(var_name):
        nonlocal cfg_variables

        if var_name in cfg_variables:
            if cfg_variables[var_name].get('protected', False):
                print(f"Переменная {var_name} защищена и не может быть удалена")
                return

            del cfg_variables[var_name]
            save_cfg_variables(cfg_variables)
            create_variable_fields()
            update_variables_combobox()
            print(f"Переменная {var_name} удалена")

    def add_new_variable():
        nonlocal cfg_variables

        dialog = ctk.CTkInputDialog(text="Введите имя новой переменной:", title="Новая переменная")
        new_var_name = dialog.get_input()

        if new_var_name and new_var_name.strip():
            new_var_name = new_var_name.strip()

            if new_var_name in cfg_variables:
                show_error_message(f"Ошибка: Переменная '{new_var_name}' уже существует!")
                print(f"Нельзя создать переменную '{new_var_name}' - она уже существует")
                return

            is_protected = False


            cfg_variables[new_var_name] = {
                'value': "",
                'protected': is_protected
            }

            save_cfg_variables(cfg_variables)
            create_variable_fields()
            update_variables_combobox()
            print(f"Добавлена новая переменная: {new_var_name}")

    # Функция для сохранения всех переменных
    def save_all_variables():
        nonlocal cfg_variables

        for var_name, entry in variable_entries.items():
            new_value = entry.get().strip()
            cfg_variables[var_name]['value'] = new_value
            entry.delete(0, 'end')

        if save_cfg_variables(cfg_variables):
            success_label = create_multiline_label(variables_display_frame,
                                                   "Переменные сохранены!",
                                                   max_lines=2,
                                                   text_color="#00ff00",
                                                   font=ctk.CTkFont(size=12, weight="bold"))
            success_label.pack(pady=5)

            root.after(2000, success_label.destroy)
            create_variable_fields()
            update_variables_combobox()

    def clear_all_variables():
        nonlocal cfg_variables

        vars_to_remove = []
        for var_name, var_data in cfg_variables.items():
            if not var_data.get('protected', False):
                vars_to_remove.append(var_name)

        for var_name in vars_to_remove:
            del cfg_variables[var_name]

        save_cfg_variables(cfg_variables)
        create_variable_fields()
        update_variables_combobox()
        print(f"Удалено {len(vars_to_remove)} незащищенных переменных")

    create_variable_fields()

    variables_buttons_frame = ctk.CTkFrame(variables_section_frame, fg_color="transparent")
    variables_buttons_frame.pack(fill="x", padx=15, pady=10)

    add_var_btn = ctk.CTkButton(variables_buttons_frame,
                                text="Добавить переменную",
                                command=add_new_variable,
                                fg_color="#444444",
                                hover_color="#555555",
                                height=30)
    add_var_btn.pack(side="left", padx=(0, 5))

    save_vars_btn = ctk.CTkButton(variables_buttons_frame,
                                  text="Сохранить",
                                  command=save_all_variables,
                                  fg_color="#00aa00",
                                  hover_color="#008800",
                                  height=30,
                                  width=120)
    save_vars_btn.pack(side="left", padx=3)

    clear_vars_btn = ctk.CTkButton(variables_buttons_frame,
                                   text="Очистить все",
                                   command=clear_all_variables,
                                   fg_color="#aa0000",
                                   hover_color="#880000",
                                   height=30)
    clear_vars_btn.pack(side="left", padx=5)

    def update_variables_combobox():
        for widget in variables_clipboard_container.winfo_children():
            widget.destroy()

        variables_clipboard_frame = ctk.CTkFrame(variables_clipboard_container, fg_color="transparent")
        variables_clipboard_frame.pack(fill="x", padx=0, pady=0)

        if variable_entries:
            sorted_vars = sort_variables(cfg_variables)
            var_names_sorted = list(sorted_vars.keys())

            var_options = ["None"] + [f"({i + 1})" for i in range(len(var_names_sorted))]
            var_clipboard_combobox = ctk.CTkComboBox(variables_clipboard_frame,
                                                     values=var_options,
                                                     state="readonly",
                                                     width=100)
            var_clipboard_combobox.set("None")

            def get_selected_variable_field():
                selected = var_clipboard_combobox.get()
                if selected == "None":
                    return None
                try:
                    field_index = int(selected.strip('()')) - 1
                    if 0 <= field_index < len(var_names_sorted):
                        var_name = var_names_sorted[field_index]
                        return variable_entries.get(var_name)
                except:
                    return None
                return None

            def paste_to_selected_variable_field():
                selected_field = get_selected_variable_field()
                if selected_field:
                    clipboard_paste(selected_field)

            var_ctrl_v_btn = ctk.CTkButton(variables_clipboard_frame,
                                           text="Ctrl + V",
                                           command=paste_to_selected_variable_field,
                                           fg_color="#444444",
                                           hover_color="#444444",
                                           width=80,
                                           height=25)
            var_ctrl_v_btn.pack(side="left", padx=(0, 5))

            def clear_selected_variable_field():
                selected_field = get_selected_variable_field()
                if selected_field:
                    selected_field.delete(0, 'end')

            var_del_btn = ctk.CTkButton(variables_clipboard_frame,
                                        text="Del",
                                        command=clear_selected_variable_field,
                                        fg_color="#444444",
                                        hover_color="#555555",
                                        width=50,
                                        height=25)
            var_del_btn.pack(side="left", padx=(0, 10))

            var_clipboard_combobox.pack(side="right")
        else:
            no_vars_clipboard_label = create_multiline_label(variables_clipboard_frame,
                                                             "Добавьте переменные для использования буфера обмена",
                                                             max_lines=2,
                                                             text_color="#888888",
                                                             font=ctk.CTkFont(size=10))
            no_vars_clipboard_label.pack(pady=5)
    update_variables_combobox()

    variables_display_frame.bind("<Button-1>", lose_focus_on_background)
    variables_section_frame.bind("<Button-1>", lose_focus_on_background)

    voice_section = ctk.CTkFrame(settings_content, fg_color="#333333")
    voice_section.pack(fill="x", padx=20, pady=(15, 15))

    voice_label = create_multiline_label(voice_section,
                                         text="Выбор голоса приложения",
                                         max_lines=2,
                                         text_color="white",
                                         font=ctk.CTkFont(size=18, weight="bold"))
    voice_label.pack(anchor="w", padx=20, pady=10)

    config = load_config()
    selected_voice = config.get("selected_voice", 1)

    voices = [
        {"name": "Айдар", "id": 0, "description": "Мужской голос"},
        {"name": "Байа", "id": 1, "description": "Женский голос"},
        {"name": "Ксения", "id": 2, "description": "Женский голос"},
        {"name": "Хениа", "id": 3, "description": "Женский голос"}
    ]

    current_selected_voice = tk.IntVar(value=selected_voice)

    def save_voice_selection():
        selected_voice_id = current_selected_voice.get()
        config["selected_voice"] = selected_voice_id
        if save_config(config):
            success_label = create_multiline_label(voice_section,
                                                   f"Голос '{voices[selected_voice_id]['name']}' сохранен!",
                                                   max_lines=2,
                                                   text_color="#00ff00",
                                                   font=ctk.CTkFont(size=12, weight="bold"))
            success_label.pack(pady=5)
            root.after(2000, success_label.destroy)

    voices_container = ctk.CTkFrame(voice_section, fg_color="#444444")
    voices_container.pack(fill="x", padx=15, pady=(0, 15))

    for voice in voices:
        voice_frame = ctk.CTkFrame(voices_container, fg_color="transparent")
        voice_frame.pack(fill="x", pady=5, padx=10)

        left_frame = ctk.CTkFrame(voice_frame, fg_color="transparent")
        left_frame.pack(side="left", fill="both", expand=True)

        radio_btn = ctk.CTkRadioButton(left_frame,
                                       text=f"{voice['name']} ({voice['description']})",
                                       variable=current_selected_voice,
                                       value=voice['id'],
                                       text_color="white",
                                       fg_color="#4682B4",
                                       hover_color="#5A9BD5",
                                       command=save_voice_selection)
        radio_btn.pack(side="left", padx=(0, 10))

        right_frame = ctk.CTkFrame(voice_frame, fg_color="transparent")
        right_frame.pack(side="right", fill="y")

        test_button = ctk.CTkButton(right_frame,
                                    text="Тест",
                                    width=50,
                                    height=25,
                                    fg_color="#00aa00",
                                    hover_color="#008800",
                                    text_color="white",
                                    font=ctk.CTkFont(size=10, weight="bold"),
                                    command=lambda vid=voice['id'], vname=voice['name']: test_voice(vid, vname))
        test_button.pack(side="left")

    model_section = ctk.CTkFrame(settings_content, fg_color="#333333")
    model_section.pack(fill="x", padx=20, pady=(0, 15))

    model_label = create_multiline_label(model_section,
                                         text="Модель распознавания",
                                         max_lines=2,
                                         text_color="white",
                                         font=ctk.CTkFont(size=18, weight="bold"))
    model_label.pack(anchor="w", padx=20, pady=10)

    available_models = get_available_recognition_models()
    selected_lib = config.get("selected_lib", "models/vosk-model-small-ru-0.22")

    models_container = ctk.CTkFrame(model_section, fg_color="#444444")
    models_container.pack(fill="x", padx=15, pady=(0, 10))

    info_container = ctk.CTkFrame(model_section, fg_color="transparent")
    info_container.pack(fill="x", padx=15, pady=(0, 10))

    warning_frame = ctk.CTkFrame(info_container, fg_color="transparent")
    warning_frame.pack(fill="x", pady=(0, 5))

    warning_text = "ВНИМАНИЕ! При использовании большой модели значительно увеличиться не только качество распознания речи, но и время запуска приложения и время обработки команд."
    warning_label = create_multiline_label(warning_frame,
                                           warning_text,
                                           max_lines=5,
                                           text_color="#ff6666",
                                           font=ctk.CTkFont(size=11, weight="bold"))
    warning_label.pack(anchor="w", padx=(0, 0))

    download_button_frame = ctk.CTkFrame(model_section, fg_color="transparent")
    download_button_frame.pack(fill="x", padx=15, pady=(10, 5))

    def download_large_model_thread():
        download_thread = threading.Thread(target=download_large_model, daemon=True)
        download_thread.start()
    download_btn = ctk.CTkButton(download_button_frame,
                                 text="Скачать большую библиотеку\nдля распознавания",
                                 command=download_large_model_thread,
                                 fg_color="#444444",
                                 hover_color="#555555",
                                 height=50,
                                 font=ctk.CTkFont(size=12, weight="bold"),
                                 anchor="w")
    download_btn.pack(fill="x", pady=(5, 0))

    info_large_model_frame = ctk.CTkFrame(download_button_frame, fg_color="transparent")
    info_large_model_frame.pack(fill="x", pady=(5, 0))

    large_model_info = "Размер: ~1.8 GB\nТочность: высокая\nЯзык: русский"
    large_model_label = create_multiline_label(info_large_model_frame,
                                               large_model_info,
                                               max_lines=4,
                                               text_color="#cccccc",
                                               font=ctk.CTkFont(size=10))
    large_model_label.pack(anchor="w", padx=(0, 0))

    if available_models:
        current_selected_model = tk.StringVar(value=selected_lib)

        def save_model_selection():
            selected_model_path = current_selected_model.get()
            config["selected_lib"] = selected_model_path
            if save_config(config):
                model_name = "Неизвестная модель"
                for model in available_models:
                    if model["path"] == selected_model_path:
                        model_name = model["name"]
                        break

                success_label = create_multiline_label(model_section,
                                                       f"Модель '{model_name}' сохранена!",
                                                       max_lines=2,
                                                       text_color="#00ff00",
                                                       font=ctk.CTkFont(size=12, weight="bold"))
                success_label.pack(pady=5)
                root.after(2000, success_label.destroy)

        for model in available_models:
            model_frame = ctk.CTkFrame(models_container, fg_color="transparent")
            model_frame.pack(fill="x", pady=3, padx=10)

            left_frame = ctk.CTkFrame(model_frame, fg_color="transparent")
            left_frame.pack(side="left", fill="both", expand=True)

            radio_btn = ctk.CTkRadioButton(left_frame,
                                           text=f"{model['name']}",
                                           variable=current_selected_model,
                                           value=model['path'],
                                           text_color="white",
                                           fg_color="#4682B4",
                                           hover_color="#5A9BD5",
                                           command=save_model_selection)
            radio_btn.pack(side="left", padx=(0, 10))

            if model['path'] == selected_lib:
                radio_btn.select()

    else:
        no_models_frame = ctk.CTkFrame(models_container, fg_color="transparent")
        no_models_frame.pack(pady=10)

        no_models_label = create_multiline_label(no_models_frame,
                                                 "Модели не найдены",
                                                 max_lines=2,
                                                 text_color="#cccccc",
                                                 font=ctk.CTkFont(size=12))
        no_models_label.pack()

    model_section.bind("<Button-1>", lose_focus_on_background)
    voice_section.bind("<Button-1>", lose_focus_on_background)
    settings_content.bind("<Button-1>", lose_focus_on_background)
    settings_canvas.bind("<Button-1>", lose_focus_on_background)
    settings_scroll_container.bind("<Button-1>", lose_focus_on_background)


def create_commands_content():
    commands_list = load_commands_from_json()

    commands_title_bar = ctk.CTkFrame(commands_panel,
                                      fg_color=BGColorForFirstButtoms,
                                      height=30,
                                      corner_radius=0)
    commands_title_bar.pack(fill="x", padx=0, pady=0)

    commands_title = create_multiline_label(commands_title_bar,
                                            text="Команды AudioAssistant",
                                            max_lines=1,
                                            text_color="white",
                                            fg_color=BGColorForFirstButtoms,
                                            font=ctk.CTkFont(size=12, weight="bold"))
    commands_title.pack(side="left", padx=10)

    commands_back_btn = ctk.CTkButton(commands_title_bar,
                                      text="← Назад",
                                      command=back_to_main_from_commands,
                                      fg_color=BGColorForFirstButtoms,
                                      hover_color="#444444",
                                      text_color="white",
                                      height=25,
                                      corner_radius=0)
    commands_back_btn.pack(side="right", padx=10)


    commands_content = ctk.CTkFrame(commands_panel,
                                    fg_color="#2b2b2b",
                                    corner_radius=0)
    commands_content.pack(fill="both", expand=True, padx=0, pady=0)



    main_title = create_multiline_label(commands_content,
                                        text="Доступные команды",
                                        max_lines=2,
                                        text_color="white",
                                        font=ctk.CTkFont(size=20, weight="bold"))
    main_title.pack(pady=(15, 15))

    scroll_container = ctk.CTkFrame(commands_content, fg_color="#2b2b2b")
    scroll_container.pack(fill="both", expand=True, padx=15, pady=(0, 10))

    canvas = tk.Canvas(scroll_container,
                       bg="#2b2b2b",
                       highlightthickness=0,
                       width=370,
                       height=450)

    v_scrollbar = ctk.CTkScrollbar(scroll_container,
                                   orientation="vertical",
                                   command=canvas.yview)

    canvas.configure(yscrollcommand=v_scrollbar.set)

    canvas.grid(row=0, column=0, sticky="nsew")
    v_scrollbar.grid(row=0, column=1, sticky="ns")

    scroll_container.grid_rowconfigure(0, weight=1)
    scroll_container.grid_columnconfigure(0, weight=1)

    commands_frame = ctk.CTkFrame(canvas, fg_color="#2b2b2b", corner_radius=0)

    canvas.create_window((0, 0), window=commands_frame, anchor="nw")

    def on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def on_canvas_configure(event):
        canvas.itemconfig(canvas.find_all()[0], width=event.width)

    commands_frame.bind("<Configure>", on_frame_configure)
    canvas.bind("<Configure>", on_canvas_configure)

    def delete_command(command_name, command_frame, is_protected=False):
        if is_protected:
            print(f"Команда {command_name} защищена и не может быть удалена")
            return

        commands = load_commands_from_json()

        updated_commands = [cmd for cmd in commands if cmd.get('name') != command_name]

        try:
            with open('commands.json', 'w', encoding='utf-8') as f:
                json.dump({"commands": updated_commands}, f, ensure_ascii=False, indent=2)

            command_frame.destroy()

            update_commands_count()

            print(f"Команда {command_name} удалена")
        except Exception as error:
            print(f"Ошибка удаления команды: {error}")

    def update_commands_count():
        commands_count = len(load_commands_from_json())
        count_label.configure(text=f"Всего команд: {commands_count}")

    if commands_list:
        for command in commands_list:
            name_for_gui = command.get("nameForGUI", "Неизвестная команда")
            is_protected = command.get("protected", False)
            keywords = command.get("keywords", [])
            keywords_text = ", ".join(keywords)

            wrapped_name = wrap_text(f"• {name_for_gui}", max_chars=25)
            wrapped_keywords = wrap_text(f"Ключевые слова: {keywords_text}", max_chars=25)

            name_lines_count = len(wrapped_name.split('\n'))
            keywords_lines_count = len(wrapped_keywords.split('\n'))

            base_height = 80
            extra_name_height = max(0, (name_lines_count - 2)) * 20
            extra_keywords_height = max(0, (keywords_lines_count - 1)) * 18
            block_height = base_height + extra_name_height + extra_keywords_height

            command_frame = ctk.CTkFrame(commands_frame,
                                         fg_color="#333333",
                                         corner_radius=8,
                                         width=350,
                                         height=block_height)
            command_frame.pack(fill="x", pady=5, padx=0)
            command_frame.pack_propagate(False)

            content_container = ctk.CTkFrame(command_frame, fg_color="transparent")
            content_container.pack(fill="both", expand=True, padx=12, pady=8)

            top_frame = ctk.CTkFrame(content_container, fg_color="transparent")
            top_frame.pack(fill="x", pady=(0, 5))

            name_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
            name_frame.pack(side="left", fill="x", expand=True)

            name_label = ctk.CTkLabel(name_frame,
                                      text=wrapped_name,
                                      text_color="white",
                                      font=ctk.CTkFont(size=14, weight="bold"),
                                      anchor="w",
                                      justify="left")
            name_label.pack(fill="x", anchor="w")

            if is_protected:
                delete_btn = ctk.CTkButton(top_frame,
                                           text="✕",
                                           width=25,
                                           height=25,
                                           fg_color="#666666",
                                           hover_color="#666666",
                                           text_color="#999999",
                                           state="disabled")
            else:
                delete_btn = ctk.CTkButton(top_frame,
                                           text="✕",
                                           width=25,
                                           height=25,
                                           fg_color="#aa0000",
                                           hover_color="#cc0000",
                                           text_color="white",
                                           command=lambda name=command.get('name'), frame=command_frame,
                                                          prot=is_protected: delete_command(name, frame, prot))
            delete_btn.pack(side="right", padx=(5, 0))

            bottom_frame = ctk.CTkFrame(content_container, fg_color="transparent")
            bottom_frame.pack(fill="x")

            keywords_label = ctk.CTkLabel(bottom_frame,
                                          text=wrapped_keywords,
                                          text_color="#cccccc",
                                          font=ctk.CTkFont(size=12),
                                          anchor="w",
                                          justify="left")
            keywords_label.pack(fill="x", anchor="w")
    else:
        no_commands_frame = ctk.CTkFrame(commands_frame,
                                         fg_color="#333333",
                                         corner_radius=8,
                                         width=350,
                                         height=80)
        no_commands_frame.pack(fill="x", pady=5, padx=0)
        no_commands_frame.pack_propagate(False)

        no_commands_label = create_multiline_label(no_commands_frame,
                                                   "Команды не найдены. Проверьте файл commands.json",
                                                   max_lines=3,
                                                   text_color="white",
                                                   font=ctk.CTkFont(size=14))
        no_commands_label.pack(padx=12, pady=12)

    commands_count = len(commands_list)
    count_frame = ctk.CTkFrame(commands_content, fg_color="#2b2b2b", height=30)
    count_frame.pack(fill="x", side="bottom", pady=(0, 5))

    count_label = create_multiline_label(count_frame,
                                         f"Всего команд: {commands_count}",
                                         max_lines=2,
                                         text_color="#aaaaaa",
                                         font=ctk.CTkFont(size=12))
    count_label.pack(pady=5)


title_bar = ctk.CTkFrame(root, fg_color=BGColorForFirstButtoms, height=30, corner_radius=0)
title_bar.pack(fill="x", padx=0, pady=0)

equals_label = create_multiline_label(title_bar,
                                      text="=" * 50,
                                      max_lines=1,
                                      text_color="white",
                                      fg_color=BGColorForFirstButtoms,
                                      font=ctk.CTkFont(size=12))
equals_label.pack(side="left", padx=10, fill="x", expand=True)

SettingsBar = ctk.CTkFrame(root,
                           fg_color=BGcolorForSettings,
                           height=40,
                           corner_radius=0)
SettingsBar.pack(fill="x", padx=0, pady=0)

settings_buttons_frame = ctk.CTkFrame(SettingsBar,
                                      fg_color=BGcolorForSettings,
                                      height=40,
                                      corner_radius=0)
settings_buttons_frame.pack(side="right", padx=0)

SetBut = ctk.CTkButton(settings_buttons_frame,
                       text="⚙️ Настройки",
                       command=toggle_settings,
                       fg_color=BGcolorForSettings,
                       hover_color="#444444",
                       text_color="white",
                       height=30,
                       width=125,
                       corner_radius=2)
SetBut.pack(side="right", padx=2)

ComList = ctk.CTkButton(settings_buttons_frame,
                        text="📋 Команды",
                        command=toggle_commands,
                        fg_color=BGcolorForSettings,
                        hover_color="#444444",
                        text_color="white",
                        height=30,
                        width=125,
                        corner_radius=2)
ComList.pack(side="right", padx=0)

Rus = create_multiline_label(SettingsBar,
                             text="Сделано в России",
                             max_lines=1,
                             text_color="white",
                             fg_color=BGcolorForSettings,
                             font=ctk.CTkFont(size=12))
Rus.pack(side="left", padx=10)

content_frame = ctk.CTkFrame(root,
                             fg_color="#783518",
                             corner_radius=0)
content_frame.pack(fill="both", expand=True, padx=0, pady=0)

welcome_label = create_multiline_label(content_frame,
                                       "Добро пожаловать!",
                                       max_lines=2,
                                       text_color="white",
                                       font=ctk.CTkFont(size=16, weight="bold"))
welcome_label.pack(pady=15)

def fade_welcome_message():
    bg_color = (120, 53, 24)

    text_color = (255, 255, 255)

    for step in range(51):
        r = int(text_color[0] + (bg_color[0] - text_color[0]) * step / 50)
        g = int(text_color[1] + (bg_color[1] - text_color[1]) * step / 50)
        b = int(text_color[2] + (bg_color[2] - text_color[2]) * step / 50)

        new_color = f"#{r:02x}{g:02x}{b:02x}"

        welcome_label.configure(text_color=new_color)

        root.update()
        root.after(40)


root.after(10000, fade_welcome_message)

circular_btn = CircularAssistantButton(content_frame, command=on_circular_button_click)
circular_btn.pack(pady=15)

status_label = create_multiline_label(content_frame,
                                      "Статус: Остановлен",
                                      max_lines=2,
                                      text_color="white",
                                      font=ctk.CTkFont(size=14))
status_label.pack(pady=5)

console_frame = ctk.CTkFrame(content_frame, fg_color="#2b2b2b", height=200, corner_radius=0)
console_frame.pack(fill="x", padx=15, pady=15, side="bottom")

console_label = create_multiline_label(console_frame,
                                       "Консоль вывода:",
                                       max_lines=1,
                                       text_color="white",
                                       font=ctk.CTkFont(size=12, weight="bold"))
console_label.pack(anchor="w", padx=10, pady=(5, 0))


console_text = ctk.CTkTextbox(console_frame,
                              fg_color="#1a1a1a",
                              text_color="#00ff00",
                              font=ctk.CTkFont(family="Consolas", size=10),
                              height=150)
console_text.pack(fill="both", expand=True, padx=10, pady=10)
console_text.insert("1.0", "Готов к работе...\n")

enable_text_shortcuts(console_text)

root.bind("<Button-1>", lose_focus_on_background)

create_settings_content()
create_commands_content()

original_stdout = sys.stdout
console_output = ConsoleOutput(console_text, original_stdout, handle_status_change)
sys.stdout = console_output

root.mainloop()

sys.stdout = original_stdout