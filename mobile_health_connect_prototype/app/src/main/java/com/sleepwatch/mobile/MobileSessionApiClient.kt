package com.sleepwatch.mobile

import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import javax.net.ssl.SSLHandshakeException

data class MobileLoginResult(
    val token: String,
    val displayName: String,
    val username: String,
    val preferredSyncSource: String,
)

data class MobileSummaryResult(
    val displayName: String,
    val username: String,
    val preferredSyncSource: String,
    val sleepGoalHours: Int,
    val lastSleepDate: String?,
    val lastSleepDuration: String?,
    val connectionCount: Int,
)

data class MobileSignupResult(
    val flow: String,
    val message: String,
)

class MobileSessionApiClient(
    private val baseUrl: String,
) {
    fun login(login: String, password: String): MobileLoginResult {
        val response = request(
            path = "/api/mobile/login/",
            method = "POST",
            body = JSONObject().apply {
                put("login", login)
                put("password", password)
            }.toString(),
        )
        val json = JSONObject(response)
        val user = json.getJSONObject("user")
        return MobileLoginResult(
            token = json.getString("token"),
            displayName = user.getString("display_name"),
            username = user.getString("username"),
            preferredSyncSource = user.getString("preferred_sync_source"),
        )
    }

    fun fetchSummary(apiToken: String): MobileSummaryResult {
        val response = request(
            path = "/api/mobile/summary/",
            method = "GET",
            apiToken = apiToken,
        )
        val json = JSONObject(response)
        val user = json.getJSONObject("user")
        val lastSleep = json.optJSONObject("last_sleep")
        val connections = json.optJSONArray("sync_connections") ?: JSONArray()
        return MobileSummaryResult(
            displayName = user.getString("display_name"),
            username = user.getString("username"),
            preferredSyncSource = json.getString("preferred_sync_source"),
            sleepGoalHours = json.getInt("sleep_goal_hours"),
            lastSleepDate = lastSleep?.optString("date")?.takeIf { it.isNotBlank() },
            lastSleepDuration = lastSleep?.optString("duration_display")?.takeIf { it.isNotBlank() },
            connectionCount = connections.length(),
        )
    }

    fun signup(
        email: String,
        ageGroup: String,
        parentEmail: String,
        password1: String,
        password2: String,
    ): MobileSignupResult {
        val response = request(
            path = "/api/mobile/signup/",
            method = "POST",
            body = JSONObject().apply {
                put("email", email)
                put("age_group", ageGroup)
                put("parent_email", parentEmail)
                put("password1", password1)
                put("password2", password2)
            }.toString(),
        )
        val json = JSONObject(response)
        return MobileSignupResult(
            flow = json.getString("flow"),
            message = json.getString("message"),
        )
    }

    fun updatePreferredSource(apiToken: String, preferredSyncSource: String) {
        request(
            path = "/api/mobile/preferences/",
            method = "POST",
            apiToken = apiToken,
            body = JSONObject().apply {
                put("preferred_sync_source", preferredSyncSource)
            }.toString(),
        )
    }

    fun fetchSleepHistory(apiToken: String): List<MobileSleepHistoryItem> {
        val response = request(
            path = "/api/mobile/sleep-history/",
            method = "GET",
            apiToken = apiToken,
        )
        val json = JSONObject(response)
        val records = json.optJSONArray("records") ?: JSONArray()
        return List(records.length()) { index ->
            val item = records.getJSONObject(index)
            MobileSleepHistoryItem(
                id = item.getInt("id"),
                sleepDate = item.getString("sleep_date"),
                durationDisplay = item.getString("duration_display"),
                bedtime = item.optString("bedtime"),
                wakeTime = item.optString("wake_time"),
                awakeningsCount = item.optInt("awakenings_count").takeIf { !item.isNull("awakenings_count") },
                source = item.getString("source"),
            )
        }
    }

    fun createManualSleep(
        apiToken: String,
        sleepDate: String,
        bedtime: String,
        wakeTime: String,
        awakeningsCount: Int?,
    ): MobileManualSleepResult {
        val response = request(
            path = "/api/mobile/manual-sleep/",
            method = "POST",
            apiToken = apiToken,
            body = JSONObject().apply {
                put("sleep_date", sleepDate)
                put("bedtime", bedtime)
                put("wake_time", wakeTime)
                if (awakeningsCount != null) {
                    put("awakenings_count", awakeningsCount)
                }
            }.toString(),
        )
        val json = JSONObject(response).getJSONObject("record")
        return MobileManualSleepResult(
            id = json.getInt("id"),
            sleepDate = json.getString("sleep_date"),
            durationDisplay = json.getString("duration_display"),
            bedtime = json.optString("bedtime"),
            wakeTime = json.optString("wake_time"),
            awakeningsCount = json.optInt("awakenings_count").takeIf { !json.isNull("awakenings_count") },
        )
    }

    private fun request(
        path: String,
        method: String,
        body: String? = null,
        apiToken: String? = null,
    ): String {
        try {
            val url = URL(normalizeBaseUrl(baseUrl) + path)
            val connection = (url.openConnection() as HttpURLConnection).apply {
                requestMethod = method
                doInput = true
                connectTimeout = 15000
                readTimeout = 15000
                setRequestProperty("Content-Type", "application/json")
                if (!apiToken.isNullOrBlank()) {
                    setRequestProperty("Authorization", "Bearer $apiToken")
                }
                if (body != null) {
                    doOutput = true
                }
            }

            if (body != null) {
                OutputStreamWriter(connection.outputStream).use { writer ->
                    writer.write(body)
                }
            }

            val responseBody = runCatching {
                BufferedReader(connection.inputStream.reader()).use { it.readText() }
            }.getOrElse {
                BufferedReader(connection.errorStream?.reader() ?: "".reader()).use { it.readText() }
            }

            if (connection.responseCode !in 200..299) {
                error("HTTP ${connection.responseCode}: $responseBody")
            }
            return responseBody
        } catch (error: Exception) {
            val detail = if (error is SSLHandshakeException || error.cause is SSLHandshakeException) {
                "blad bezpiecznego polaczenia HTTPS. Sprawdz, czy w Backend URL jest https://sleepwatch.onrender.com, czy telefon ma poprawna date i czy strona otwiera sie w przegladarce telefonu."
            } else {
                error.message ?: error.javaClass.simpleName
            }
            throw IllegalStateException("Nie mozna polaczyc z kontem: $detail", error)
        }
    }

    private fun normalizeBaseUrl(rawBaseUrl: String): String {
        return rawBaseUrl.trim()
            .removeSuffix("/")
            .removeSuffix("/dashboard")
            .removeSuffix("/dashboard/")
    }
}
