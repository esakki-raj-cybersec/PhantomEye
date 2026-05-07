from server import *
import sys

if __name__ == "__main__":

    if len(sys.argv) < 3:
        print("\n[!] Arguments Not Found! \nGive LHOST and LPORT as argument")
        print(f"\nUsage: python main.py 192.168.31.1 4444")
        sys.exit(1)

    host = sys.argv[1]
    port = sys.argv[2]
    
    try:
        listener = Listener(host,int(port))
        listener.main()

    except Exception as e:
        print(f"\nERROR: {e}")

    except KeyboardInterrupt:
        print("\n[*] Quiting forcefully....")
        listener.socket.close()

