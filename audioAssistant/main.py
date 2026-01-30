import vosk
import pyaudio
import json
import time

from torch.utils.hipify.hipify_python import value

from FuncLib import (
    open_browser_and_search, remove_keywords, close_tab, new_tab,
    go_to_tab, scroll_up, scroll_down, volume_down, volume_up, mute,
    open_browser, close_browser, open_dota, close_dota, for_close,
    right, left, down, up, left_click, double_click, right_click,
    extract_number_from_text, word_to_number,
    BROWSER_PATH, DOTA_PATH,
)


def AbsolutStarter123(file_path: str = ""):
    import os
    if not file_path:
        print("ОШИБКА: Не указан путь к файлу")
        return

    try:
        file_path = file_path.strip()
        if file_path.startswith('"') and file_path.endswith('"'):
            file_path = file_path[1:-1]
        elif file_path.startswith("'") and file_path.endswith("'"):
            file_path = file_path[1:-1]

        print(f"Открываю файл: {file_path}")

        if not os.path.exists(file_path):
            print(f"Файл не найден: {file_path}")
            return

        os.startfile(file_path)
        print("Файл успешно открыт")

    except Exception as error:
        print(f"Ошибка при открытии файла: {error}")


def AbsolutCloser123(file_path: str = ""):
    import os
    import subprocess

    if not file_path:
        print("ОШИБКА: Не указан путь к файлу")
        return

    try:
        file_path = file_path.strip()
        if file_path.startswith('"') and file_path.endswith('"'):
            file_path = file_path[1:-1]
        elif file_path.startswith("'") and file_path.endswith("'"):
            file_path = file_path[1:-1]

        process_name = os.path.basename(file_path)

        if not process_name.lower().endswith('.exe'):
            process_name += '.exe'

        print(f"Закрываю процесс: {process_name}")

        try:
            subprocess.run(['taskkill', '/f', '/im', process_name],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL,
                           creationflags=subprocess.CREATE_NO_WINDOW)
            print("Процесс завершен")
        except Exception as error:
            print(f"Не удалось завершить процесс: {error}")

    except Exception as error:
        print(f"Ошибка при закрытии приложения: {error}")

def Sorter(text: str):
    sorted_text = text.split(" ")
    return sorted_text


def Starter(text: list):
    text_str = " ".join(text).lower()

    with open('commands.json', 'r', encoding='utf-8') as f:
        commands_config = json.load(f)

    for command in commands_config['commands']:
        if all(keyword in text_str for keyword in command['keywords']):
            print(f"Выполняю: {command['name']}")
            execute_command(command, text)
            return

    print("Команда не распознана")





def execute_command(command, text_list):
    text_str = " ".join(text_list).lower()

    functions = {
        'openBrowser': open_browser,
        'closeBrowser': close_browser,
        'openDota': open_dota,
        'closeDota': close_dota,
        'open_browser_and_search': open_browser_and_search,
        'close_tab': close_tab,
        'new_tab': new_tab,
        'go_to_tab': go_to_tab,
        'scroll_down': scroll_down,
        'scroll_up': scroll_up,
        'mute': mute,
        'volume_down': volume_down,
        'volume_up': volume_up,
        'right': right,
        'left': left,
        'down': down,
        'up': up,
        'left_click': left_click,
        'double_click': double_click,
        'right_click': right_click,
        'AbsolutStarter': AbsolutStarter123,
        'AbsolutCloser': AbsolutCloser123,
    }

    args = []
    for arg in command['args']:
        if arg == 'remove_keywords(text_str)':
            args.append(remove_keywords(text_str))
        elif arg == 'text_str':
            args.append(text_str)
        elif arg == 'extract_number(text_list)':
            pixels = extract_number_from_text(text_list)
            args.append(pixels)
        elif arg == 'browserUrl':
            args.append(BROWSER_PATH)
        else:
            if 'cfg_vars' in arg:
                import re
                match = re.search(r"cfg_vars\['([^']+)'\]", arg)
                if match:
                    var_name = match.group(1)
                    try:
                        with open('cfg.json', 'r', encoding='utf-8') as f:
                            cfg_vars = json.load(f)
                            if var_name in cfg_vars:
                                args.append(cfg_vars[var_name].get('value', ''))
                            else:
                                args.append(arg)
                    except:
                        args.append(arg)
                else:
                    args.append(arg)
            else:
                args.append(arg)

    try:
        func = functions[command['function']]
        func(*args)
    except KeyError:
        print(f"Функция {command['function']} не найдена")
        try:
            from FuncLib import AbsolutStarter, AbsolutCloser
            if command['function'] == 'AbsolutStarter':
                AbsolutStarter(*args)
            elif command['function'] == 'AbsolutCloser':
                AbsolutCloser(*args)
            else:
                print(f"Неизвестная функция: {command['function']}")
        except ImportError:
            print(f"Не удалось импортировать функцию из FuncLib")
    except Exception as error:
        print(f"Ошибка выполнения: {error}")


