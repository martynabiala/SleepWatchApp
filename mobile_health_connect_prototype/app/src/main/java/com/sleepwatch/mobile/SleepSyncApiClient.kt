package com.sleepwatch.mobile

import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL

class SleepSyncApiClient(
    private val baseUrl: String,
    private val apiToken: String,
) {

    fun syncSleepRecords(records: List<SleepRecordPayload>): SyncResult {
        try {
            val url = URL(baseUrl.trimEnd('/') + "/api/sleep/sync/")
            val connection = (url.openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                doOutput = true
                setRequestProperty("Content-Type", "application/json")
                setRequestProperty("Authorization", "Bearer $apiToken")
                connectTimeout = 15000
                readTimeout = 15000
            }

            val payload = JSONObject().apply {
                put("provider", "health_connect")
                put("device_name", "Android Health Connect")
                put("records", JSONArray(records.map { it.toJson() }))
            }

            OutputStreamWriter(connection.outputStream).use { writer ->
                writer.write(payload.toString())
            }

            val responseBody = runCatching {
                BufferedReader(connection.inputStream.reader()).use { it.readText() }
            }.getOrElse {
                BufferedReader(connection.errorStream?.reader() ?: "".reader()).use { reader -> reader.readText() }
            }

            if (connection.responseCode !in 200..299) {
                error("HTTP ${connection.responseCode}: $responseBody")
            }

            val json = JSONObject(responseBody)
            return SyncResult(
                receivedCount = json.optInt("received_count"),
                addedCount = json.optInt("added_count"),
                updatedCount = json.optInt("updated_count"),
            )
        } catch (error: Exception) {
            val detail = error.message ?: error.javaClass.simpleName
            throw IllegalStateException("Nie mozna polaczyc z backendem: $detail", error)
        }
    }
}
