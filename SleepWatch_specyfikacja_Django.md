# SleepWatch - poprawiona specyfikacja projektu Django

## 1. Opis aplikacji

SleepWatch to webowa aplikacja w Pythonie i Django do monitorowania snu na podstawie danych z opaski Mi Band. Aplikacja sluzy przede wszystkim do analizy wlasnych wynikow uzytkownika w czasie, a nie do bezposredniego porownywania danych medycznych z innymi osobami.

Glowne zalozenie:

- najwazniejsze jest porownywanie "uzytkownik vs jego wczesniejsze wyniki",
- porownania z innymi sa ograniczone do bezpiecznych, zagregowanych danych grupowych,
- nie ma modulu znajomych,
- zamiast tego sa grupy porownawcze z podzialem wedlug wieku i stylu zycia,
- analizy grupowe sa dostepne dopiero po zebraniu odpowiedniej ilosci danych, np. po 30 dniach.

## 2. Zmieniona wizja projektu

Wzgledem pierwotnej koncepcji wprowadzamy nastepujace zmiany:

- usuwamy porownywanie danych medycznych "Ty vs konkretny inny uzytkownik",
- usuwamy modul znajomych,
- zostawiamy grupy, ale ich rola jest ograniczona do porownan ogolnych metryk snu,
- grupy sa kategoryzowane wedlug wieku i stylu zycia,
- porownania grupowe nie pokazuja wrazliwych danych pojedynczych osob,
- system najpierw buduje profil i trendy danego uzytkownika, a dopiero potem pozwala odniesc wynik do grupy podobnych osob.

## 3. Dla kogo jest aplikacja

Aplikacja jest przeznaczona dla:

- osob posiadajacych Mi Band i chcacych monitorowac swoj sen,
- osob, ktore chca obserwowac trendy snu na przestrzeni tygodni i miesiecy,
- osob, ktore chca zobaczyc, jak ich wyniki wypadaja na tle podobnej grupy wiekowej i stylu zycia,
- osob, ktore chca laczyc dane snu z codziennymi notatkami, np. stres, trening, kofeina, alkohol.

## 4. Glowny cel aplikacji

Glownym celem aplikacji jest wspieranie samoobserwacji i budowania zdrowych nawykow snu poprzez:

- import i bezpieczne przechowywanie danych z Mi Band,
- prezentowanie historii nocy i trendow,
- wykrywanie zmian wzgledem wlasnych poprzednich wynikow,
- laczenie danych liczbowych z kontekstem dnia,
- ostrozne i opoznione porownanie do podobnej grupy uzytkownikow.

## 5. Zasady prywatnosci i bezpieczenstwa

To jest bardzo wazna czesc projektu.

- Aplikacja nie sluzy do stawiania diagnozy medycznej.
- Aplikacja nie pokazuje innemu uzytkownikowi szczegolowych danych zdrowotnych konkretnej osoby.
- Nie ma widoku "Ty vs Anna", "Ty vs Kuba" itp.
- W grupach pokazywane sa tylko dane zagregowane, np. sredni czas snu grupy.
- Dane grupowe pojawiaja sie dopiero po spelnieniu warunku minimalnej liczby dni analizy, np. 30 dni.
- Dane grupowe powinny byc dostepne tylko wtedy, gdy grupa ma minimalna liczbe aktywnych uczestnikow, np. co najmniej 10 osob.

## 6. Podzial grup

Kazdy uzytkownik przy konfiguracji profilu wybiera:

- przedzial wieku, np. 18-25, 26-35, 36-50, 51+,
- styl zycia, np. student, pracownik biurowy, pracownik zmianowy, aktywny sportowo.

Na tej podstawie system przypisuje uzytkownika do odpowiednich grup porownawczych lub pozwala filtrowac porownania po takich segmentach.

Przyklad:

- uzytkownik widzi, ze jego sredni czas snu z ostatnich 30 dni wynosi 6h 40m,
- system pokazuje, ze srednia dla grupy "26-35, pracownik biurowy" wynosi 7h 05m,
- system nie pokazuje, kto dokladnie tworzy te wyniki.

## 7. Nowe wymagania funkcjonalne

### FR-01 Rejestracja i logowanie

- Rejestracja przez e-mail i haslo.
- Logowanie i wylogowanie.
- Po zalogowaniu uzytkownik trafia na Dashboard.

### FR-02 Profil uzytkownika

- Uzytkownik uzupelnia podstawowe informacje profilu:
- nick,
- rok urodzenia albo przedzial wieku,
- styl zycia,
- opcjonalnie cele snu, np. 8 godzin snu.

