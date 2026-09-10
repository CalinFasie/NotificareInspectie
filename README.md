# VehicleCheck

Aplicație Windows pentru vehicule, CRP, inspecții și notificări email.

## Instalare

Necesită Python 3.10+, SQL Server și ODBC Driver 18 for SQL Server.
Conexiunea SQL utilizează contul Windows curent. Baza trebuie să conțină
tabelele CONFIG, VEHICLES și INSPECTIONS. Pentru o bază nouă, selectați baza
VehicleCheck și executați `schema.sql`, extras din specificația Explorare 2 și
completat cu cele trei coloane de notificări. Nu îl executați peste tabele existente.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Configurați serverul SQL și SMTP în `config.py`. Executați manual
`notification_columns.sql` în baza VehicleCheck dacă lipsesc coloanele de evidență.
Parola SMTP se citește din variabila de mediu `VEHICLECHECK_SMTP_PASSWORD`.
Nu o salvați în repository. Contul Windows trebuie configurat în CONFIG;
primul administrator trebuie creat în baza de date.

## Utilizare

```powershell
.\.venv\Scripts\python.exe main.py
.\.venv\Scripts\python.exe notifications.py --dry-run
.\.venv\Scripts\python.exe notifications.py
```

Comanda cu `--dry-run` citește baza și afișează alertele, fără emailuri sau
actualizări SQL. Comanda fără acest argument trimite emailuri reale.
Pentru Windows Task Scheduler configurați rularea zilnică la 08:00 și folosiți
calea absolută către Python din `.venv`, argumentul cu calea către
`notifications.py` și directorul proiectului ca director de lucru. Contul sarcinii
necesită acces SQL și variabila de mediu SMTP. Programarea nu este creată automat.

Administratorii pot adăuga, edita și activa/dezactiva utilizatori din Configurare.
Butonul „Schimbă alocarea” permite administratorilor schimbarea Seller/Advisor
pentru un vehicul activ. Eliminarea Advisor șterge și CRP, cu confirmare.
Un consilier nu poate fi alocat înainte de introducerea CRP. Selectorii afișează
numele și username-ul, inclusiv pentru persoane cu nume identice.
Username-ul existent nu poate fi redenumit, pentru a păstra alocările și istoricul.
Contul activ și permisiunile se reverifică înainte de fiecare salvare din interfață.
Nu se pot dezactiva singuri sau schimba propriul rol/username în sesiunea curentă.

## Notificări și erori

Data este calculată în Europe/Bucharest. CRP lipsă produce alerte din ziua 6,
inspecțiile în ziua 27 și din ziua 30. Inspecția făcută astăzi oprește alerta
doar după ziua 30, conform regulii curente.

O blocare SQL de sesiune împiedică două procese de notificare să ruleze simultan.
O eroare este raportată în stderr cu VehicleID și procesarea continuă cu următorul
vehicul. Codul de ieșire este 1 dacă există erori, inclusiv la obținerea blocării;
altfel este 0. Conexiunea SMTP are timeout de 30 de secunde.
O eroare a alertei CRP nu împiedică procesarea alertei de inspecție pentru același vehicul.
Conexiunile SQL sunt închise după operații; conectarea are timeout de 10 secunde,
iar comenzile SQL de 30 de secunde. Salvările CRP/facturare fără efect sunt raportate.
Adăugarea inspecției blochează rândul vehiculului până la finalizarea tranzacției,
astfel încât o facturare concurentă să nu permită inserarea după închidere.

Refuzurile SMTP, inclusiv cele parțiale, sunt raportate ca erori și notificarea
nu este marcată drept trimisă. Destinatarii acceptați pot primi din nou emailul
la reexecutare. Verificați raportul de eroare înainte de reexecutare.
La o întrerupere după acceptarea emailului, dar înainte de salvarea în SQL,
mesajul poate fi retrimis. SMTP și SQL nu oferă aici o tranzacție comună;
evidența zilnică și blocarea nu garantează livrarea exact o singură dată.

## Verificare locală fără SQL sau email

```powershell
.\.venv\Scripts\python.exe -B -m unittest -v
```

Testele simulează serviciile externe. Interfața și integrarea SQL/SMTP necesită
verificare separată într-un mediu configurat.
