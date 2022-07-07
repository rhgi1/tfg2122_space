from glob import glob
import math, socket, threading, time, signal, sys, bluetooth, numpy as np, json, sqlite3, bleak, asyncio, struct
from os import system, name
from enum import Enum
from datetime import datetime, timedelta
from bluetooth import *
from Crypto.Cipher import AES

LOCAL_MAC = read_local_bdaddr()[0].lower()
MIBAND4_MAC = "CC:17:D2:EA:51:0B"

class TipoSensor(Enum):
    ESP32 = 1       # Placa de desarrollo ESP32
    LocalBT = 2     # Sensor Bluetooth local

class Sensor:
    def __init__(self, tipo, x, y, z, n, err, rssiD0, conn = None, handler = None, name = None, mac = None, connThread = None):
        self.tipo = tipo
        self.x = x
        self.y = y
        self.z = z
        self.n = n
        self.err = err
        self.rssiD0 = rssiD0
        self.conn = conn
        self.handler = handler
        self.name = name
        self.mac = mac
        self.connThread = connThread

# Variables de configuración
global sensors
sensors = []
global space_size
space_size = []
global steps
steps_registry = [-1, datetime.now()]
global heart_rate_range
heart_rate_range = []
# Sensor(TipoSensor.ESP32,   x=400, y=290, z=80,  conn=None, name="Zeus_0002", mac="84:cc:a8:58:fb:86"),
# Sensor(TipoSensor.ESP32,   x=400, y=290, z=80,  conn=None, name="Zeus_0003", mac="7c:9e:bd:f9:c7:02") ]


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
    print("## M A I N ##")
    print("#############\n")

def sigint_handler(signal, frame):
    global file
    global client
    
    print('')
    for sensor in sensors:
        if sensor.connThread is not None and sensor.connThread.is_alive() is True:
            print("Killing thread from sensor " + sensor.name)
            sensor.connThread.join()
            
    file.close()

    if 'client' in globals() and client is not None:
        client.disconnect()

    sys.exit(0)

# Carga la configuración del mapa y de los sensores
def loadConfig(path):
    global sensors
    global space_size
    global heart_rate_range

    f = open(path, 'r')
    data = json.load(f)

    # Carga la config de los sensores
    for s in data['sensors']:
        tipo = TipoSensor.LocalBT if s['tipo'] == "LocalBT" else TipoSensor.ESP32
        sensors.append(Sensor(tipo, x=s['x'], y=s['y'], z=s['z'], n=s['n'], err=s['err'], rssiD0=s['rssi_D0'], name=s['name'], mac=s['mac']))

    # Tamaño del espacio
    space_size = [data['space_size'][0], data['space_size'][1]]
    # Rangos del ritmo cardíaco
    heart_rate_range = [data['heart_rate_range'][0], data['heart_rate_range'][1]]


# Solicita del sensor el RSSI de la pulsera
def getRSSIFromSensor(sensor, mac):
    if sensor.conn is not None:
        try:
            if sensor.tipo is TipoSensor.ESP32:
                sensor.conn.send(bytearray(b'0508\x00')) # request = [Clave REQ: 4 bytes]
                response = sensor.conn.recv(8) # response = [Handler: 4 bytes | RSSI: 4 bytes]
                
                # Comprobamos si el paquete es para nosotros comparando el handler
                if len(response) == 8 and sensor.handler == int.from_bytes(response[0:4], "little", signed=False):
                    return int.from_bytes(response[4:8], "little", signed=True)

            elif sensor.tipo is TipoSensor.LocalBT:
                sensor.conn.send(mac.encode('utf-8'))
                return int(sensor.conn.recv(4))

        except (ValueError, AttributeError, BrokenPipeError, bluetooth.btcommon.BluetoothError) as exception:
            sensor.conn = None
    
    else:
        return None