### FR-03 Import danych z Mi Band

- Uzytkownik importuje dane z pliku CSV lub JSON.
- System waliduje format pliku.
- System zapisuje rekordy snu i unika duplikatow.
- System zapisuje historie importow.

### FR-04 Historia nocy

- System pokazuje liste nocy.
- Uzytkownik moze filtrowac po zakresie dat.
- Kazda noc zawiera podstawowe metryki:
- czas snu,
- srednie tetno nocne,
- minimalne SpO2,
- poziom ruchu lub aktywnosci nocnej.

### FR-05 Szczegoly nocy

- System pokazuje szczegoly wybranej nocy.
- Uzytkownik moze oznaczyc noc jako dobra, neutralna lub slaba.
- Uzytkownik moze dodac notatke.

### FR-06 Notatki i czynniki dnia

- Uzytkownik moze zapisac:
- kofeine po 16:00,
- alkohol,
- trening,
- poziom stresu,
- godzine zasniecia,
- subiektywna jakosc snu,
- dodatkowy opis.

### FR-07 Analiza samego siebie

To najwazniejszy modul aplikacji.

- System pokazuje trendy 7, 30 i 90 dni.
- System porownuje obecny okres do poprzedniego okresu tego samego uzytkownika.
- System pokazuje zmiany, np.:
- sredni czas snu wzrosl o 25 minut,
- srednie tetno nocne spadlo o 3 bpm,
- liczba zlych nocy spadla z 6 do 2.

### FR-08 Wnioski po 30 dniach

- Jezeli uzytkownik ma co najmniej 30 dni danych, system generuje podsumowanie miesieczne.
- Podsumowanie pokazuje:
- najlepsze i najslabsze tygodnie,
- powtarzajace sie wzorce,
- zaleznosci miedzy notatkami a snem,
- zmiany wzgledem poprzedniego miesiaca.

### FR-09 Grupy porownawcze

- Nie ma znajomych.
- Uzytkownik nalezy do grup porownawczych zdefiniowanych przez segmenty wieku i stylu zycia.
- System pokazuje porownanie do sredniej grupy lub percentyla, ale bez pokazywania pojedynczych osob.

### FR-10 Ograniczone porownania grupowe

- Porownania grupowe sa dostepne dopiero po zebraniu co najmniej 30 dni danych.
- Porownania dotycza tylko ogolnych metryk, np.:
- sredni czas snu,
- regularnosc godzin snu,
- liczba nocy krotszych niz 6 godzin,
- srednia subiektywna jakosc snu.
- Nie pokazujemy porownan szczegolowych parametrow medycznych jednej osoby do drugiej osoby.

### FR-11 Eksport danych

- Uzytkownik moze wyeksportowac swoje dane do CSV.
- Uzytkownik moze pobrac PDF z raportem miesiecznym.

## 8. Funkcje, ktore nalezy usunac z pierwotnej wersji

Te elementy z pierwotnego dokumentu trzeba usunac albo zmienic:

- modul znajomych,
- dolaczanie do grup typu "znajomi/projekt" jako glowna funkcja spolecznosciowa,
- ranking konkretnych uzytkownikow po nickach,
- ekran "Ty vs wybrany uzytkownik",
- porownywanie wrazliwych danych medycznych z konkretna osoba.

## 9. MVP do zrobienia w Django

Najlepsza wersja na start to MVP, czyli najprostsza sensowna wersja.

### Zakres MVP

- rejestracja, logowanie, wylogowanie,
- profil uzytkownika z wiekiem i stylem zycia,
- import danych z pliku,
- lista nocy,
- szczegoly nocy,
- notatki do nocy,
- dashboard z analiza 7/30 dni,
- porownanie "ten miesiac vs poprzedni miesiac",
- prosty modul grup porownawczych oparty o srednie zagregowane,
- eksport CSV.

### Po MVP

- PDF z raportem,
- wykresy,
- automatyczne wnioski i rekomendacje,
- bardziej zaawansowane segmenty grup,
- panel administratora,
- API do synchronizacji zamiast importu plikow.

## 10. Proponowana architektura Django

### Aplikacje w projekcie

- `users` - konta, profil, segment wieku i styl zycia,
- `sleep` - dane nocy, import, historia importow,
- `notes` - notatki i czynniki wplywu,
- `analytics` - trendy, porownania okresow, podsumowania miesieczne,
- `groups` - grupy porownawcze i zagregowane statystyki,
- `reports` - eksport CSV i PDF.

### Proponowane modele danych

#### User

