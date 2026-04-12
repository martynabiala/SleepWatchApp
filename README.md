# SleepWatch - etap 2

Ten etap projektu zawiera dzialajacy modul:

- rejestracji uzytkownika,
- logowania,
- wylogowania,
- potwierdzenia konta przez e-mail aktywacyjny.
- profilu uzytkownika,
- resetu hasla przez e-mail,
- panelu administratora,
- importu danych snu z CSV,
- historii nocy,
- szczegolow nocy,
- historii importow.

## Co zostalo zaimplementowane

Uzytkownik:

- zaklada konto przez formularz rejestracji,
- podaje login, e-mail i haslo,
- po rejestracji konto jest tworzone jako nieaktywne,
- aplikacja wysyla wiadomosc aktywacyjna,
- po kliknieciu linku z e-maila konto zostaje aktywowane,
- po aktywacji uzytkownik trafia na dashboard,
- moze uzupelnic profil o nazwe wyswietlana, grupe wiekowa, aktywnosc fizyczna i cel snu,
- moze zresetowac haslo przez e-mail,
- moze importowac dane snu z pliku CSV,
- moze przegladac zapisane noce i szczegoly rekordu,
- widzi historie wykonanych importow,
- moze dodawac notatki do nocy i oznaczac jakosc snu,
- widzi podstawowe trendy 7 i 30 dni na dashboardzie.

Administrator:

- ma dostep do panelu `/admin/`,
- widzi liste uzytkownikow oraz profili,
- moze zarzadzac danymi kont i profili z jednego miejsca.

Projekt obsluguje dwie bazy danych:

- `sqlite` - domyslna baza lokalna zapisywana w pliku `db.sqlite3`,
- `mysql` - baza `MySQL` lub `MariaDB`, np. uruchomiona z `XAMPP`.

Projekt obsluguje tez dwa tryby wysylki e-mail:

- `gmail` - prawdziwa wysylka przez Gmail SMTP,
- `file` - zapis wiadomosci do folderu `sent_emails`.

## Jak uruchomic aplikacje

1. Przejdz do katalogu projektu
   
2. Jesli trzeba, zainstaluj zaleznosci:

```powershell
py -m pip install -r requirements.txt
```

3. Skonfiguruj `.env`:

- skopiuj plik `.env.example` do `.env`
- wybierz baze danych
- jesli chcesz Gmail SMTP, wpisz swoj adres Gmail i haslo aplikacji Google

Przykladowy `.env`:

```text
DEBUG=true
DB_ENGINE=sqlite
DB_NAME=sleepwatch
DB_USER=root
DB_PASSWORD=
DB_HOST=127.0.0.1
DB_PORT=3306
EMAIL_DELIVERY_MODE=gmail
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
EMAIL_TIMEOUT=20
EMAIL_HOST_USER=twoj_adres_gmail@gmail.com
EMAIL_HOST_PASSWORD=abcdefghijklmnop
```

Uwaga dla Gmail:

- musisz miec wlaczone uwierzytelnianie dwuetapowe na koncie Google,
- potem w Google generujesz `Haslo do aplikacji`,
- to wlasnie ten 16-znakowy kod wpisujesz do `EMAIL_HOST_PASSWORD`.
- jesli port `587` nie dziala w Twojej sieci, sprobuj:

```text
EMAIL_PORT=465
EMAIL_USE_TLS=false
EMAIL_USE_SSL=true
```

4. Wykonaj migracje bazy danych:

```powershell
py manage.py migrate
```

5. Uruchom serwer developerski:

```powershell
py manage.py runserver
```

6. Otworz aplikacje w przegladarce:

```text
http://127.0.0.1:8000/
```

## Jak podlaczyc baze z XAMPP

1. Uruchom w `XAMPP Control Panel` modul `MySQL`.

2. Otworz `phpMyAdmin` i utworz baze, na przyklad:

```text
sleepwatch
```

3. Ustaw w `.env`:

```text
DB_ENGINE=mysql
DB_NAME=sleepwatch
DB_USER=root
DB_PASSWORD=
DB_HOST=127.0.0.1
DB_PORT=3306
```

4. Zainstaluj zaleznosci:

```powershell
py -m pip install -r requirements.txt
```

5. Wykonaj migracje:

```powershell
py manage.py migrate
```

6. Jesli chcesz przeniesc dane z obecnej `SQLite`, wykonaj eksport:

```powershell
py manage.py dumpdata --exclude contenttypes --exclude auth.permission > data.json
```

7. Po przelaczeniu `.env` na `mysql` i po migracjach zaimportuj dane:

```powershell
py manage.py loaddata data.json
```

Praktyczna uwaga:

- w typowej lokalnej konfiguracji `XAMPP` uzytkownik `root` nie ma hasla,
- na produkcje lepiej postawic osobna baze i osobnego uzytkownika,
- `XAMPP` tutaj jest tylko dostawca bazy danych, aplikacja dalej dziala jako `Django`.

## Format importu CSV

Aktualny etap obsluguje prosty import pliku CSV z kolumnami:

```text
sleep_date,sleep_duration_minutes,avg_heart_rate,min_heart_rate,max_heart_rate,min_spo2,movement_level
2026-03-20,430,58,49,74,93,low
2026-03-21,405,61,52,78,92,medium
```

Dozwolone wartosci `movement_level`:

- `low`
- `medium`
- `high`
- `unknown`

## Jak utworzyc administratora

Jesli chcesz zalogowac sie do panelu administratora, wykonaj:

```powershell
py manage.py createsuperuser
```

Nastepnie otworz:

```text
http://127.0.0.1:8000/admin/
```
