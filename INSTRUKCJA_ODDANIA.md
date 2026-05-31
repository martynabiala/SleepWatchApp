# SleepWatch - instrukcja oddania, uruchomienia i wdrozenia

## 1. Pliki aplikacji

Do oddania nalezy przekazac archiwum ZIP z plikami projektu SleepWatch.

W archiwum powinny znalezc sie przede wszystkim:

- `accounts/` - modul kont uzytkownikow, profilu, powiadomien, znajomych i dashboardu,
- `sleep/` - modul zapisu, importu i analizy snu,
- `sleepwatch_project/` - konfiguracja projektu Django,
- `templates/` - szablony HTML aplikacji,
- `static/` - pliki statyczne, grafiki, ikony, manifest i muzyka,
- `docs/` - dokumentacja projektu,
- `docs/dane_demo.csv` - przykladowy plik CSV do testowego importu danych snu,
- `manage.py`,
- `requirements.txt`,
- `build.sh`,
- `render.yaml`,
- `README.md`,
- `INSTRUKCJA_ODDANIA.md`.

Nie nalezy pakowac:

- folderu srodowiska wirtualnego, np. `.venv/`, `venv/`,
- folderu `.git/`,
- plikow cache, np. `__pycache__/`, `.pytest_cache/`,
- lokalnych plikow build, np. `staticfiles/`,
- lokalnych plikow konfiguracyjnych z haslami, np. `.env`,
- lokalnej bazy `db.sqlite3`, jezeli oddawana wersja ma byc uruchamiana od zera lub na serwerze z osobna baza danych.

## 2. Link do aplikacji na serwerze web

Aplikacja jest dostepna pod adresem:

```text
https://sleepwatch.onrender.com/
```

## 3. Wymagania techniczne

Aplikacja zostala przygotowana jako projekt Django.

Wymagane srodowisko:

- Python 3.13,
- pip,
- baza danych SQLite lokalnie albo PostgreSQL/MySQL na serwerze,
- przegladarka internetowa.

Glowne biblioteki znajduja sie w pliku `requirements.txt`:

- Django,
- Pillow,
- gunicorn,
- whitenoise,
- dj-database-url,
- psycopg2-binary,
- PyMySQL.

## 4. Uruchomienie lokalne

1. Rozpakowac projekt i przejsc do katalogu aplikacji:

```powershell
cd Aplikacja_SleepWatch
```

2. Utworzyc srodowisko wirtualne:

```powershell
py -m venv .venv
```

3. Aktywowac srodowisko:

```powershell
.venv\Scripts\activate
```

4. Zainstalowac zaleznosci:

```powershell
py -m pip install -r requirements.txt
```

5. Przygotowac plik `.env` w katalogu glownym projektu.

Przykladowa konfiguracja lokalna:

```text
DEBUG=true
SECRET_KEY=dev-only-change-me
DB_ENGINE=sqlite
EMAIL_DELIVERY_MODE=file
```

6. Wykonac migracje bazy danych:

```powershell
py manage.py migrate
```

7. Opcjonalnie utworzyc konto administratora:

```powershell
py manage.py createsuperuser
```

8. Opcjonalnie przygotowac dane demo:

```powershell
py manage.py seed_demo_data --users 1 --days 14 --seed 42
```

9. Uruchomic aplikacje:

```powershell
py manage.py runserver
```

10. Otworzyc aplikacje w przegladarce:

```text
http://127.0.0.1:8000/
```

## 5. Uruchomienie na serwerze web

Projekt jest przygotowany do wdrozenia na Renderze.

W repozytorium znajduja sie pliki:

- `render.yaml` - konfiguracja uslugi webowej i bazy danych,
- `build.sh` - skrypt instalacji zaleznosci, zbierania statycznych plikow i migracji,
- `requirements.txt` - lista zaleznosci Python,
- `sleepwatch_project/wsgi.py` - punkt startowy aplikacji dla `gunicorn`.

Konfiguracja uslugi webowej:

```text
Build command: ./build.sh
Start command: gunicorn sleepwatch_project.wsgi:application
```

Zmienne srodowiskowe wymagane na serwerze:

```text
DEBUG=false
SECRET_KEY=<wygenerowany sekretny klucz>
DATABASE_URL=<adres bazy PostgreSQL>
ALLOWED_HOSTS_EXTRA=sleepwatch.onrender.com
CSRF_TRUSTED_ORIGINS=https://sleepwatch.onrender.com
```

Na Renderze `DATABASE_URL` moze byc podlaczony automatycznie z bazy danych PostgreSQL.

Podczas wdrozenia skrypt `build.sh` wykonuje:

```bash
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
```

Po wdrozeniu aplikacja dziala przez:

```text
gunicorn sleepwatch_project.wsgi:application
```

## 6. Konto demo

Aplikacja obsluguje konto demo. Jezeli po wdrozeniu konto demo nie istnieje, nalezy uruchomic komende:

```powershell
py manage.py seed_demo_data --users 1 --days 14 --seed 42
```

Na serwerze Render te komende mozna uruchomic w Shellu uslugi webowej.

## 7. Przykladowe dane CSV

W folderze `docs/` znajduje sie plik:

```text
docs/dane_demo.csv
```

Jest to przykladowy plik z danymi snu, ktory mozna wykorzystac do przetestowania importu CSV w aplikacji. Plik zawiera m.in. date snu, czas snu, czas czuwania, sen lekki, sen gleboki, REM, liczbe wybudzen, srednie tetno i minimalne SpO2.

## 8. Krotki opis aplikacji

SleepWatch to aplikacja webowa do monitorowania snu. Uzytkownik moze rejestrowac noce, dodawac notatki, analizowac trendy, sprawdzac tygodniowe raporty, porownywac nawyki i korzystac z konta demo. Aplikacja zawiera takze widoki profilu, znajomych, powiadomien, analize podstawowych parametrow snu oraz zapis danych o fazach snu. Synchronizacja danych z telefonu zostala oznaczona jako funkcja w fazie rozwoju.
