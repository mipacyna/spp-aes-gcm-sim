import packet,config,socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.sendto(packet.pack(packet.SpacePacket(1, 0x10, 0b11, 0), b"PING"), ("127.0.0.1", 5002))
raw,addr=s.recvfrom(4096)
print(raw.hex(" "))
