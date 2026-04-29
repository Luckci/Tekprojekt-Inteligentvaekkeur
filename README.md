# Tekprojekt - Addon: Intelligent Vækkeur (Eksamensprojekt)

Dette repository indeholder et lille addon / hjælpeprogram til et eksamensprojekt (ikke hele eksamensprojektet). Formålet er at lade sensor-/alarm-backend og en Flutter-android/iOS-app kommunikere mellem en computer/server og appen.

Bemærk: Dette er et tilføjelsesprojekt til et eksamensprojekt — lærere eller andre kan frit gennemgå kildekoden her.

**Indhold**
- `Tek-Backend/` – Python-backend (flask/fastapi afhængigt af implementering) som kører på en computer eller server.
- `TekProjektAlarm/` – Flutter-app-projekt (appen). Appens kode ligger især under `TekProjektAlarm/flutter_alarm_app/lib`.
- `Vækkeurs-kode/` – eventuelle Arduino/ESP-ino-filer (hardware-eksperimenter).

**Vigtigt (konfiguration før kørsel)**

1) Udskift IP-adresse i TekProjektAlarm
- Appen bruger en hardkodet eller placeholder IP-adresse som peger på den computer/server hvor backend (i `Tek-Backend`) kører. Du skal åbne app-koden og erstatte placeholder'en med den faktiske IP-adresse for den maskine, der kører backend-skriptet.
- Sti til appens hovedfil: [TekProjektAlarm/flutter_alarm_app/lib/main.dart](TekProjektAlarm/flutter_alarm_app/lib/main.dart#L1)

Typisk skal du finde en linje der ligner (eksempel):

```dart
// Erstat følgende med serverens IP
const String serverIp = 'REPLACE_WITH_SERVER_IP';
```

Udskift `'REPLACE_WITH_SERVER_IP'` med den IP-adresse du finder i næste trin.

2) Find IP-adressen på computeren/serveren
- Windows (cmd eller PowerShell):

```powershell
ipconfig
```

- Linux / macOS:

```bash
ip addr show
# eller kortere: hostname -I
```

Find den IPv4-adresse som er tilgængelig for samme netværk som mobilenheden (typisk 192.168.x.x eller 10.x.x.x på lokale netværk).

3) Start backend (på server/computer)
- Opret og aktivér et Python-virtualenv, installer afhængigheder og kør backend.

Eksempel (Windows PowerShell / cmd):

```powershell
cd Tek-Backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Eksempel (Linux/macOS):

```bash
cd Tek-Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Bemærk: Hvis `app.py` bruger en anden kommando eller et entrypoint (f.eks. `schedule.py` eller Docker), følg den tilsvarende fils instruktion.

4) Konfigurer og kør Flutter-appen
- Efter at have erstattet IP-adressen i [TekProjektAlarm/flutter_alarm_app/lib/main.dart](TekProjektAlarm/flutter_alarm_app/lib/main.dart#L1), start appen via Flutter tooling (for udvikling på emulator eller fysisk enhed):

```bash
cd TekProjektAlarm/flutter_alarm_app
flutter pub get
flutter run
```

Sørg for at mobilenheden er på samme netværk som serveren, eller brug port-forwarding / VPN efter behov.

**Fejlsøgning**
- Hvis appen ikke kan kontakte backend: kontroller at backendprocessen kører, at IP/port er korrekt, og at ingen firewall blokerer trafikken.
- Test adgang fra en anden enhed til serveren ved at hente en simpel status-URL (fx `http://<SERVER_IP>:<PORT>/status`) i en browser.

**Privatliv / eksamen**
- Dette repository er beregnet som et addon til et eksamensprojekt. Alle kildefiler er med, så underviser(e) frit kan gennemgå koden. Der er ingen følsomme data i denne mappe; hvis I tilføjer sådanne, fjern dem eller brug miljøvariabler i stedet for hardkodede hemmeligheder.

**Kontakt / videre arbejde**
- Vil du have, at jeg:
	- hjælper med at finde og ændre den nøjagtige placeholder i main.dart?
	- opretter et lille script til automatisk at finde maskinens IP og indsætte den i en konfigurationsfil?

Tak — sig til hvis du vil at jeg laver en commit med eksempelkode eller en lille guide til at automatisere IP-indstilling.

