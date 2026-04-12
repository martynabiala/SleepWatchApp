# SleepWatch Sleep Sync API

Dokument opisuje backendowy endpoint przygotowany pod synchronizacje mobilna.

## Endpoint

`POST /api/sleep/sync/`

## Autoryzacja

Naglowek:

`Authorization: Bearer <TOKEN_API>`

Token jest generowany w profilu uzytkownika w aplikacji SleepWatch.

## Obslugiwani providerzy

- `health_connect`
- `zepp_sync`
- `zepp_life`

## Przykladowy request

```json
{
  "provider": "health_connect",
  "device_name": "Pixel 8",
  "records": [
    {
      "external_id": "hc-001",
      "sleep_date": "2026-04-10",
      "bedtime": "23:20:00",
      "wake_time": "07:05:00",
      "sleep_duration_minutes": 465,
      "awakenings_count": 2,
      "awake_minutes": 18,
      "light_sleep_minutes": 230,
      "deep_sleep_minutes": 130,
      "rem_minutes": 100,
      "avg_heart_rate": 57,
      "min_spo2": 95,
      "raw_data": {
        "source": "Health Connect"
      }
    }
  ]
}
```

## Przykladowy response

```json
{
  "status": "ok",
  "provider": "health_connect",
  "received_count": 1,
  "added_count": 1,
  "updated_count": 0,
  "last_synced_at": "2026-04-11T22:00:00+02:00"
}
```

## Zasady zapisu

- jesli rekord ma `external_id`, backend probuje zaktualizowac istniejacy rekord tego samego provideru,
- jesli nie ma `external_id`, backend szuka rekordu po `sleep_date` i zrodle,
- po udanym zapisie aktualizowany jest status polaczenia synchronizacji,
- profil i dashboard pokazuja ostatnia synchronizacje, liczbe rekordow i urzadzenie.

## Wazna uwaga

Na `MariaDB` warunkowy `UniqueConstraint` dla `external_record_id` nie jest w pelni wspierany, wiec dodatkowa ostroznosc po stronie klienta nadal jest dobrym pomyslem.
