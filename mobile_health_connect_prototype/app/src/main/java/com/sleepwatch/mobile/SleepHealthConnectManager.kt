package com.sleepwatch.mobile

import android.content.Context
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.SleepSessionRecord
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
import java.time.Duration
import java.time.Instant
import java.time.ZoneId

class SleepHealthConnectManager(private val context: Context) {

    companion object {
        private const val PROVIDER_PACKAGE_NAME = "com.google.android.apps.healthdata"
    }

    val permissions = setOf(
        HealthPermission.getReadPermission(SleepSessionRecord::class),
    )

    private val client: HealthConnectClient?
        get() = if (getSdkStatus() == HealthConnectClient.SDK_AVAILABLE) {
            HealthConnectClient.getOrCreate(context)
        } else {
            null
        }

    fun isAvailable(): Boolean {
        return getSdkStatus() == HealthConnectClient.SDK_AVAILABLE
    }

    fun getAvailabilityMessage(): String {
        return when (getSdkStatus()) {
            HealthConnectClient.SDK_AVAILABLE -> "Health Connect jest dostepny."
            HealthConnectClient.SDK_UNAVAILABLE_PROVIDER_UPDATE_REQUIRED -> "Zaktualizuj lub zainstaluj Health Connect."
            else -> "Health Connect nie jest dostepny na tym urzadzeniu."
        }
    }

    private fun getSdkStatus(): Int {
        return HealthConnectClient.getSdkStatus(context, PROVIDER_PACKAGE_NAME)
    }

    suspend fun readLast30DaysSleep(): List<SleepRecordPayload> {
        val safeClient = client ?: error("Health Connect nie jest dostepny.")
        val end = Instant.now()
        val start = end.minus(Duration.ofDays(30))

        val response = safeClient.readRecords(
            ReadRecordsRequest(
                recordType = SleepSessionRecord::class,
                timeRangeFilter = TimeRangeFilter.between(start, end),
            ),
        )

        return response.records.map { record ->
            val zoneId = record.startZoneOffset?.let { ZoneId.ofOffset("UTC", it) } ?: ZoneId.systemDefault()
            val localDate = record.startTime.atZone(zoneId).toLocalDate()
            val durationMinutes = Duration.between(record.startTime, record.endTime).toMinutes().toInt()

            val stageTotals = record.stages.groupBy { it.stage }.mapValues { entry ->
                entry.value.sumOf { Duration.between(it.startTime, it.endTime).toMinutes().toInt() }
            }

            SleepRecordPayload(
                externalId = record.metadata.id,
                sleepDate = localDate.toString(),
                bedtime = record.startTime.atZone(zoneId).toLocalTime().toString(),
                wakeTime = record.endTime.atZone(zoneId).toLocalTime().toString(),
                sleepDurationMinutes = durationMinutes,
                awakeMinutes = stageTotals[SleepSessionRecord.STAGE_TYPE_AWAKE] ?: 0,
                lightSleepMinutes = stageTotals[SleepSessionRecord.STAGE_TYPE_LIGHT] ?: 0,
                deepSleepMinutes = stageTotals[SleepSessionRecord.STAGE_TYPE_DEEP] ?: 0,
                remMinutes = stageTotals[SleepSessionRecord.STAGE_TYPE_REM] ?: 0,
                rawSource = "Health Connect",
            )
        }
    }
}