# Estima la posición de la pulsera a partir de las distancias de los sensores
# Formato distances => [x, y, error, distancia]
def getPositionFromDistances(distances):
    if (len(distances[0]) != 4):
        return [-1, -1]

    points = []
    for i in range(space_size[0]//10):
        for j in range(space_size[1]//10):
            points.append([i*10, j*10])

    for distance in distances:
        r_min = distance[3] - distance[2]
        r_max = distance[3] + distance[2]

        for point in list(points):
            dist = abs(math.dist([distance[0], distance[1]], [point[0], point[1]]))
            if dist < r_min or dist > r_max:
                points.remove(point)

    if len(points) == 0:
        return ['-1', '-1']

    min_x = min(points, key=lambda x:x[0])[0]
    max_x = max(points, key=lambda x:x[0])[0]
    min_y = min(points, key=lambda x:x[1])[1]
    max_y = max(points, key=lambda x:x[1])[1]

    return [(max_x - min_x)/2, (max_y - min_y)/2]

# Calcula la distancia desde el sensor hasta la pulsera basada en el RSSI
def getDistanceFromSensor(sensor, rssi):
    distance = np.power(10, (sensor.rssiD0 - rssi) / (10 * sensor.n)) * 100
    return distance

# Suscribe la dirección MAC de la pulsera para ser escuchada
def subscribeDevice(sensor, mac):
    request = bytearray(b'')
    for byte in mac.split(':'):
        request.append(int(byte, 16))

    try:
        sensor.conn.send(request)   # request = [MAC Pulsera: 6 bytes]
        while True:
            response = sensor.conn.recv(10) # response = [MAC Raspberry: 6 bytes | Handler: 4 bytes]
            if response[0:6].hex(":") == LOCAL_MAC:
                sensor.handler = int.from_bytes(response[6:10], "little", signed=False)
                break

    except (ValueError, ConnectionRefusedError, bluetooth.btcommon.BluetoothError) as ex:
        sensor.conn = None
        sensor.handler = None

# Establece una conexión con el sensor
def connectToSensor(sensor):
    print(f'Connecting to sensor {sensor.mac} ...')
    try:
        # Tipo 1: ESP32
        if sensor.tipo is TipoSensor.ESP32:
            client = bluetooth.BluetoothSocket(bluetooth.RFCOMM)

            client.connect((sensor.mac, 1))
            sensor.conn = client

        # Tipo 2: Bluetooth local
        elif sensor.tipo is TipoSensor.LocalBT:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            client.connect((socket.gethostbyname(socket.gethostname()), 2000))
            sensor.conn = client

        print(sensor.name, 'has been connected.')
    except (ValueError, ConnectionRefusedError, bluetooth.btcommon.BluetoothError) as ex:
        if type(ex) is ConnectionRefusedError or type(ex) is bluetooth.btcommon.BluetoothError:
            print(ex)
            print(sensor.name, 'is not available.')

        sensor.conn = None

    # Si hemos conseguido establecer la conexión, suscribimos la pulsera
    # if sensor.conn is not None:
    if sensor.tipo is TipoSensor.ESP32 and sensor.conn is not None:
        subscribeDevice(sensor, MIBAND4_MAC)

def getCurrentBand():
    f = open('band.json', 'r')
    data = json.load(f)
    f.close()
    return data['mac'], data['extra1']

async def main():
    if len(sys.argv) > 1:
        execName = str(sys.argv[1])
    else:
        execName = ""

    global file
    global client
    global band_auth
    global band_mac
    global sensorData
    sensorData = []
    global heartData
    heartData = []

    showBanner()

    loadConfig('config.json')

    # La primera conexión será de forma secuencial para evitar errores
    for sensor in sensors:
        connectToSensor(sensor)

    # file = open(datetime.now().strftime("%d-%m-%Y.log"), "a")
    # file.write("# Nueva ejecución a las " + datetime.now().strftime("%H:%M:%S -> ") + execName + '\n')
    # file.write("------------------------------\n")
    
    # Controla salida con Ctrl + C
    signal.signal(signal.SIGINT, sigint_handler)

    # El tiempo cada minuto 
    current_time = time.time()

    # Estado actual de la pulsera (dentro/fuera)
    band_localized = "in"

    # Mediciones fallidas
    sensor_failed = 0
    # Mediciones acertadas
    sensor_ok = 0

    while True:
        band_mac, band_auth = getCurrentBand()
        
        #################################################
        # BLOQUE 1: CONEXIÓN CON LOS SENSORES BLUETOOTH #
        #################################################
        if (time.time() - current_time < 60):
            file = open(datetime.now().strftime("%d-%m-%Y.log"), "a")
            
            # Se reconectará a los sensores si estuviesen desconectados
            for sensor in sensors:
                if sensor.conn is None and (sensor.connThread is None or sensor.connThread.is_alive() is False):
                    sensor.connThread = threading.Thread(target=connectToSensor, args=(sensor, ))
                    sensor.connThread.start()
            
            distances = []
            for sensor in sensors:
                rssi = getRSSIFromSensor(sensor, MIBAND4_MAC)

                # Si no la ha encontrado ...
                if rssi is None:
                    sensor_ok = 0
                    sensor_failed += 1
                    if band_localized == "in" and sensor_failed >= 5:
                        band_localized = "out"
                        sensor_ok = 0
                        saveEvent("Salida", 1)
                else:
                    sensor_failed = 0
                    sensor_ok += 1
                    if band_localized == "out" and sensor_ok >= 5:
                        band_localized = "in"
                        sensor_failed = 0
                        saveEvent("Entrada", 1)

                    distance = getDistanceFromSensor(sensor, rssi)
                    distances.append([sensor.x, sensor.y, sensor.err, distance])
            
            position = getPositionFromDistances(distances)
            
            db_connection = sqlite3.connect('file:db/space.db?mode=ro', uri=True)
            space_db = db_connection.cursor()
            space_db.execute(f'SELECT x, y FROM locations WHERE mac_address = \'{band_mac}\' ORDER BY date DESC LIMIT 1')
            rows = space_db.fetchone()
            db_connection.close()
            
            # Solo guardamos la posición SI:
            # O no tenemos registros previos
            # O si la nueva posición es distinta de -1, -1
            # O si la nueva posición es -1, -1 y la última no lo es
            if (rows is None or (position[0] != -1 and position[1] != -1) or ((position[0] == -1 and position[1] == -1) and (rows[0] != '-1' and rows[1] != '-1'))):
                db_connection = sqlite3.connect(r"db/space.db")
                space_db = db_connection.cursor()
                space_db.execute("INSERT INTO locations VALUES ('" + band_mac + "', '" + datetime.today().strftime('%Y-%m-%d %H:%M:%S') + "', " + str(position[0]) + ", " + str(position[1]) + ")")
                db_connection.commit()
                db_connection.close()
            
                file.write(datetime.now().strftime("%H:%M:%S") + ' - ' + str(position) + '\n')
                print(position)
            
            file.close()

            await asyncio.sleep(1)

        
        #################################################
        #   BLOQUE 2: CONEXIÓN DIRECTA CON LA PULSERA   #
        #   CADA 60 SEGUNDOS (1 MINUTO)                 #
        #################################################
        else:
            try:
                async with bleak.BleakClient(band_mac) as client:
                    global btSignal
                    btSignal = False
                    global counter
                    counter = 10

                    # AUTENTICACIÓN
                    # Activa las notificaciones ...
                    await client.start_notify('00000009-0000-3512-2118-0009af100700', auth_handler)
                    # y solicita el número aleatorio
                    await client.write_gatt_char('00000009-0000-3512-2118-0009af100700', b'\x02\x00')
                    
                    while(btSignal is False):
                        await asyncio.sleep(1)
                    btSignal = False

                    # Recibido el número aleatorio, solicitamos toda la info

                    # Activamos las notificaciones ...
                    await client.start_notify('00000005-0000-3512-2118-0009af100700', activity_handler)

                    while(btSignal is False):
                        await asyncio.sleep(1)
                    btSignal = False

                    await client.disconnect()

                    current_time = time.time()
            except Exception as ex:
                print(ex)
        
async def auth_handler(sender, data):
    global client
    global band_auth
    global btSignal

    # Número aleatorio recibido
    if data[:3] == b'\x10\x02\x01':
        # Número aleatorio que tenemos que encriptar y devolver
        random_nb = data[3:]
        # El algoritmo AES encriptará este número con nuestra clave de autenticación
        aes = AES.new(bytearray.fromhex(band_auth), AES.MODE_ECB)
        # Enviaremos \x03\x00 + el número encriptado
        send_data = bytearray(b'\x03\x00') + aes.encrypt(random_nb)
        await client.write_gatt_char('00000009-0000-3512-2118-0009af100700', send_data)

    # Autenticación realizada con éxito
    elif data[:3] == b'\x10\x03\x01':
        btSignal = True
        await client.stop_notify('00000009-0000-3512-2118-0009af100700')
        

async def activity_handler(sender, data):
    global client
    global btSignal
    global steps
    global counter

    if len(data) % 4 == 1:
        i = 1
        while i < len(data):
            steps = struct.unpack("B", data[i + 2:i + 3])[0]
            heart_rate = struct.unpack("B", data[i + 3:i + 4])[0]

            # Evento: ritmo cardíaco inusual
            if (heart_rate < heart_rate_range[0] and heart_rate > heart_rate_range[1]):
                saveEvent("BPM inusual (" + heart_rate + ")", 2)

            # Evento: inactividad
            steps_now_date = datetime.now()
            for registry in steps_registry:
                if registry[1] < steps_now_date - datetime.timedelta(hours=1):
                    # Si se han registrado menos de 100 pasos en una hora, evento
                    if steps - registry[0] < 100:
                        saveEvent("Inactividad", 0)
                        
    await client.write_gatt_char('00002a39-0000-1000-8000-00805f9b34fb', b'\x03')
    await client.stop_notify('00002a39-0000-1000-8000-00805f9b34fb')
    btSignal = True

# Guarda en la base de datos el evento registrado
def saveEvent(message, priority):
    # Creamos la conexion con la BD
    db_connection = sqlite3.connect(r"db/space.db")
    space_db = db_connection.cursor()
    space_db.execute("INSERT INTO events VALUES ('" + band_mac + "', '" + datetime.today().strftime('%Y-%m-%d %H:%M:%S') + "', " + message + ", " + str(priority) + ")")
    db_connection.commit()
    db_connection.close()

if __name__ == '__main__':
    asyncio.run(main())
    