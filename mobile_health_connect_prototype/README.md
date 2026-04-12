# SleepWatch Mobile Health Connect Prototype

To jest starter aplikacji Android, ktora:

- prosi o dostep do `Health Connect`,
- odczytuje sesje snu z ostatnich 30 dni,
- wysyla je do backendu SleepWatch na endpoint `POST /api/sleep/sync/`.

Ten katalog jest prototypem startowym. Nie byl budowany w tym repo, ale zawiera komplet plikow potrzebnych do dalszego rozwoju w Android Studio.

## Co jest potrzebne

1. Android Studio.
2. Telefon lub emulator z Androidem.
3. Zainstalowane `Health Connect`.
4. Dzialajacy backend SleepWatch.
5. Token API wygenerowany w profilu uzytkownika w aplikacji webowej.

## Jak uruchomic

1. Otworz katalog `mobile_health_connect_prototype` w Android Studio.
2. Poczekaj na synchronizacje Gradle.
3. W pliku `app/src/main/java/com/sleepwatch/mobile/MainActivity.kt` ustaw:
   - adres backendu,
   - token API.
4. Uruchom aplikacje.
5. Kliknij `Sprawdz Health Connect`.
6. Kliknij `Nadaj uprawnienia`.
7. Kliknij `Synchronizuj sen`.

## Gdzie trafiaja dane

Aplikacja wysyla dane do:

`POST {BACKEND_URL}/api/sleep/sync/`

Naglowek autoryzacji:

`Authorization: Bearer <TOKEN_API>`

## Format danych

Payload jest zgodny z backendem SleepWatch:

```json
{
  "provider": "health_connect",
  "device_name": "Android Health Connect",
  "records": [
    {
      "external_id": "hc-2026-04-10T21:20:00Z",
      "sleep_date": "2026-04-10",
      "bedtime": "23:20:00",
      "wake_time": "07:05:00",
      "sleep_duration_minutes": 465,
      "awake_minutes": 18,
      "light_sleep_minutes": 230,
      "deep_sleep_minutes": 130,
      "rem_minutes": 100,
      "raw_data": {
        "source": "Health Connect"
      }
    }
  ]
}
```

## Ograniczenia prototypu

- Starter zaklada reczna konfiguracje URL i tokenu.
- Na razie nie zapisuje tokenu w bezpiecznym magazynie.
- Nie ma automatycznego harmonogramu synchronizacji.
- Zepp nie jest tu jeszcze obslugiwany bezposrednio. Najpierw spinamy `Health Connect`.

## Nastepne kroki

- dodac zapis tokenu i URL w `EncryptedSharedPreferences`,
- dodac automatyczna synchronizacje przez `WorkManager`,
- rozszerzyc mapowanie faz snu,
- sprawdzic, czy dane z Zepp trafiaja do `Health Connect`.
