# SleepWatch - dokumentacja finalna

Stan dokumentu: 2026-05-30  
Typ dokumentu: dokumentacja analityczna, projektowa, techniczna, wdrozeniowa i utrzymaniowa  
Link do aplikacji webowej: `https://sleepwatch.onrender.com/`

## 1. Cel i zakres dokumentu

Celem dokumentu jest opisanie aplikacji SleepWatch przygotowanej jako projekt zaliczeniowy. Dokument obejmuje analize wymagan, projekt UX/UI, architekture, model danych, technologie, wdrozenie, testowanie oraz informacje utrzymaniowe.

SleepWatch jest aplikacja webowa do monitorowania snu. Uzytkownik moze zapisywac noce, importowac dane z pliku CSV, dodawac notatki, analizowac trendy, korzystac z konta demo, sprawdzac tygodniowe raporty oraz obserwowac wplyw nawykow na sen.

## 2. Analiza wymagan

### 2.1 Interesariusze

- Uzytkownik koncowy - osoba chcaca monitorowac sen i swoje nawyki.
- Administrator - osoba zarzadzajaca danymi przez panel administracyjny Django.
- Zespol projektowy - osoby rozwijajace aplikacje.
- Prowadzaca - osoba oceniajaca aplikacje, dokumentacje i sposob wdrozenia.

### 2.2 Wymagania funkcjonalne

| ID | Wymaganie | Opis |
| --- | --- | --- |
| WF-01 | Rejestracja konta | System pozwala utworzyc konto uzytkownika na podstawie loginu, adresu e-mail i hasla. |
| WF-02 | Logowanie | System pozwala zalogowac sie loginem lub adresem e-mail. |
| WF-03 | Reset hasla | System udostepnia mechanizm odzyskiwania hasla przez e-mail. |
| WF-04 | Konto demo | System pozwala obejrzec aplikacje bez zakladania konta. Konto demo jest ograniczone do podgladu. |
| WF-05 | Profil uzytkownika | Uzytkownik moze ustawic dane profilu, avatar, cel snu, grupe wiekowa i aktywnosc fizyczna. |
| WF-06 | Reczne dodawanie nocy | Uzytkownik moze zapisac date snu, czas snu, tetno, wybudzenia, SpO2 i fazy snu. |
| WF-07 | Import CSV | System importuje dane snu z pliku CSV, w tym przykladowe dane z `docs/dane_demo.csv`. |
| WF-08 | Historia nocy | System prezentuje liste zapisanych nocy i szczegoly pojedynczego rekordu. |
| WF-09 | Notatki do nocy | Uzytkownik moze zapisac informacje o kofeinie, alkoholu, treningu, stresie, drzemkach i jakosci snu. |
| WF-10 | Dashboard | System pokazuje ostatnia noc, trend tygodniowy, plan dnia, status danych i skroty do akcji. |
| WF-11 | Analiza snu | System pokazuje trendy dlugosci snu, tetna, wybudzen i faz snu. |
| WF-12 | Raport tygodniowy | System generuje podsumowanie tygodnia i umozliwia pobranie raportu PDF. |
| WF-13 | Eksperyment miesiaca | System pozwala wybrac hipoteze miesiaca i porownywac noce z wybranym czynnikiem. |
| WF-14 | Znajomi i spolecznosc | System zawiera modul znajomych i porownan z podobnymi uzytkownikami. |
| WF-15 | Powiadomienia | System pokazuje powiadomienia, np. przypomnienia i aktualizacje profilu. |
| WF-16 | Tryb jasny i ciemny | Uzytkownik moze korzystac z jasnej albo ciemnej wersji interfejsu. |
| WF-17 | Panel administratora | Administrator ma dostep do panelu Django `/admin/`. |
| WF-18 | Synchronizacja telefonu | Widok synchronizacji jest oznaczony jako funkcja w fazie rozwoju. |

### 2.3 Scenariusze uzycia

#### Scenariusz 1: sprawdzenie aplikacji bez konta

1. Uzytkownik otwiera strone glowna.
2. Wybiera opcje otwarcia konta demo.
3. System loguje uzytkownika na konto demonstracyjne.
4. Uzytkownik oglada dashboard, historie, analize i przykladowe dane.
5. Zamiast standardowego wylogowania system zacheca do zalozenia konta.

#### Scenariusz 2: rejestracja i pierwsze logowanie

