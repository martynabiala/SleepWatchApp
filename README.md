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

Projekt obsluguje dwa tryby wysylki e-mail:

- `gmail` - prawdziwa wysylka przez Gmail SMTP,
- `file` - zapis wiadomosci do folderu `sent_emails`.

## Jak uruchomic aplikacje

1. Przejdz do katalogu projektu
   
2. Jesli trzeba, zainstaluj zaleznosci:

```powershell
py -m pip install -r requirements.txt
```

3. Skonfiguruj Gmail SMTP:

- skopiuj plik `.env.example` do `.env`
- wpisz swoj adres Gmail
- wpisz haslo aplikacji Google, nie zwykle haslo do konta

Przykladowy `.env`:

```text
EMAIL_DELIVERY_MODE=gmail
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
EMAIL_TIMEOUT=20
EMAIL_HOST_USER=twoj_adres_gmail@gmail.com
EMAIL_HOST_PASSWORD=abcdefghijklmnop
```

Uwaga:

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

## Jak pokazac, ze modul dziala

### Rejestracja i aktywacja e-mail

1. Wejdz na strone glowna.
2. Kliknij `Rejestracja`.
3. Wypelnij formularz:
   login,
   adres e-mail,
   haslo,
   potwierdzenie hasla.
4. Po wyslaniu formularza pojawi sie komunikat o sprawdzeniu e-maila.
5. Sprawdz skrzynke Gmail podana w formularzu.
6. Otworz wiadomosc od SleepWatch.
7. Kliknij link aktywacyjny.
8. Po otwarciu linku konto zostanie aktywowane i nastapi przekierowanie na `Dashboard`.

### Logowanie

1. Po aktywacji konta przejdz na `Logowanie`.
2. Podaj login i haslo.
3. Po poprawnym logowaniu uzytkownik przechodzi do `Dashboard`.

### Profil uzytkownika

1. Po zalogowaniu kliknij `Profil`.
2. Uzupelnij:
   nazwe wyswietlana,
   grupe wiekowa,
   aktywnosc fizyczna,
   cel snu,
   opis.
3. Kliknij `Zapisz profil`.
4. Po zapisie dane sa widoczne na ekranie profilu i dashboardzie.

### Import danych snu

1. Po zalogowaniu kliknij `Import`.
2. Wybierz zrodlo danych.
3. Wgraj plik CSV zgodny z wymaganym formatem.
4. Kliknij `Importuj dane`.
5. Po imporcie zobaczysz liczbe dodanych rekordow, duplikatow i bledow.

### Historia nocy i szczegoly

1. Kliknij `Noce`.
2. Sprawdz liste zaimportowanych nocy.
3. Uzyj filtrow dat, jesli chcesz zawezic wyniki.
4. Kliknij `Szczegoly`, aby zobaczyc dane jednej nocy.

### Notatki do nocy i jakosc snu

1. Otworz szczegoly wybranej nocy.
2. Ustaw jakosc snu.
3. Dodaj informacje o kofeinie, alkoholu, treningu i stresie.
4. Zapisz notatke.

### Trendy na dashboardzie

1. Po imporcie danych przejdz do `Dashboard`.
2. Sprawdz podsumowanie ostatniej nocy.
3. Zobacz trendy dla 7 i 30 dni.

### Historia importow

1. Wejdz do `Import`.
2. Kliknij `Pelna historia importow`.
3. Sprawdz wynik kazdego importu.

### Reset hasla

1. Na ekranie logowania kliknij `Nie pamietam hasla`.
2. Podaj adres e-mail uzytkownika.
3. Otworz wiadomosc w skrzynce Gmail.
4. Kliknij link do ustawienia nowego hasla.
5. Wpisz nowe haslo i zapisz zmiane.

### Panel administratora

1. Utworz konto administratora przez `py manage.py createsuperuser`.
2. Wejdz na `/admin/`.
3. Zaloguj sie danymi administratora.
4. W panelu mozna zarzadzac:
   uzytkownikami,
   profilami uzytkownikow.

### Wylogowanie

1. Na gornej belce kliknij `Wyloguj`.
2. Uzytkownik wraca na strone startowa.

## Jak udowodnic, ze dziala bez zrzutow ekranu

Do projektu dodane sa automatyczne testy Django. Sprawdzaja one:

- czy rejestracja tworzy konto nieaktywne,
- czy wysylany jest e-mail aktywacyjny,
- czy link aktywacyjny aktywuje konto,
- czy nieaktywne konto nie moze sie zalogowac,
- czy profil mozna edytowac,
- czy reset hasla wysyla e-mail,
- czy import CSV zapisuje rekord snu,
- czy duplikaty sa zliczane,
- czy lista nocy pokazuje tylko dane zalogowanego uzytkownika,
- czy notatka do nocy zapisuje sie poprawnie,
- czy dashboard pokazuje trendy snu.

Uruchom testy poleceniem:

```powershell
py manage.py test
```

Oczekiwany wynik:

```text
Ran 10 tests
OK
```

## Najwazniejsze pliki

- `sleepwatch_project/settings.py` - konfiguracja projektu i backendu e-mail,
- `sleepwatch_project/urls.py` - routing glowny,
- `accounts/forms.py` - formularze rejestracji i logowania,
- `accounts/views.py` - widoki rejestracji, aktywacji, profilu, resetu hasla i dashboardu,
- `accounts/models.py` - model profilu uzytkownika,
- `accounts/urls.py` - routing modulu kont,
- `accounts/tests.py` - testy potwierdzajace dzialanie,
- `sleep/models.py` - modele rekordu snu, notatek i historii importow,
- `sleep/views.py` - widoki importu, listy nocy, szczegolow i notatek,
- `sleep/services.py` - logika parsowania CSV,
- `sleep/tests.py` - testy modułu snu,
- `templates/` - szablony stron.

## Uwaga techniczna

Domyslnie projekt moze dzialac w trybie `file`, ale po uzupelnieniu `.env` obsluguje prawdziwa wysylke przez Gmail SMTP.
