class SpacePacket:

  def __init__(self, packet_type:int,apid:int,seq_flag:int,seq_number:int):
    self.pvn = 0
    self.packet_type = packet_type # 1b  0 - telemetric 1 - telecommand
    self.sec_flag = 0 # 1b 0 - data doesnt contains secondary header 1 - it does
    self.apid = apid # 11b application id, used for identification
    self.seq_flag = seq_flag # 2b 00 - continuation, 01 - first, 10 - last, 11 - unsegmented data
    self.seq_number = seq_number # 14b / or packet name
    self.data = "" 
    self.data_size = ""

p0 = SpacePacket(1,11,1,1)
def pack_payload(data:bytes,sec_header:bytes = b"")->bytes:
  packet_data = (data)
  packet_sec_header = (sec_header)
  return packet_sec_header + packet_data


def pack_header(packet_type:int,sec_flag:int,apid:int,seq_flag:int,seq_number:int,data_size:int)->bytes:
    packet_identificators = (packet_type<<12) | (sec_flag<<11) | (apid<<0) # first 2 octets
    packet_sequence_control = (seq_flag<<14) | (seq_number<<0) # second 2 octets
    packet_data_length = (data_size-1<<0)

    return packet_identificators.to_bytes(2,"big") + packet_sequence_control.to_bytes(2,"big")+packet_data_length.to_bytes(2,"big");


def pack(p: SpacePacket, data: bytes, sec_header: bytes = b"") -> bytes:
    payload = pack_payload(data, sec_header)
    sec_flag = 1 if sec_header else 0       
    header = pack_header(p.packet_type, sec_flag, p.apid, p.seq_flag, p.seq_number, len(payload))
    return header + payload


def unpack(raw: bytes, sec_header_len: int = 0) -> tuple[SpacePacket, bytes, bytes]:
    packet_identificators = int.from_bytes(raw[0:2], "big")
    packet_sequence_control = int.from_bytes(raw[2:4], "big")
    packet_data_length = int.from_bytes(raw[4:6], "big")

    pvn = packet_identificators >> 13
    packet_type = (packet_identificators >> 12) & 0b1
    sec_flag = (packet_identificators >> 11) & 0b1
    apid = packet_identificators & 0x7FF

    seq_flag = packet_sequence_control >> 14
    seq_number = packet_sequence_control & 0x3FFF

    payload = raw[6:6 + packet_data_length + 1]

    if sec_flag:
        sec_header = payload[:sec_header_len]
        data = payload[sec_header_len:]
    else:
        sec_header = b""
        data = payload

    p = SpacePacket(packet_type, apid, seq_flag, seq_number)
    p.pvn = pvn
    p.sec_flag = sec_flag
    p.data = data
    return p, data, sec_header





