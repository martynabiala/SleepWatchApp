# Biezacy stan aplikacji i dokumentacji SleepWatch

Data opracowania: 2026-05-24
Projekt: SleepWatch
Link do aplikacji: https://sleepwatch.onrender.com
Repozytorium lokalne: `D:\Aplikacja_SleepWatch`

## 1. Cel dokumentu

Dokument przedstawia aktualny stan aplikacji SleepWatch oraz opisuje technologie i rozwiązania zastosowane w projekcie. Zawiera podsumowanie gotowych funkcji, architektury, modelu danych, integracji, sposobu uruchomienia i stanu dokumentacji.

## 2. Opis aplikacji

SleepWatch to aplikacja webowa wspierająca monitorowanie snu. Użytkownik może utworzyć konto, aktywować je przez e-mail, uzupełnić profil, dodawać lub importować dane snu, analizować historię nocy, zapisywać notatki dotyczące snu oraz obserwować trendy w dashboardzie.

Projekt zawiera także backendowe API przygotowane do synchronizacji danych z aplikacji mobilnej oraz prototyp aplikacji Android wykorzystującej Health Connect.

## 3. Aktualny stan funkcjonalny

W obecnej wersji zaimplementowano:

- rejestrację użytkownika,
- aktywację konta przez e-mail,
- obsługę kont dziecka z mechanizmem zgody rodzica,
- logowanie loginem lub adresem e-mail,
- wylogowanie,
- reset hasła przez e-mail,
- profil użytkownika z nazwą, awatarem, grupą wiekową, stylem życia i celem snu,
- ustawienia konta,
- konto demonstracyjne z ograniczeniami zapisu,
- dashboard z podsumowaniem danych snu,
- analizę snu w okresach 7, 30, 90 i 365 dni,
- raport tygodniowy,
- widoki poranne i wieczorne,
- centrum nawyków,
- dziennik wniosków,
- porównanie snu w grupie,
- moduł znajomych,
- odznaki i osiągnięcia,
- formularz zgłaszania błędów,
- powiadomienia użytkownika,
- ręczne dodawanie rekordu snu,
- import danych snu z CSV,
- historię importów,
- listę nocy z filtrowaniem,
- szczegóły pojedynczej nocy,
- notatki do nocy, m.in. jakość snu, kofeina, drzemka, alkohol, trening i stres,
- automatyczną ocenę nocy,
- API synchronizacji danych snu,
- mobilne endpointy do logowania, rejestracji, preferencji, historii snu, ręcznego dodawania snu i podsumowania.

## 4. Technologie

| Obszar | Zastosowana technologia |
|---|---|
| Backend | Python 3.13, Django 6 |
| Frontend | Django Templates, HTML, CSS, JavaScript |
| Baza lokalna | SQLite |
| Alternatywna baza lokalna | MySQL / MariaDB |
| Baza produkcyjna | PostgreSQL przez `DATABASE_URL` na Renderze |
| ORM | Django ORM |
| Serwer produkcyjny | Gunicorn |
| Pliki statyczne | WhiteNoise |
| E-mail | Django file backend albo Gmail SMTP |
| Hosting | Render |
| Aplikacja mobilna/prototyp | Android, Kotlin, Health Connect |
| Testy | Django TestCase |
| Kontrola wersji | Git |

Główne zależności projektu znajdują się w pliku `requirements.txt`:

- `Django==6.0.3`,
- `Pillow==11.1.0`,
- `gunicorn==23.0.0`,
- `whitenoise==6.9.0`,
- `dj-database-url==2.3.0`,
- `psycopg2-binary==2.9.10`,
- `PyMySQL==1.1.1`.

## 5. Architektura projektu

Projekt ma strukturę typową dla aplikacji Django:

- `sleepwatch_project` - konfiguracja główna projektu, routing, ustawienia środowiskowe, WSGI/ASGI,
- `accounts` - konta użytkowników, profil, logowanie, rejestracja, dashboard, znajomi, powiadomienia i część API mobilnego,
- `sleep` - rekordy snu, import CSV, historia nocy, notatki, analiza i API synchronizacji,
- `templates` - szablony HTML,
- `static` - pliki statyczne, grafiki, favicony i zasoby wizualne,
- `docs` - dokumentacja projektu,
- `mobile_health_connect_prototype` - prototyp aplikacji Android do integracji z Health Connect.

Aplikacja korzysta z architektury MVT charakterystycznej dla Django:

- model opisuje dane i relacje,
- view obsługuje logikę widoków i endpointów,
- template odpowiada za prezentację HTML,
- formularze odpowiadają za walidację danych wejściowych,
- `services.py` zawiera część logiki importu i synchronizacji.

## 6. Model danych

Najważniejsze encje w projekcie:

| Encja | Przeznaczenie |
|---|---|
| `User` | konto użytkownika Django |
| `UserProfile` | rozszerzony profil użytkownika |
| `SleepRecord` | pojedynczy rekord nocy |
| `SleepNote` | notatka i czynniki wpływające na sen |
| `ImportHistory` | historia importów CSV |
| `SleepSyncConnection` | status połączenia synchronizacji |
| `SleepApiToken` | token API do synchronizacji |
| `Friendship` | relacje między użytkownikami |
| `BugReport` | zgłoszenia błędów |
| `UserNotification` | powiadomienia użytkownika |

Relacje:

