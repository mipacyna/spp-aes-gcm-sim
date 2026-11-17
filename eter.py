"""
eter.py - symulator kanalu radiowego.

Wszystkie wezly (ziemia, satelita, atakujacy) wysylaja ramki na ETHER_PORT.
Eter:
  * kieruje ramke do adresata na podstawie bitu "typ pakietu" w naglowku CCSDS
    (1 = telekomenda -> satelita, 0 = telemetria -> ziemia),
  * dokłada efekty kanalu: utrate ramki (LOSS), przeklamania bitow (BER),
    opoznienie (DELAY_MS +/- JITTER_MS),
  * rozsyla kopie kazdej ramki do nasluchujacych (SNIFFER_PORTS) - kanal
    radiowy jest jawny, wiec kazdy w zasiegu "slyszy" transmisje.

Uzycie:
    python eter.py                       # parametry z config.py
    python eter.py --ber 1e-4 --loss 0.05 --delay 50 --jitter 10
    python eter.py --log eter_log.csv    # zapis kazdej ramki do CSV (do wykresow)
"""
import argparse
import csv
import heapq
import random
import socket
import threading
import time

import config

HEADER_LEN = 6


# ---------------------------------------------------------------- kanal ----

def flip_bits(frame: bytes, ber: float, rng: random.Random) -> tuple[bytes, int]:
    """Przeklamuje kazdy bit niezaleznie z prawdopodobienstwem ber.
    Zwraca (nowa_ramka, liczba_przeklamanych_bitow)."""
    if ber <= 0 or not frame:
        return frame, 0
    n_bits = len(frame) * 8
    # liczba bledow ~ Binomial(n_bits, ber); potem losujemy ich pozycje bez powtorzen
    n_err = sum(1 for _ in range(n_bits) if rng.random() < ber)
    if n_err == 0:
        return frame, 0
    buf = bytearray(frame)
    for pos in rng.sample(range(n_bits), n_err):
        buf[pos // 8] ^= 0x80 >> (pos % 8)
    return bytes(buf), n_err


def peek_header(frame: bytes) -> dict | None:
    """Odczytuje jawny naglowek CCSDS (bez walidacji reszty ramki)."""
    if len(frame) < HEADER_LEN:
        return None
    ident = int.from_bytes(frame[0:2], "big")
    seq = int.from_bytes(frame[2:4], "big")
    return {
        "type": (ident >> 12) & 1,
        "apid": ident & 0x7FF,
        "seq": seq & 0x3FFF,
    }


# ---------------------------------------------------------------- eter -----

class Ether:
    def __init__(self, ber, loss, delay_ms, jitter_ms, seed=None, log_path=None, verbose=True):
        self.ber = ber
        self.loss = loss
        self.delay = delay_ms / 1000.0
        self.jitter = jitter_ms / 1000.0
        self.rng = random.Random(seed)
        self.verbose = verbose

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((config.HOST, config.ETHER_PORT))

        self.earth = (config.HOST, config.EARTH_PORT)
        self.sat = (config.HOST, config.SAT_PORT)
        self.sniffers = [(config.HOST, p) for p in config.SNIFFER_PORTS]

        # kolejka (czas_dostarczenia, nr, ramka, adres) obslugiwana przez osobny watek
        self._queue: list = []
        self._cv = threading.Condition()
        self._counter = 0

        self.stats = {"rx": 0, "forwarded": 0, "lost": 0, "corrupted": 0,
                      "bits_flipped": 0, "malformed": 0}

        self._log_file = None
        self._log = None
        if log_path:
            self._log_file = open(log_path, "w", newline="")
            self._log = csv.writer(self._log_file)
            self._log.writerow(["time", "src_port", "dst_port", "len", "type", "apid",
                                "seq", "lost", "bits_flipped", "ber", "loss"])

    # -- planowanie wysylki z opoznieniem --
    def _schedule(self, frame: bytes, addr):
        d = self.delay + (self.rng.uniform(-self.jitter, self.jitter) if self.jitter else 0.0)
        t = time.monotonic() + max(0.0, d)
        with self._cv:
            self._counter += 1
            heapq.heappush(self._queue, (t, self._counter, frame, addr))
            self._cv.notify()

    def _sender_loop(self):
        while True:
            with self._cv:
                while not self._queue:
                    self._cv.wait()
                t, _, frame, addr = self._queue[0]
                now = time.monotonic()
                if t > now:
                    self._cv.wait(t - now)
                    continue
                heapq.heappop(self._queue)
            try:
                self.sock.sendto(frame, addr)
            except OSError:
                pass  # np. adresat nie slucha (Windows: WSAECONNRESET)

    # -- obsluga jednej ramki --
    def route(self, hdr: dict):
        return self.sat if hdr["type"] == config.TC else self.earth

    def handle(self, frame: bytes, src):
        self.stats["rx"] += 1
        hdr = peek_header(frame)
        if hdr is None:
            self.stats["malformed"] += 1
            self._print(f"[eter] odrzucono zbyt krotka ramke ({len(frame)} B) od {src[1]}")
            return

        # kopia dla podsluchujacych (pomijamy nadawce, zeby nie slyszal sam siebie)
        for sn in self.sniffers:
            if sn[1] != src[1]:
                self._schedule(frame, sn)

        dst = self.route(hdr)
        lost = self.rng.random() < self.loss
        flipped = 0
        if lost:
            self.stats["lost"] += 1
        else:
            out, flipped = flip_bits(frame, self.ber, self.rng)
            if flipped:
                self.stats["corrupted"] += 1
                self.stats["bits_flipped"] += flipped
            self.stats["forwarded"] += 1
            self._schedule(out, dst)

        kind = "TC" if hdr["type"] == config.TC else "TM"
        status = "LOST" if lost else (f"{flipped} bit(y) przeklamane" if flipped else "ok")
        self._print(f"[eter] {src[1]} -> {dst[1]}  {kind} apid=0x{hdr['apid']:03x} "
                    f"seq={hdr['seq']:5d} len={len(frame):4d}  {status}")

        if self._log:
            self._log.writerow([f"{time.time():.6f}", src[1], dst[1], len(frame), kind,
                                hdr["apid"], hdr["seq"], int(lost), flipped, self.ber, self.loss])
            self._log_file.flush()

    def _print(self, msg):
        if self.verbose:
            print(msg, flush=True)

    def print_stats(self):
        s = self.stats
        print(f"\n[eter] odebrano={s['rx']} przekazano={s['forwarded']} zgubiono={s['lost']} "
              f"uszkodzono={s['corrupted']} (bitow: {s['bits_flipped']}) bledne={s['malformed']}")

    def run(self):
        threading.Thread(target=self._sender_loop, daemon=True).start()
        print(f"[eter] nasluch na {config.HOST}:{config.ETHER_PORT}  "
              f"BER={self.ber} LOSS={self.loss} DELAY={self.delay*1000:.0f}ms "
              f"JITTER={self.jitter*1000:.0f}ms  podsluch -> {[p for _, p in self.sniffers]}")
        self.sock.settimeout(0.5)
        try:
            while True:
                try:
                    frame, src = self.sock.recvfrom(65535)
                except socket.timeout:
                    continue
                except ConnectionResetError:
                    continue  # Windows zglasza ICMP "port unreachable" jako blad recvfrom
                self.handle(frame, src)
        except KeyboardInterrupt:
            pass
        finally:
            self.print_stats()
            if self._log_file:
                self._log_file.close()


def main():
    ap = argparse.ArgumentParser(description="Symulator kanalu radiowego (eter)")
    ap.add_argument("--ber", type=float, default=config.BER, help="bit error rate")
    ap.add_argument("--loss", type=float, default=config.LOSS, help="prawdopodobienstwo utraty ramki")
    ap.add_argument("--delay", type=float, default=config.DELAY_MS, help="opoznienie [ms]")
    ap.add_argument("--jitter", type=float, default=config.JITTER_MS, help="rozrzut opoznienia [ms]")
    ap.add_argument("--log", default=None, help="plik CSV z logiem ramek")
    ap.add_argument("-q", "--quiet", action="store_true", help="nie wypisuj kazdej ramki")
    a = ap.parse_args()
    Ether(a.ber, a.loss, a.delay, a.jitter, a.seed, a.log, not a.quiet).run()


if __name__ == "__main__":
    main()