Mozna uzyc wbudowanego modelu Django `AbstractUser` lub osobnego profilu.

#### UserProfile

- `user`
- `display_name`
- `birth_year` albo `age_group`
- `lifestyle_type`
- `sleep_goal_minutes`
- `created_at`

#### SleepRecord

- `user`
- `source`
- `sleep_date`
- `sleep_duration_minutes`
- `avg_heart_rate`
- `min_heart_rate`
- `max_heart_rate`
- `min_spo2`
- `movement_level`
- `raw_payload`
- `created_at`

#### ImportHistory

- `user`
- `source`
- `file_name`
- `imported_at`
- `added_count`
- `duplicate_count`
- `error_count`

#### SleepNote

- `user`
- `sleep_record`
- `caffeine_after_16`
- `alcohol`
- `training_level`
- `stress_level`
- `subjective_sleep_quality`
- `note_text`

#### ComparisonGroup

- `age_group`
- `lifestyle_type`
- `is_active`

#### GroupAggregate

- `group`
- `period_start`
- `period_end`
- `avg_sleep_duration`
- `avg_sleep_regularity`
- `avg_subjective_quality`
- `members_count`

## 11. Dashboard - co powinien pokazywac

Dashboard po zalogowaniu powinien pokazac:

- podsumowanie ostatniej nocy,
- sredni czas snu z 7 dni,
- sredni czas snu z 30 dni,
- zmiane wzgledem poprzedniego okresu,
- liczbe zlych nocy,
- szybki wglad w czynniki, ktore czesto towarzysza slabszemu snowi,
- sekcje "Twoj postep po 30 dniach",
- sekcje "Porownanie do podobnej grupy", jesli warunki sa spelnione.

## 12. Najwazniejsza logika biznesowa

To warto jasno zapisac w projekcie:

1. Uzytkownik widzi przede wszystkim swoje dane i swoje trendy.
2. System porownuje obecne wyniki glownie do wczesniejszych wynikow tego samego uzytkownika.
3. Porownania grupowe sa dodatkiem, a nie glowna funkcja.
4. Porownania grupowe sa anonimowe i zagregowane.
5. Porownania grupowe sa dostepne dopiero po odpowiednim czasie analizy, np. 30 dniach.

## 13. Przykladowe scenariusze uzycia

### Scenariusz 1

- Uzytkownik zaklada konto.
- Uzupelnia profil: wiek i styl zycia.
- Importuje dane z Mi Band.
- Widzi liste nocy i trendy z ostatnich 7 dni.

### Scenariusz 2

- Uzytkownik po kazdej nocy dodaje notatke o stresie, treningu i kofeinie.
- Po 30 dniach system pokazuje, ze po ciezkim treningu i wysokim stresie sredni czas snu jest krotszy.

### Scenariusz 3

- Po miesiacu system pokazuje:
- Twoj sredni czas snu wzrosl z 6h 20m do 6h 50m,
- liczba slabych nocy spadla,
- w grupie "18-25, student" srednia wynosi 7h 00m.

## 14. Scenariusze testowe do projektu

- Rejestracja -> logowanie -> wejscie na dashboard.
- Uzupelnienie profilu -> zapis wieku i stylu zycia.
- Import poprawnego pliku -> zapis danych -> wyswietlenie nocy.
- Import tego samego pliku drugi raz -> wykrycie duplikatow.
- Wejscie w szczegoly nocy -> dodanie notatki -> widocznosc notatki po odswiezeniu.
- Zmiana zakresu dat -> przeliczenie trendow 7/30/90 dni.
- Po uzyskaniu 30 dni danych -> pokazanie podsumowania miesiecznego.
- Przy zbyt malej liczbie danych -> brak dostepu do porownania grupowego.
- Eksport CSV -> pobranie pliku z wybranego zakresu.

## 15. Rekomendacja techniczna

Do wykonania tej aplikacji w Django polecam:

- Django
- Django ORM
- SQLite na start, potem PostgreSQL
- Django templates albo frontend w Bootstrap na MVP
- `pandas` do importu i analizy CSV
- `matplotlib` albo `chart.js` do wykresow
- `django-allauth` jezeli chcesz szybciej zrobic logowanie
- `WeasyPrint` albo `ReportLab` do PDF

## 16. Najlepszy opis projektu w jednym zdaniu

SleepWatch to aplikacja webowa w Django do analizy snu z danych Mi Band, nastawiona glownie na porownywanie uzytkownika z jego wlasnymi wynikami w czasie oraz na anonimowe, zagregowane porownania do grup o podobnym wieku i stylu zycia po co najmniej 30 dniach analizy.
