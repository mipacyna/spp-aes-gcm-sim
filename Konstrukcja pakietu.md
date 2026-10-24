
Jak jest zbudowany pakiet CCSDSS SPP: **nagłówek główny 48 bitów (6 bajtów)** + **pole danych** (opcjonalny drugi nagłówek + dane). 

## Ogólna budowa:

| Bity  | Pole                              | Rozmiar   | Wartości                        |
| ----- | --------------------------------- | --------- | ------------------------------- |
| 0–2   | Wersja (PVN)                      | 3 b       | rekomendowane `000`             |
| 3     | Typ pakietu                       | 1 b       | `0` telemetria, `1` telekomenda |
| 4     | Flaga drugiego nagłówka           | 1 b       | `0` brak, `1` obecny            |
| 5–15  | APID                              | 11 b      | $0\ldots 2047$, `2047` = IDLE   |
| 16–17 | Flagi sekwencji                   | 2 b       | `00` / `01` / `10` / `11`       |
| 18–31 | Licznik sekwencji / nazwa pakietu | 14 b      | $0\ldots 16383$                 |
| 32–47 | Długość pola danych               | 16 b      | $C-1$                           |
| 48…   | Pole danych                       | 1–65536 B | drugi nagłówek i/lub dane       |

Bity 3–15 to razem pole identyfikacji pakietu (Packet Identification), a bity 16–31 to kontrola sekwencji (Packet Sequence Control).

## 1. Wersja (bity 0–2)
- Zakodowana binarnie, w praktyce **zawsze `000`**, co oznacza „pakiet CCSDS w wersji 1”.
- Pole jest po to, żeby w przyszłości dało się wprowadzić inne struktury pakietów.

## 2. Identyfikacja pakietu (bity 3–15, razem 13 bitów)
1. **Typ pakietu** (bit 3): `0` = telemetria (raporty itp.), `1` = telekomenda (komendy, requesty).
2. **Flaga drugiego nagłówka** (bit 4): `0` = nie ma, `1` = jest.
3. **APID** (bity 5–15, 11 bitów):
   - unikalny tylko w swojej **domenie nazewniczej** (np. w obrębie danej misji), więc gdzie indziej ten sam APID może znaczyć coś innego (jak port na danym hoście),
   - pakiety **IDLE** mają APID `11111111111` $= 2^{11}-1 = 2047$. To pakiety-wypełniacze: lecą, kiedy nie ma nic do wysłania, a odbiorca je po prostu wyrzuca.

## 3. Flagi sekwencji (bity 16–17)
| Flagi | Znaczenie |
|---|---|
| `00` | kontynuacja (środkowy kawałek danych) |
| `01` | pierwszy segment |
| `10` | ostatni segment |
| `11` | dane niesegmentowane (całość w jednym pakiecie) |

## 4. Licznik sekwencji albo nazwa pakietu (bity 18–31, 14 bitów)
- **Telemetria** (typ `0`): wymagany licznik sekwencji.
- **Telekomenda** (typ `1`): licznik sekwencji **albo** nazwa pakietu.

### Licznik sekwencji
1. Kolejny numer (binarnie) każdego pakietu wygenerowanego przez daną aplikację, rozpoznawaną po APID. **Każdy APID ma swój własny, niezależny licznik**, niczego się tu nie dzieli z innymi.
2. Licznik ma być **ciągły w modulo $2^{14} = 16384$**. **Nie wolno go resetować przed dojściem do 16383**, chyba że jest to nieuniknione.
3. Istnieje by odbiorca mógł **posortowac pakiety z jednego APID w dobrej kolejności**, jeśli pomieszaja się w transporcie, i żeby **wyłapać utracone pakiety**.
4. Jak licznik się wyzeruje przez nieunikniony restart całego procesu, to kompletnosc procesu nie jest gwarantowana.
5. Licznik można łączyć z **kodem czasu** (pole czasu w drugim nagłówku, nieobowiązkowe). Wtedy da się ułożyć pakiety nawet przez długi czas misji.

### Nazwa pakietu (Packet Name)
- Pozwala odróżnić konkretny pakiet od innych **w ramach tej samej sesji komunikacji**.
- Może to być **dowolny 14-bitowy wzór**, norma nic nie narzuca.

## 5. Długość pola danych (bity 32–47, 16 bitów)
- $C$ = liczba **oktetów (bajtów) w polu danych**.
- W polu zapisujemy $C - 1$. Np. 4 bajty danych → wpisujemy `3`.
- Dlatego pole danych ma minimum 1 bajt, a maksimum $2^{16} = 65536$ bajtów.

## 6. Pole danych
1. Musi zawierać **co najmniej jedno** z poniższych, dokładnie w tej kolejności:
   - **drugi nagłówek**,
   - **dane użytkownika**.
2. **Drugi nagłówek**:
   - jeśli jest, leży **od razu za nagłówkiem głównym**, bez przerwy,
   - jest **obowiązkowy jeśli nie ma danych użytkownika**,
   - jego obecność sygnalizuje **flaga drugiego nagłówka (w pierwszym naglowku) = `1`** (bit 4).
1. **Co siedzi w drugim nagłówku**, w tej kolejności (oba sa opcjonalne):
   2. **Pole czasu**: P (preambuła, czyli jaki to format czasu; może być pominięta, jeśli format jest z góry ustalony) + T (właściwy czas).
   3. **Pomocnicze pole danych** (ancillary data): zawartość ustala misja, np. info o czasie lokalnym/wewnętrznym albo położenie satelity. Norma niczego tu nie narzuca, położenie to tylko przykład.


źródło: https://ccsds.org/Pubs/133x0b2e2.pdf