def VoiceActive(activation_word="один"):

    with open('config.json', 'r', encoding='utf-8') as f:
        MODEL_PATH = json.load(f).get("selected_lib", {})

    # MODEL_PATH = r"models/vosk-model-small-ru-0.22"

    print("Загружаем модель...")
    model = vosk.Model(MODEL_PATH)

    mic = pyaudio.PyAudio()
    stream = mic.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=1024
    )

    activation_recognizer = vosk.KaldiRecognizer(model, 16000)
    main_recognizer = vosk.KaldiRecognizer(model, 16000)

    print(f"Ожидание ключевого слова: '{activation_word}'")

    try:
        while True:
            activation_detected = False

            while not activation_detected:
                data = stream.read(512, exception_on_overflow=False)

                if activation_recognizer.AcceptWaveform(data):
                    result = json.loads(activation_recognizer.Result())
                    text = result.get('text', '').lower()

                    if activation_word in text:
                        activation_detected = True
                        break

            print("Слушаю")

            main_recognizer = vosk.KaldiRecognizer(model, 16000)
            silence_timeout = 0

            try:
                with open('cfg.json', 'r', encoding='utf-8') as f:
                    cfg_data = json.load(f)
                    silence_var = cfg_data.get("Время для перехода в режим ожидания(в секундах)", {})
                    max_silence_str = silence_var.get("value", "")

                    try:
                        max_silence = int(max_silence_str)
                    except (ValueError, TypeError):
                        max_silence = 10
                        print(
                            f"Время для перехода в режим ожидания должно быть числом. Использую {max_silence} секунд")
            except Exception as error:
                print(f"Ошибка загрузки cfg.json: {error}")
                max_silence = 10


            while silence_timeout < max_silence:
                data = stream.read(2048, exception_on_overflow=False)

                if main_recognizer.AcceptWaveform(data):
                    result = json.loads(main_recognizer.Result())
                    text = result.get('text', '')

                    if text:
                        print(f"Распознано: {text}")
                        processed_text = Sorter(text)
                        print(processed_text)
                        Starter(processed_text)
                        silence_timeout = 0
                    else:
                        silence_timeout += 0.5
                else:
                    partial = json.loads(main_recognizer.PartialResult())
                    partial_text = partial.get('partial', '')
                    if partial_text:
                        print(f"Говорите...: {partial_text}")
                        silence_timeout = 0
                    else:
                        silence_timeout += 0.2

                time.sleep(0.1)

            print("Возврат к ожиданию ключевого слова...")
            activation_recognizer = vosk.KaldiRecognizer(model, 16000)

    except KeyboardInterrupt:
        print("\nДо свидания!")
    finally:
        stream.stop_stream()
        stream.close()
        mic.terminate()


class EnhancedVoiceRecognizer:
    def __init__(self, model_path):
        self.model = vosk.Model(model_path)
        self.recognizer = vosk.KaldiRecognizer(self.model, 16000)
        self.enhancement_dict = {
            "вкладку": ["вклад куб"],
        }


if __name__ == "__main__":
    try:
        with open('cfg.json', 'r', encoding='utf-8') as f:
            name = json.load(f).get("Имя голосового помощника", {}).get("value", "").strip().lower()

    except:
        name = "один"

    VoiceActive(name)