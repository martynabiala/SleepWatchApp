package com.sleepwatch.mobile

import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import javax.net.ssl.SSLHandshakeException

class SleepSyncApiClient(
    private val baseUrl: String,
    private val apiToken: String,
) {

    fun syncSleepRecords(
        records: List<SleepRecordPayload>,
        provider: String = "health_connect",
        deviceName: String = "Android Health Connect",
    ): SyncResult {
        try {
            val url = URL(normalizeBaseUrl(baseUrl) + "/api/sleep/sync/")
            val connection = (url.openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                doOutput = true
                setRequestProperty("Content-Type", "application/json")
                setRequestProperty("Authorization", "Bearer $apiToken")
                connectTimeout = 15000
                readTimeout = 15000
            }

            val payload = JSONObject().apply {
                put("provider", provider)
                put("device_name", deviceName)
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
            val detail = if (error is SSLHandshakeException || error.cause is SSLHandshakeException) {
                "blad bezpiecznego polaczenia HTTPS. Sprawdz, czy w Backend URL jest https://sleepwatch.onrender.com, czy telefon ma poprawna date i czy strona otwiera sie w przegladarce telefonu."
            } else {
                error.message ?: error.javaClass.simpleName
            }
            throw IllegalStateException("Nie mozna polaczyc z backendem: $detail", error)
        }
    }

    private fun normalizeBaseUrl(rawBaseUrl: String): String {
        return rawBaseUrl.trim()
            .removeSuffix("/")
            .removeSuffix("/dashboard")
            .removeSuffix("/dashboard/")
    }
}