1. Uzytkownik wybiera rejestracje.
2. Wpisuje e-mail, grupe wiekowa i haslo.
3. System tworzy konto.
4. Uzytkownik loguje sie i trafia do dashboardu.
5. Uzytkownik moze uzupelnic profil i dodac pierwsza noc.

#### Scenariusz 3: import danych CSV

1. Uzytkownik przechodzi do importu danych.
2. Wybiera plik CSV, np. `docs/dane_demo.csv`.
3. System rozpoznaje kolumny i waliduje dane.
4. Poprawne rekordy sa zapisywane w bazie.
5. Uzytkownik widzi dane w historii i analizie.

#### Scenariusz 4: analiza trendow

1. Uzytkownik otwiera sekcje analizy.
2. Wybiera zakres, np. 30 dni.
3. System pokazuje wykresy czasu snu, tetna, wybudzen i faz snu.
4. Uzytkownik porownuje wyniki z celem snu.

#### Scenariusz 5: eksperyment miesiaca

1. Uzytkownik przechodzi do sekcji eksperymentu.
2. Wybiera czynnik, np. kofeine, stres, trening albo alkohol.
3. System zapisuje hipoteze miesiaca.
4. Po zebraniu danych aplikacja porownuje noce z tym czynnikiem i bez niego.

### 2.4 User stories

- Jako uzytkownik chce szybko dodac noc, aby regularnie zapisywac sen.
- Jako uzytkownik chce importowac CSV, aby nie przepisywac danych recznie.
- Jako uzytkownik chce zobaczyc wykresy, aby zrozumiec trendy snu.
- Jako uzytkownik chce zapisac notatki, aby sprawdzic wplyw kofeiny, stresu, alkoholu i treningu.
- Jako uzytkownik chce korzystac z trybu ciemnego, aby wygodnie uzywac aplikacji wieczorem.
- Jako nowy uzytkownik chce otworzyc demo, aby zobaczyc aplikacje przed rejestracja.
- Jako administrator chce miec panel admina, aby kontrolowac dane systemu.

### 2.5 Wymagania niefunkcjonalne

#### Wydajnosc

- Aplikacja powinna szybko ladowac widoki dashboardu, historii i analizy.
- Import CSV powinien walidowac dane i zapisywac tylko poprawne rekordy.
- Pliki statyczne sa obslugiwane przez WhiteNoise.

#### Bezpieczenstwo

- Aplikacja korzysta z mechanizmow autoryzacji Django.
- Hasla sa przechowywane jako hashe, zgodnie z mechanizmami Django.
- W produkcji `DEBUG=false`.
- W produkcji wymagany jest `SECRET_KEY` w zmiennych srodowiskowych.
- Wlaczona jest ochrona CSRF.
- Konto demo jest ograniczone do podgladu.
- Plik `.env` nie powinien byc dolaczany do paczki oddawanej publicznie.

#### Skalowalnosc

- Lokalnie aplikacja moze dzialac na SQLite.
- Na serwerze moze korzystac z PostgreSQL przez `DATABASE_URL`.
- Warstwa bazy danych jest oddzielona od logiki aplikacji przez ORM Django.

#### Dostepnosc

- Aplikacja jest dostepna jako strona webowa.
- Interfejs zostal dopracowany dla desktopu i telefonu.
- Nawigacja mobilna jest dostosowana do malego ekranu.
- Aplikacja udostepnia tryb jasny i ciemny.

#### Utrzymywalnosc

- Projekt jest podzielony na aplikacje Django: `accounts` i `sleep`.
- Widoki, formularze, modele i serwisy sa rozdzielone.
- Repozytorium zawiera testy backendu.
- Instrukcja uruchomienia znajduje sie w `INSTRUKCJA_ODDANIA.md`.

## 3. Projektowanie UX/UI

### 3.1 Zalozenia UX

UX oznacza doswiadczenie uzytkownika, czyli to, czy aplikacja jest zrozumiala i wygodna. W SleepWatch najwazniejsze bylo, aby uzytkownik mogl szybko:

- zobaczyc najwazniejsze informacje po zalogowaniu,
- dodac noc,
- przejsc do historii,
- sprawdzic analize,
- wejsc w profil albo ustawienia,
- korzystac z aplikacji na telefonie.

### 3.2 Zalozenia UI

UI oznacza wyglad i sposob obslugi interfejsu. Finalna wersja aplikacji wykorzystuje jasna kolorystyke z akcentami fioletowymi, karty informacyjne, ikony, pasek boczny na desktopie i dolna nawigacje na telefonie.

