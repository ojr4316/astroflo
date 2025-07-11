import socket
import struct
import time
import threading

HOST = '0.0.0.0'
PORT = 10001

class StellariumConnection:
    def __init__(self, host: str = HOST, port: int = PORT):
        self.host = host
        self.port = port
        self.server_thread = None
        self.has_update = False
        self.ra = 0.0
        self.dec = 0.0

    def encode_position(self, ra_hours: float, dec_deg: float) -> bytes:
        ra_int = int(ra_hours * (2**32 / 24.0))                # RA: 0-24h → uint32
        dec_int = int(dec_deg * (0x40000000 / 90.0))           # Dec: -90° to +90° → int32
        timestamp = int(time.time() * 1e6)                     # Current time in microseconds
        return struct.pack('<hhqIii', 24, 0, timestamp, ra_int, dec_int, 0)

    def send_position(self, conn, ra_deg: float, dec_deg: float):
        ra_hours = ra_deg / 15.0 
        packet = self.encode_position(ra_hours, dec_deg)
        conn.sendall(packet)

    def update_position(self, ra: float, dec: float):
        self.ra = ra
        self.dec = dec
        self.has_update = True

    def server(self):
        print("Starting Stellarium server...")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((HOST, PORT))
                s.listen(1)
                print(f"Waiting for Stellarium to connect on port {PORT}...")
                
                conn, addr = s.accept()
                with conn:
                    print(f"Stellarium connected from {addr}")
                    while True:
                        if self.has_update:
                            self.has_update = False
                            self.send_position(conn, self.ra, self.dec)
                        time.sleep(0.5)
        except OSError as e:
            print(f"Error starting Stellarium server: {e}")
            time.sleep(10)
            self.server()

    def run_server(self):
        self.server_thread = threading.Thread(target=self.server, daemon=True)
        self.server_thread.start()
    
    def stop_server(self):
        self.server_thread.stop()
                    
