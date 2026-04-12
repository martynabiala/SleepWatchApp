package com.sleepwatch.mobile

import org.json.JSONObject

data class SleepRecordPayload(
    val externalId: String,
    val sleepDate: String,
    val bedtime: String,
    val wakeTime: String,
    val sleepDurationMinutes: Int,
    val awakeMinutes: Int,
    val lightSleepMinutes: Int,
    val deepSleepMinutes: Int,
    val remMinutes: Int,
    val rawSource: String,
) {
    fun toJson(): JSONObject {
        return JSONObject().apply {
            put("external_id", externalId)
            put("sleep_date", sleepDate)
            put("bedtime", bedtime)
            put("wake_time", wakeTime)
            put("sleep_duration_minutes", sleepDurationMinutes)
            put("awake_minutes", awakeMinutes)
            put("light_sleep_minutes", lightSleepMinutes)
            put("deep_sleep_minutes", deepSleepMinutes)
            put("rem_minutes", remMinutes)
            put("raw_data", JSONObject().put("source", rawSource))
        }
    }
}

data class SyncResult(
    val receivedCount: Int,
    val addedCount: Int,
    val updatedCount: Int,
)
