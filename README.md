# spp-aes-gcm-sim
Ground–satellite link simulator: CCSDS Space Packet Protocol secured with AES-256-GCM, tested over a noisy channel with attacks.

## Modules

All nodes communicate over UDP only through the ether (`eter.py`), which routes each frame by the packet type bit in its header: TC → satellite, TM → ground station.

### `packet.py` — CCSDS Space Packet frame
Builds and parses SPP packets (CCSDS 133.0-B-2): a 6-byte primary header (big-endian) followed by the data field.
- `SpacePacket(packet_type, apid, seq_flag, seq_number)` — header fields: type (0 = TM, 1 = TC), APID (11 bits), sequence flags (2 bits, `0b11` = unsegmented), sequence count (14 bits).
- `pack(p, data, sec_header=b"")` → `bytes` — prepends the secondary header to the data and sets its flag and the length field (`len(payload) - 1`) automatically.
- `unpack(raw, sec_header_len=0)` → `(SpacePacket, data, sec_header)` — parses the header and extracts the data. The secondary header length is not transmitted in the frame, so it has to be passed in (it is fixed per APID).
- `pack_header()`, `pack_payload()` — helpers used by `pack()`.

### `earth.py` — ground station
Sends a telecommand (TC, APID `0x10`, data `PING`) through the ether and waits up to 3 s for telemetry on `EARTH_PORT`. Prints the received frame in hex, or a message if no reply arrived.

### `satellite.py` — satellite
Listens in a loop on `SAT_PORT`. Unpacks every received frame and sends an acknowledgement back through the ether (TM, APID `0x11`, same sequence count, data `received`).
### Running
Start each module in a separate terminal, in this order:

1. Ether:
   ```bash
   python eter.py
   ```
2. Satellite:
   ```bash
   python satellite.py
   ```
3. Sniffer (attacker):
   ```bash
   python atak.py sniff
   ```
4. Ground station:
   ```bash
   python earth.py
   ```
Noisy channel example (restart only the ether):
```bash
python eter.py --ber 0.01 --loss 0.2 --delay 100
```
Address and ports are set in `config.py` (default `127.0.0.1`: ether 5000, ground station 5001, satellite 5002, attacker 5003).
