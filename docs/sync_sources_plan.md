# Plan Integracji Zrodel Danych Snu

## Kierunek projektu

SleepWatch powinien dawac uzytkownikowi wybor zrodla danych, zamiast opierac sie tylko na jednym ekosystemie.

## Zrodla

### 1. Health Connect

- rola: glowna integracja automatyczna dla Androida
- dla kogo: osoby korzystajace z aplikacji i urzadzen zapisujacych sen do Health Connect
- plusy:
  - jedna nowoczesna sciezka dla wielu zgodnych aplikacji
  - mobilny prototyp synchronizacji jest juz przygotowany
  - architektura backendu jest gotowa
- ograniczenia:
  - dziala tylko wtedy, gdy inne aplikacje rzeczywiscie zapisza dane do Health Connect

### 2. Zepp Life

- rola: oddzielna sciezka dla opasek Amazfit / Mi Band
- dla kogo: uzytkownicy, ktorzy nie moga przekazac danych do Health Connect
- plusy:
  - odpowiada realnemu przypadkowi uzytkownika projektu
  - pozwala obsluzyc obecna opaske bez wymiany ekosystemu
- ograniczenia:
  - wymaga osobnej integracji lub importu
  - nie nalezy obiecywac pelnego realtime na pierwszym etapie

## Rekomendowana decyzja

1. Pokazujemy uzytkownikowi wybor zrodla:
   - Health Connect
   - Zepp Life
2. Health Connect traktujemy jako wariant rekomendowany i najbardziej automatyczny.
3. Zepp Life traktujemy jako osobna sciezke kompatybilnosci dla aktualnej opaski.
4. W UI pokazujemy status, ograniczenia i nastepny krok dla kazdego zrodla.

## Etapy wdrozenia

### Etap 1

- dzialajacy backend synchronizacji
- prototyp Android + Health Connect
- status integracji w profilu i dashboardzie

### Etap 2

- osobny ekran lub sekcja wyboru zrodla
- jasna informacja, czy dane ida przez Health Connect czy przez Zepp Life
- oddzielne komunikaty dla pustych danych i bledow synchronizacji

### Etap 3

- Zepp Life jako polautomatyczny import lub mostek
- ewentualna dedykowana synchronizacja, jesli uda sie zbudowac bezpieczna sciezke pobierania danych

## Jak to komunikowac

Najuczciwiej:

"SleepWatch wspiera dwa kierunki integracji danych snu. Health Connect jest glowna, automatyczna sciezka dla zgodnych aplikacji Android. Dla uzytkownikow opasek dzialajacych przez Zepp Life przewidziana jest oddzielna sciezka importu lub przyszlej synchronizacji."