Najwazniejsze decyzje UI:

- bialo-fioletowa stylistyka,
- ograniczenie zielonych akcentow z wczesniejszego wygladu,
- czytelniejsze teksty pomocnicze,
- dopracowany tryb ciemny,
- responsywny topbar i sidebar,
- osobne poprawki dla widoku mobilnego.

### 3.3 Mapa aplikacji

```text
Strona glowna
|-- Logowanie
|-- Rejestracja
|-- Konto demo

Po zalogowaniu
|-- Panel glowny
|-- Dodaj noc
|-- Historia nocy
|   |-- Szczegoly nocy
|-- Check-in poranny
|-- Check-in wieczorny
|-- Nawyki
|-- Wnioski
|-- Analiza
|-- Raport tygodniowy
|-- Eksperyment miesiaca
|-- Znajomi
|-- Sen spolecznosci
|-- Profil
|-- Ustawienia
|-- Powiadomienia
|-- Import CSV
|-- Synchronizacja danych
```

### 3.4 Sciezki uzytkownika

#### User Journey: nowy uzytkownik

1. Wejscie na strone glowna.
2. Otwarcie demo albo rejestracja.
3. Zapoznanie sie z dashboardem.
4. Dodanie pierwszej nocy.
5. Przejscie do analizy.

#### User Journey: regularny uzytkownik

1. Logowanie.
2. Sprawdzenie ostatniej nocy.
3. Wykonanie check-inu.
4. Dodanie notatek.
5. Sprawdzenie trendu tygodniowego.

#### User Journey: uzytkownik importujacy dane

1. Wejscie do importu CSV.
2. Wgranie pliku.
3. Kontrola wyniku importu.
4. Analiza danych na wykresach.

### 3.5 Wireframe low-fidelity

#### Dashboard

```text
+---------------------------------------------------+
| Logo SleepWatch              Ikony / profil       |
+---------------------------------------------------+
| Sidebar | Witaj, Uzytkowniku                      |
|         | [Dodaj noc] [Import CSV] [Raport]       |
|         +----------------+-----------------------+
|         | Ostatnia noc   | Trend tygodniowy      |
|         +----------------+-----------------------+
|         | Status danych  | Plan dnia             |
+---------------------------------------------------+
```

#### Widok mobilny

```text
+-----------------------------+
| Logo        powiad. profil  |
+-----------------------------+
| Karta dashboardu            |
| Ostatnia noc                |
| Trend                       |
| Plan dnia                   |
+-----------------------------+
| Panel | Dodaj | Profil | ...|
+-----------------------------+
```

### 3.6 Makieta high-fidelity

Finalna makieta high-fidelity zostala zrealizowana bezposrednio w HTML/CSS w aplikacji. Obejmuje:

- ekran logowania i rejestracji,
- strone glowna przed logowaniem,
- dashboard,
- historie nocy,
- formularz dodawania nocy,
- analize wykresow,
- raport tygodniowy,
- profil i ustawienia,
- widoki mobilne.

## 4. Architektura i projekt techniczny

### 4.1 Architektura systemu

Aplikacja wykorzystuje architekture warstwowa:

```text
Warstwa prezentacji
HTML templates + CSS + JavaScript

Warstwa logiki aplikacji
Django views + forms + services

Warstwa danych
Django ORM + SQLite/PostgreSQL/MySQL
```

### 4.2 Diagram kontekstowy

```text
Uzytkownik
   |
   v
Przegladarka internetowa
   |
   v
Aplikacja Django SleepWatch
   |
   +--> Baza danych
   +--> System e-mail
   +--> Pliki statyczne
   +--> Import CSV
```

### 4.3 Komponenty aplikacji

| Komponent | Odpowiedzialnosc |
| --- | --- |
| `accounts` | konta, profil, dashboard, ustawienia, znajomi, powiadomienia |
| `sleep` | rekordy snu, import CSV, historia, szczegoly nocy, analiza danych |
| `templates` | warstwa widokow HTML |
| `static` | obrazy, ikony, style pomocnicze, manifest, audio |
| `sleepwatch_project` | konfiguracja projektu Django |
| `docs` | dokumentacja i dane demo |

### 4.4 Przeplyw danych

#### Dodanie nocy

```text
Formularz -> walidacja Django -> SleepRecord -> baza danych -> dashboard/analiza
```

#### Import CSV

```text
Plik CSV -> dekodowanie -> mapowanie kolumn -> walidacja -> zapis rekordow -> historia importow
```

