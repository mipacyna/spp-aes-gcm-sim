import socket
import packet
import config


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((config.HOST, config.SAT_PORT))
    print("satellite is listening on port "+str(config.SAT_PORT))
    ether = (config.HOST, config.ETHER_PORT)
    while True:
        try:
            raw, addr = sock.recvfrom(65535) # odbior pakietu (zawsze z eteru)
        except ConnectionResetError:
            continue # Windows: ICMP port unreachable po poprzedniej wysylce
        p,data,sec_h=packet.unpack(raw)  # odpakowanie
        SpacePacket = packet.SpacePacket(0,config.APID_TM,0b11,p.seq_number) # pakowanie odpowiedzi
        sock.sendto((packet.pack(SpacePacket,b"received")), ether) # potwierdzenie przez eter
        print(raw.hex(" "))
        print(data)
if __name__ == "__main__":
    main()