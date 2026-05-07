import json
import os
import base64

class DataProcessor:
    """This module Send and receive the data via socket using json and process different type of data.

    ## Usage:

        send() --> send data with json format
        receive() --> receive the data with header and jsondata
        shareing_data() --> if you want send and receive data instant and simultaneously
        write_file() --> writting the received raw byte as file
        read_file() --> Read the bytes of the file 

    """
    def __init__(self,conn):
        self.conn = conn

    def send(self,data):

        self.conn.send(json.dumps(data).encode("utf-8"))
    
    def receive(self):

        header = int.from_bytes(self.conn.recv(4), byteorder='big')
        
        if header == 0:
            return None
        
        if not header:
            return None
        
        json_data = ""
        while len(json_data) < header:
            data = self.conn.recv(header-len(json_data)).decode('utf-8')
            if not data:
                break
            json_data += data

        return json.loads(json_data)
    
    def sharing_data(self,data):

        self.send(data)
        return self.receive()
    
    def write_file(self,filename,content):

        with open(filename,"wb") as file:
            file.write(base64.b64decode(content))
            return "[+] Successfully download "

    def read_file(self,path):

        with open(path,"rb") as file:
            return base64.b64encode(file.read())
        
    def upload_file(self,path):
        """Read the given file or folder and return the content of the file or folder as dictionary format.
        
        return like this {filename:filedata}  
        """

        folder_content = {}
        if os.path.isfile(path):
            folder_content[os.path.basename(path)] = self.read_file(path).decode()

        for root, dirs, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root,file).replace("\\","/")
                folder_content[file_path] = self.read_file(file_path).decode()

        return folder_content

    def download(self,data):
        "write the given data as file or folder "

        num = 0

        if not data:
            return "[-] No file or directory found"
        
        for file_path,content in data.items():
            folder = file_path.removesuffix(os.path.basename(file_path))
        
            if not os.path.exists(folder) and folder != "":
                os.makedirs(folder)
            result = self.write_file(file_path,content.encode())
            num += 1

        return f"{result} {num} files"