- jeden użytkownik ma jeden profil,
- jeden użytkownik może mieć wiele rekordów snu,
- jeden rekord snu może mieć jedną notatkę,
- jeden użytkownik może mieć wiele importów,
- jeden użytkownik może mieć wiele powiadomień i zgłoszeń błędów,
- synchronizacja mobilna wykorzystuje token API przypisany do użytkownika.

## 7. Import i synchronizacja danych

Aplikacja obsługuje import plików CSV. Dane są normalizowane i zapisywane jako rekordy `SleepRecord`. System zapisuje też historię importu, liczbę dodanych rekordów, duplikatów i błędów.

Dostępny jest również endpoint:

```text
POST /api/sleep/sync/
```

Endpoint służy do synchronizacji danych snu z aplikacji mobilnej lub zewnętrznego źródła. Autoryzacja odbywa się przez token API, np. w nagłówku:

```text
Authorization: Bearer <token>
```

W projekcie istnieją także endpointy mobilne:

- `POST /api/mobile/login/`,
- `POST /api/mobile/signup/`,
- `POST /api/mobile/preferences/`,
- `GET /api/mobile/summary/`,
- `GET /api/mobile/sleep-history/`,
- `POST /api/mobile/manual-sleep/`.

## 8. Wdrożenie

Projekt jest przygotowany do wdrożenia na Renderze. Konfiguracja znajduje się w pliku `render.yaml`.

Aktualna konfiguracja obejmuje:

- usługę webową `sleepwatch-app`,
- komendę budowania `./build.sh`,
- komendę startową `gunicorn sleepwatch_project.wsgi:application`,
- bazę danych `sleepwatch-db`,
- zmienne środowiskowe dla trybu produkcyjnego,
- zadania cykliczne do tworzenia powiadomień porannych i wieczornych.

Link do aplikacji webowej:

```text
https://sleepwatch.onrender.com
```

## 9. Uruchomienie lokalne

Podstawowe kroki uruchomienia:

```powershell
py -m pip install -r requirements.txt
py manage.py migrate
py manage.py runserver
```

Adres lokalny:

```text
http://127.0.0.1:8000/
```

Konfiguracja środowiska znajduje się w pliku `.env`. Projekt obsługuje SQLite, MySQL/MariaDB oraz produkcyjną bazę przez `DATABASE_URL`.

## 10. Stan testów i walidacji

W projekcie znajdują się testy w aplikacjach `accounts` i `sleep`. Django wykrywa 83 testy dla tych modułów.

Wykonana walidacja:

```text
py manage.py check
```

Wynik:

```text
System check identified no issues (0 silenced).
```

Pełne uruchomienie testów lokalnie wymaga uporządkowania lub ponownego użycia istniejącej bazy testowej MySQL `test_sleepwatch`. Podczas próby testowej Django wykryło istniejącą bazę testową i zatrzymało się na pytaniu interaktywnym. Uruchomienie z `--keepdb` nie zakończyło się w limicie 2 minut, dlatego w aktualnym raporcie potwierdzony jest wynik `manage.py check`, a pełny wynik testów pozostaje do ponownego wykonania.

## 11. Stan dokumentacji

W repozytorium znajdują się:

- `README.md` - instrukcja uruchomienia i opis podstawowych funkcji,
- `SleepWatch_specyfikacja_Django.md` - wcześniejsza specyfikacja projektu,
- `docs/SleepWatch_Dokumentacja_ver_1.md` - główna dokumentacja projektowa,
- `docs/SleepWatch_Dokumentacja_ver_1.docx` - wersja Word dokumentacji,
- `docs/sleep_sync_api.md` - dokumentacja API synchronizacji,
- `docs/sync_sources_plan.md` - plan źródeł synchronizacji,
- `docs/assets/hifi/` - makiety high-fidelity.

Dokumentacja opisuje cel systemu, wymagania, architekturę, model danych, UX/UI, wdrożenie, testowanie i dalszy rozwój. Obecny plik jest uzupełnieniem dokumentacji o bieżący stan aplikacji na dzień 2026-05-24.

## 12. Elementy do dalszego rozwoju

Najważniejsze kolejne kroki:

- ponowne pełne uruchomienie testów po uporządkowaniu bazy testowej,
- rozszerzenie testów end-to-end,
- dalsze dopracowanie prototypu Android i integracji Health Connect,
- dopisanie pełnej dokumentacji wszystkich endpointów mobilnych,
- rozwinięcie testów bezpieczeństwa i wydajności,
- uzupełnienie dokumentacji o aktualne zrzuty ekranów działającej aplikacji,
- dopracowanie funkcji porównań grupowych i społecznościowych.

## 13. Podsumowanie

SleepWatch jest działającą aplikacją Django do monitorowania i analizy snu. Aktualna wersja obejmuje konta użytkowników, profile, import i ręczne dodawanie danych snu, dashboard, analizy, notatki, powiadomienia, znajomych, raporty oraz API do synchronizacji mobilnej. Projekt posiada konfigurację produkcyjną dla Rendera, dokumentację w Markdown i Word oraz prototyp aplikacji Android przygotowany pod Health Connect.

Aplikacja jest rozwijana iteracyjnie. Najważniejsze funkcje webowe są zaimplementowane, a dalszy rozwój powinien skupić się na pełnym przebiegu testów, dopracowaniu integracji mobilnej i aktualizacji dokumentacji o finalne zrzuty ekranów.