#### Konto demo

```text
Strona glowna -> otworz demo -> utworzenie/odszukanie demo_anna -> login -> dashboard demo
```

### 4.5 Baza danych

Projekt korzysta z ORM Django. Lokalnie domyslnie uzywana jest SQLite, a na produkcji PostgreSQL przez `DATABASE_URL`.

Glowne encje:

- `User` - konto uzytkownika Django,
- `UserProfile` - rozszerzenie profilu,
- `SleepRecord` - pojedyncza noc,
- `SleepNote` - notatki i czynniki wplywajace na sen,
- `ImportHistory` - historia importow CSV,
- `Friendship` - relacje znajomych,
- `Notification` - powiadomienia,
- modele pomocnicze synchronizacji API.

#### Uproszczone ERD

```text
User 1 --- 1 UserProfile
User 1 --- N SleepRecord
SleepRecord 1 --- 1 SleepNote
User 1 --- N ImportHistory
User 1 --- N Notification
User N --- N User przez Friendship
```

### 4.6 Interfejsy zewnetrzne i API

#### Import CSV

Aplikacja obsluguje pliki CSV. Przykladowy plik:

```text
docs/dane_demo.csv
```

Najwazniejsze kolumny:

- `sleep_date`,
- `sleep_duration_minutes`,
- `awake_minutes`,
- `light_sleep_minutes`,
- `deep_sleep_minutes`,
- `rem_minutes`,
- `avg_heart_rate`,
- `min_spo2`.

#### API mobilne

W projekcie istnieja endpointy przygotowane pod synchronizacje mobilna, ale funkcja synchronizacji z telefonem jest oznaczona w aplikacji jako etap rozwoju. W finalnej wersji webowej glownym sposobem wprowadzania danych jest formularz reczny i import CSV.

### 4.7 Technologie i narzedzia

| Obszar | Technologia |
| --- | --- |
| Backend | Python, Django |
| Frontend | HTML, CSS, JavaScript |
| Baza lokalna | SQLite |
| Baza produkcyjna | PostgreSQL |
| ORM | Django ORM |
| Statyczne pliki | WhiteNoise |
| Serwer aplikacji | gunicorn |
| Hosting | Render |
| Kontrola wersji | Git, GitHub |
| Testy | Django TestCase |

## 5. Implementacja i wdrozenie

### 5.1 Opis modulow

#### `accounts`

Modul odpowiada za:

- rejestracje i logowanie,
- reset hasla,
- konto demo,
- profil uzytkownika,
- dashboard,
- powiadomienia,
- znajomych,
- ustawienia,
- widoki pomocnicze zwiazane z nawykami i analiza.

#### `sleep`

Modul odpowiada za:

- model rekordu snu,
- reczne dodawanie nocy,
- import CSV,
- historie importow,
- szczegoly nocy,
- walidacje danych,
- serwisy analityczne.

### 5.2 Wybrane algorytmy i mechanizmy

#### Walidacja CSV

System sprawdza, czy plik ma wymagane kolumny, czy wartosci liczbowe sa poprawne oraz czy suma faz snu nie przekracza logicznie calkowitego czasu snu.

#### Analiza snu

System wylicza trendy na podstawie zapisanych nocy. Analizowane sa m.in.:

- czas snu,
- tetno,
- liczba wybudzen,
- fazy snu,
- realizacja celu snu,
- roznica wzgledem poprzednich okresow.

#### Eksperyment miesiaca

System zapisuje wybrany czynnik i porownuje noce z tym czynnikiem oraz bez niego, jezeli uzytkownik ma wystarczajaca liczbe notatek.

### 5.3 Wzorce i praktyki

- MVC/MVT Django: modele, widoki, szablony.
- ORM do pracy z baza danych.
- Formularze Django do walidacji danych.
- Oddzielenie logiki pomocniczej w serwisach.
- Middleware ograniczajacy zapis na koncie demo.
- Zmienne srodowiskowe dla konfiguracji produkcyjnej.

### 5.4 Instalacja lokalna

Pelna instrukcja znajduje sie w pliku:

```text
INSTRUKCJA_ODDANIA.md
```

Najkrotszy zestaw komend:

```powershell
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
py manage.py migrate
py manage.py runserver
```

### 5.5 Wdrozenie na serwerze

Aplikacja jest wdrozona na Renderze:

```text
https://sleepwatch.onrender.com/
```

Konfiguracja:

```text
Build command: ./build.sh
Start command: gunicorn sleepwatch_project.wsgi:application
```

