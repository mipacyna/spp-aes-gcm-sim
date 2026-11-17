HOST = "127.0.0.1"
EARTH_PORT = 5001
SAT_PORT = 5002
APID_TC = 0x10      # komendy ziemia -> satelita
APID_TM = 0x11      # telemetria satelita -> ziemia
TC, TM = 1, 0

# --- eter (symulator kanalu radiowego) ---
ETHER_PORT = 5000   # ziemia, satelita i atakujacy wysylaja wszystko tutaj
ATTACK_PORT = 5003  # atakujacy slucha tu kopii wszystkiego, co leci przez eter
# porty, na ktore eter rozsyla kopie kazdej ramki (kanal radiowy jest jawny)
SNIFFER_PORTS = [ATTACK_PORT]

# domyslne parametry kanalu (mozna nadpisac z linii polecen eter.py)
BER = 0.0           # bit error rate - prawdopodobienstwo przeklamania pojedynczego bitu
LOSS = 0.0          # prawdopodobienstwo zgubienia calej ramki
DELAY_MS = 0.0      # stale opoznienie propagacji [ms]
JITTER_MS = 0.0     # losowy rozrzut opoznienia +/- [ms]
