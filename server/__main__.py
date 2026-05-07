from server.listener import Listener
import sys

if __name__ == "__main__":
    
    if len(sys.argv) < 3:
        print("\n[!] Arguments Not Found! \nGive LHOST and LPORT as argument")
        print(f"\n Usage: python -m server 192.168.31.1 4444")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])

    try:
        listener = Listener(host,port)
        listener.main()
        
    except Exception as e:
        print(f"\nERROR: {e}")

    except KeyboardInterrupt:
        print("\n[*] Quiting forcefully....\n")
        listener.socket.close()