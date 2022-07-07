import socket, threading, signal, sys
from os import system, name
from bluepy.btle import Scanner, DefaultDelegate

listening = False
devices = {}

def clear():
    if name == 'nt':  # Windows
        system('cls')
  
    else:   # Mac y Linux
        system('clear')

def showBanner():
    clear()
    print("       __")
    print("  (___()'`;")
    print("  /,    /`")
    print("  \\\\\"--\\\\")
    print("#############")
    print("## Z E U S ##")
    print("#############")
    print("## SENSOR  ##")
    print("#############\n")

def sigint_handler(signal, frame):
    global server
    global scanThread
    server.close()
    scanThread.join()
    
    print('')
    sys.exit(0)

def btScanner():
    scanner = Scanner()
    global devices

    while True:
        devices = scanner.scan(5)

def startServer():
    global server
    server.listen()

    showBanner()
    print(f"Listening on {socket.gethostbyname(socket.gethostname())}")

    while True:
        conn, addr = server.accept()
        print(f"New connection: {addr[0]}:{addr[1]}")

        while True:
            inRange = False
            macAddress = conn.recv(17).decode('utf-8').lower()   # Recibimos la dirección MAC

            try:
                for device in devices:
                    if device.addr == macAddress:
                        conn.send(str(device.rssi).encode('utf-8'))
                        inRange = True
                        break
                
                if inRange is False:
                    conn.send('0'.encode('utf-8'))

            except BrokenPipeError:
                break
        
if __name__ == '__main__':
    global scanThread
    global server

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Previene los sockets abiertos al colapsar la conexión
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((socket.gethostbyname(socket.gethostname()), 2000))
    
    scanThread = threading.Thread(target=btScanner)
    scanThread.start()

    # Controla el Ctrl + C
    signal.signal(signal.SIGINT, sigint_handler)

    startServer()