Zmienne srodowiskowe:

```text
DEBUG=false
SECRET_KEY=<sekretny klucz>
DATABASE_URL=<adres bazy>
ALLOWED_HOSTS_EXTRA=sleepwatch.onrender.com
CSRF_TRUSTED_ORIGINS=https://sleepwatch.onrender.com
```

## 6. Testowanie i jakosc

### 6.1 Strategia testow

Projekt wykorzystuje:

- testy jednostkowe,
- testy integracyjne,
- testy funkcjonalne kluczowych przeplywow,
- reczne testy UI,
- reczne testy wdrozenia na Renderze.

### 6.2 Testy jednostkowe

Testy jednostkowe sprawdzaja mniejsze fragmenty logiki, np. walidacje formularzy, parsowanie CSV i pomocnicze funkcje analityczne.

### 6.3 Testy integracyjne

Testy integracyjne sprawdzaja wspolprace widokow, formularzy, modeli i bazy danych. W projekcie sa testy w:

```text
accounts/tests.py
sleep/tests.py
```

### 6.4 Testy funkcjonalne

Sprawdzane scenariusze:

- rejestracja i logowanie,
- otwarcie konta demo,
- reczne dodanie nocy,
- import CSV,
- zapis notatek,
- analiza danych,
- ograniczenia konta demo,
- reset hasla.

### 6.5 Testy wydajnosciowe i bezpieczenstwa

W projekcie nie przygotowano osobnego automatycznego pakietu testow obciazeniowych. Uwzgledniono jednak:

- korzystanie z ORM Django,
- walidacje danych wejsciowych,
- ochrone CSRF,
- brak hasel w repozytorium,
- produkcyjne `DEBUG=false`,
- oddzielenie konfiguracji przez `.env` i zmienne srodowiskowe.

### 6.6 Raport testow

| Obszar | Sposob testowania | Wynik |
| --- | --- | --- |
| Konta uzytkownikow | testy Django i test reczny | poprawnie |
| Konto demo | testy Django i test reczny | poprawnie |
| Import CSV | testy Django, plik `docs/dane_demo.csv` | poprawnie |
| Dodawanie nocy | testy Django i test reczny | poprawnie |
| Analiza snu | test reczny i testy pomocnicze | poprawnie |
| UI desktop | test reczny | poprawnie |
| UI mobile | test reczny na telefonie | poprawiono |
| Wdrozenie Render | test uruchomienia aplikacji | poprawnie |

## 7. Dokumentacja utrzymaniowa

### 7.1 Podrecznik administratora

Administrator moze:

- zalogowac sie do panelu `/admin/`,
- zarzadzac uzytkownikami,
- przegladac profile,
- kontrolowac rekordy snu,
- sprawdzac historie importow,
- zarzadzac powiadomieniami.

Utworzenie administratora lokalnie:

```powershell
py manage.py createsuperuser
```

### 7.2 Instrukcja uzytkownika

1. Wejdz na strone aplikacji.
2. Zaloz konto albo otworz demo.
3. Dodaj pierwsza noc lub zaimportuj CSV.
4. Uzupelnij notatki przy nocach.
5. Sprawdz dashboard i analize.
6. Korzystaj z raportu tygodniowego i eksperymentu miesiaca.

### 7.3 Historia wersji

| Wersja | Opis |
| --- | --- |
| Etap 1 | Rejestracja, logowanie, podstawowa struktura Django |
| Etap 2 | Import CSV, historia nocy, profil, admin |
| Etap 3 | Dashboard, analiza, notatki, raporty |
| Etap 4 | Konto demo, znajomi, eksperyment miesiaca |
| Finalna | Nowy UI, tryb ciemny, poprawki mobile, fazy snu, instrukcja wdrozenia |

### 7.4 Plan wsparcia i rozwoju

Mozliwe kierunki dalszego rozwoju:

- pelna integracja z aplikacja mobilna i Health Connect,
- glebsza analiza faz snu,
- bardziej rozbudowane rekomendacje,
- eksport raportow,
- testy E2E,
- testy wydajnosciowe,
- rozszerzenie dostepnosci WCAG.

## 8. Zalaczniki

- `INSTRUKCJA_ODDANIA.md` - instrukcja uruchomienia i wdrozenia.
- `docs/dane_demo.csv` - przykladowy plik importu CSV.
- `README.md` - podstawowe informacje projektowe.
- `render.yaml` - konfiguracja wdrozenia Render.
