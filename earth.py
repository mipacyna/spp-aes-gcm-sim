import packet,config,socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind((config.HOST, config.EARTH_PORT))  # eter dostarcza telemetrie na ten port
s.settimeout(3)
s.sendto(packet.pack(packet.SpacePacket(1, 0x10, 0b11, 0), b"PING"), (config.HOST, config.ETHER_PORT))
try:
    raw,addr=s.recvfrom(4096)
    print(raw.hex(" "))
except socket.timeout:
    print("brak odpowiedzi (ramka zgubiona w eterze?)")
