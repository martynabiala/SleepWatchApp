package com.sleepwatch.mobile

import android.content.Context
import android.os.Bundle
import android.view.View
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.health.connect.client.PermissionController
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : ComponentActivity() {

    private enum class AuthMode {
        LOGIN,
        SIGNUP,
    }

    private enum class SyncSource(
        val label: String,
        val provider: String,
    ) {
        PHONE_SYNC("Synchronizacja z telefonu", "health_connect"),
    }

    private lateinit var authContainer: LinearLayout
    private lateinit var appContainer: LinearLayout
    private lateinit var signupFieldsContainer: LinearLayout
    private lateinit var authSubtitleText: TextView
    private lateinit var summaryText: TextView
    private lateinit var statusText: TextView
    private lateinit var sourceHintText: TextView

    private lateinit var backendUrlInput: EditText
    private lateinit var loginInput: EditText
    private lateinit var passwordInput: EditText
    private lateinit var passwordRepeatInput: EditText
    private lateinit var parentEmailInput: EditText
    private lateinit var apiTokenInput: TextView

    private lateinit var sourceSpinner: Spinner
    private lateinit var ageGroupSpinner: Spinner

    private lateinit var loginModeButton: Button
    private lateinit var signupModeButton: Button
    private lateinit var authActionButton: Button

    private lateinit var healthConnectManager: SleepHealthConnectManager

    private var authMode: AuthMode = AuthMode.LOGIN

    private val preferences by lazy {
        getSharedPreferences("sleepwatch_mobile", Context.MODE_PRIVATE)
    }

    companion object {
        private const val KEY_BACKEND_URL = "backend_url"
        private const val KEY_API_TOKEN = "api_token"
        private const val KEY_SYNC_SOURCE = "sync_source"
        private const val KEY_LOGIN = "login"
        private const val DEFAULT_BACKEND_URL = "https://sleepwatch.onrender.com"
    }

    private val ageGroupValues = listOf(
        "under_18" to "Ponizej 18 lat",
        "18-25" to "18-25 lat",
        "26-35" to "26-35 lat",
        "36-50" to "36-50 lat",
        "51+" to "51+ lat",
    )

    private val requestPermissions =
        registerForActivityResult(PermissionController.createRequestPermissionResultContract()) { granted ->
            if (granted.containsAll(healthConnectManager.permissions)) {
                updateStatus("Uprawnienia nadane. Mozesz uruchomic synchronizacje.")
            } else {
                updateStatus("Nie nadano wszystkich wymaganych uprawnien. Nadane: ${granted.joinToString()}")
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        bindViews()
        setupAdapters()
        restoreSavedConfiguration()
        setupListeners()
        updateAuthModeUi()
        refreshSessionUi()
    }

    private fun bindViews() {
        authContainer = findViewById(R.id.authContainer)
        appContainer = findViewById(R.id.appContainer)
        signupFieldsContainer = findViewById(R.id.signupFieldsContainer)
        authSubtitleText = findViewById(R.id.authSubtitleText)
        summaryText = findViewById(R.id.summaryText)
        statusText = findViewById(R.id.statusText)
        sourceHintText = findViewById(R.id.sourceHintText)

        backendUrlInput = findViewById(R.id.backendUrlInput)
        loginInput = findViewById(R.id.loginInput)
        passwordInput = findViewById(R.id.passwordInput)
        passwordRepeatInput = findViewById(R.id.passwordRepeatInput)
        parentEmailInput = findViewById(R.id.parentEmailInput)
        apiTokenInput = findViewById(R.id.apiTokenInput)

        sourceSpinner = findViewById(R.id.sourceSpinner)
        ageGroupSpinner = findViewById(R.id.ageGroupSpinner)

        loginModeButton = findViewById(R.id.loginModeButton)
        signupModeButton = findViewById(R.id.signupModeButton)
        authActionButton = findViewById(R.id.authActionButton)

        healthConnectManager = SleepHealthConnectManager(this)
    }

    private fun setupAdapters() {
        sourceSpinner.adapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_dropdown_item,
            SyncSource.entries.map { it.label },
        )
        ageGroupSpinner.adapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_dropdown_item,
            ageGroupValues.map { it.second },
        )
    }

    private fun setupListeners() {
        loginModeButton.setOnClickListener {
            authMode = AuthMode.LOGIN
            updateAuthModeUi()
        }
        signupModeButton.setOnClickListener {
            authMode = AuthMode.SIGNUP
            updateAuthModeUi()
        }
        authActionButton.setOnClickListener {
            if (authMode == AuthMode.LOGIN) {
                loginToAccount()
            } else {
                signupAccount()
            }
        }
        findViewById<Button>(R.id.logoutButton).setOnClickListener {
            logout()
        }
        findViewById<Button>(R.id.saveSourceButton).setOnClickListener {
            saveSourcePreference()
        }
        findViewById<Button>(R.id.checkAvailabilityButton).setOnClickListener {
            checkAvailability()
        }
        findViewById<Button>(R.id.requestPermissionsButton).setOnClickListener {
            requestHealthPermissions()
        }
        findViewById<Button>(R.id.syncButton).setOnClickListener {
            syncSleep()
        }
        sourceSpinner.onItemSelectedListener =
            object : AdapterView.OnItemSelectedListener {
                override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                    updateSourceUi()
                }

                override fun onNothingSelected(parent: AdapterView<*>?) = Unit
            }
    }

    private fun updateAuthModeUi() {
        val isSignup = authMode == AuthMode.SIGNUP
        signupFieldsContainer.visibility = if (isSignup) View.VISIBLE else View.GONE
        authSubtitleText.text = if (isSignup) {
            "Zaloz konto tak jak w wersji webowej. Po aktywacji wejdziesz do mobilnej wersji SleepWatch."
        } else {
            "Zaloguj sie, aby wejsc do mobilnej wersji SleepWatch."
        }
        authActionButton.text = if (isSignup) "Zarejestruj" else "Zaloguj"
        loginModeButton.setBackgroundResource(if (isSignup) R.drawable.sleepwatch_button_secondary else R.drawable.sleepwatch_button_primary)
        loginModeButton.setTextColor(getColor(if (isSignup) R.color.sleepwatch_text else android.R.color.white))
        signupModeButton.setBackgroundResource(if (isSignup) R.drawable.sleepwatch_button_primary else R.drawable.sleepwatch_button_secondary)
        signupModeButton.setTextColor(getColor(if (isSignup) android.R.color.white else R.color.sleepwatch_text))
    }

    private fun refreshSessionUi() {
        val hasToken = !preferences.getString(KEY_API_TOKEN, "").isNullOrBlank()
        authContainer.visibility = if (hasToken) View.GONE else View.VISIBLE
        appContainer.visibility = if (hasToken) View.VISIBLE else View.GONE
        updateSourceUi()
        if (hasToken) {
            refreshSummaryIfPossible()
        } else {
            summaryText.text = "Konto: niepolaczone"
        }
    }

    private fun loginToAccount() {
        val backendUrl = backendUrlInput.text.toString().trim()
        val loginValue = loginInput.text.toString().trim()
        val passwordValue = passwordInput.text.toString()

        if (backendUrl.isBlank() || loginValue.isBlank() || passwordValue.isBlank()) {
            updateStatus("Uzupelnij backend URL, login i haslo.")
            return
        }

        lifecycleScope.launch {
            runCatching {
                updateStatus("Logowanie do SleepWatch...")
                withContext(Dispatchers.IO) {
                    MobileSessionApiClient(backendUrl).login(loginValue, passwordValue)
                }
            }.onSuccess { result ->
                apiTokenInput.text = "Token API zapisany automatycznie po zalogowaniu."
                val selectedIndex = SyncSource.entries.indexOfFirst { it.provider == result.preferredSyncSource }
                if (selectedIndex >= 0) {
                    sourceSpinner.setSelection(selectedIndex)
                }
                preferences.edit().putString(KEY_API_TOKEN, result.token).apply()
                saveLocalConfiguration()
                passwordInput.setText("")
                summaryText.text = "Konto: ${result.displayName} (@${result.username})"
                updateStatus("Zalogowano. Token zapisano automatycznie.")
                refreshSessionUi()
            }.onFailure { error ->
                updateStatus("Blad logowania: ${error.message}")
            }
        }
    }

    private fun signupAccount() {
        val backendUrl = backendUrlInput.text.toString().trim()
        val email = loginInput.text.toString().trim()
        val password1 = passwordInput.text.toString()
        val password2 = passwordRepeatInput.text.toString()
        val parentEmail = parentEmailInput.text.toString().trim()
        val ageGroup = ageGroupValues[ageGroupSpinner.selectedItemPosition].first

        if (backendUrl.isBlank() || email.isBlank() || password1.isBlank() || password2.isBlank()) {
            updateStatus("Uzupelnij backend URL, e-mail i oba pola hasla.")
            return
        }

        lifecycleScope.launch {
            runCatching {
                updateStatus("Tworzenie konta...")
                withContext(Dispatchers.IO) {
                    MobileSessionApiClient(backendUrl).signup(
                        email = email,
                        ageGroup = ageGroup,
                        parentEmail = parentEmail,
                        password1 = password1,
                        password2 = password2,
                    )
                }
            }.onSuccess { result ->
                updateStatus(result.message)
                authMode = AuthMode.LOGIN
                updateAuthModeUi()
                if (result.flow == "adult") {
                    loginInput.setText(email)
                }
            }.onFailure { error ->
                updateStatus("Blad rejestracji: ${error.message}")
            }
        }
    }

    private fun saveSourcePreference() {
        val backendUrl = backendUrlInput.text.toString().trim()
        val apiToken = preferences.getString(KEY_API_TOKEN, "").orEmpty()
        val preferredSource = getSelectedSource().provider

        if (backendUrl.isBlank() || apiToken.isBlank()) {
            updateStatus("Najpierw zaloguj sie do konta.")
            return
        }

        lifecycleScope.launch {
            runCatching {
                withContext(Dispatchers.IO) {
                    MobileSessionApiClient(backendUrl).updatePreferredSource(apiToken, preferredSource)
                }
            }.onSuccess {
                saveLocalConfiguration()
                updateStatus("Zapisano preferowane zrodlo danych.")
                refreshSummaryIfPossible()
            }.onFailure { error ->
                updateStatus("Blad zapisu zrodla: ${error.message}")
            }
        }
    }

    private fun checkAvailability() {
        updateStatus(healthConnectManager.getAvailabilityMessage())
    }

    private fun requestHealthPermissions() {
        if (!healthConnectManager.isAvailable()) {
            updateStatus("Health Connect nie jest dostepny na tym urzadzeniu.")
            return
        }
        runCatching {
            requestPermissions.launch(healthConnectManager.permissions)
        }.onFailure { error ->
            updateStatus("Blad nadawania uprawnien: ${error.message}")
        }
    }

    private fun syncSleep() {
        val backendUrl = backendUrlInput.text.toString().trim()
        val apiToken = preferences.getString(KEY_API_TOKEN, "").orEmpty()
        if (backendUrl.isBlank() || apiToken.isBlank()) {
            updateStatus("Najpierw zaloguj sie do konta.")
            return
        }

        lifecycleScope.launch {
            runCatching {
                val selectedSource = getSelectedSource()
                updateStatus("Pobieranie danych snu z telefonu...")
                val sleepRecords = healthConnectManager.readLast30DaysSleep()
                if (sleepRecords.isEmpty()) {
                    updateStatus("Nie znaleziono danych snu z ostatnich 30 dni. Sprawdz, czy telefon lub polaczona aplikacja zapisuje sen w Health Connect.")
                    return@launch
                }
                updateStatus("Pobrano ${sleepRecords.size} rekordow. Wysylanie do SleepWatch...")
                withContext(Dispatchers.IO) {
                    SleepSyncApiClient(
                        baseUrl = backendUrl,
                        apiToken = apiToken,
                    ).syncSleepRecords(
                        records = sleepRecords,
                        provider = selectedSource.provider,
                        deviceName = "Android Health Connect",
                    )
                }
            }.onSuccess { result ->
                updateStatus(
                    "Synchronizacja zakonczona. Dodano ${result.addedCount}, zaktualizowano ${result.updatedCount}, odebrano ${result.receivedCount}.",
                )
                refreshSummaryIfPossible()
            }.onFailure { error ->
                updateStatus("Blad synchronizacji: ${error.message}")
            }
        }
    }

    private fun logout() {
        preferences.edit()
            .remove(KEY_API_TOKEN)
            .apply()
        apiTokenInput.text = "Zaloguj sie, aby aplikacja zapisala token automatycznie."
        passwordInput.setText("")
        passwordRepeatInput.setText("")
        authMode = AuthMode.LOGIN
        updateAuthModeUi()
        refreshSessionUi()
        updateStatus("Wylogowano z aplikacji mobilnej.")
    }

    private fun updateStatus(message: String) {
        statusText.text = "Status: $message"
    }

    private fun getSelectedSource(): SyncSource {
        return SyncSource.entries[sourceSpinner.selectedItemPosition]
    }

    private fun updateSourceUi() {
        sourceHintText.text =
            "To glowna automatyczna sciezka na Androidzie. SleepWatch odczytuje sen z Health Connect, wiec moze korzystac z danych udostepnianych przez rozne aplikacje zapisane w telefonie."
    }

    private fun saveLocalConfiguration() {
        preferences.edit()
            .putString(KEY_BACKEND_URL, backendUrlInput.text.toString().trim())
            .putString(KEY_SYNC_SOURCE, getSelectedSource().provider)
            .putString(KEY_LOGIN, loginInput.text.toString().trim())
            .apply()
    }

    private fun restoreSavedConfiguration() {
        backendUrlInput.setText(preferences.getString(KEY_BACKEND_URL, DEFAULT_BACKEND_URL))
        loginInput.setText(preferences.getString(KEY_LOGIN, ""))
        apiTokenInput.text = if (preferences.getString(KEY_API_TOKEN, "").isNullOrBlank()) {
            "Zaloguj sie, aby aplikacja zapisala token automatycznie."
        } else {
            "Token API zapisany automatycznie po zalogowaniu."
        }
        val savedSource = preferences.getString(KEY_SYNC_SOURCE, SyncSource.PHONE_SYNC.provider)
        val selectedIndex = SyncSource.entries.indexOfFirst { it.provider == savedSource }.coerceAtLeast(0)
        sourceSpinner.setSelection(selectedIndex)
    }

    private fun refreshSummaryIfPossible() {
        val backendUrl = backendUrlInput.text.toString().trim()
        val apiToken = preferences.getString(KEY_API_TOKEN, "").orEmpty()
        if (backendUrl.isBlank() || apiToken.isBlank()) {
            summaryText.text = "Konto: niepolaczone"
            return
        }

        lifecycleScope.launch {
            runCatching {
                withContext(Dispatchers.IO) {
                    MobileSessionApiClient(backendUrl).fetchSummary(apiToken)
                }
            }.onSuccess { summary ->
                val sourceLabel = getPreferredSourceLabel(summary.preferredSyncSource)
                val lastSleepText = if (summary.lastSleepDuration != null && summary.lastSleepDate != null) {
                    "Ostatnia noc: ${summary.lastSleepDuration} (${summary.lastSleepDate})"
                } else {
                    "Ostatnia noc: brak danych"
                }
                summaryText.text =
                    "Konto: ${summary.displayName} (@${summary.username})\n" +
                    "Preferowane zrodlo: $sourceLabel\n" +
                    "Cel snu: ${summary.sleepGoalHours} h\n" +
                    "$lastSleepText\n" +
                    "Integracje: ${summary.connectionCount}"
            }.onFailure {
                summaryText.text = "Konto: polaczone, ale nie udalo sie pobrac podsumowania"
            }
        }
    }

    private fun getPreferredSourceLabel(provider: String): String {
        return when (provider) {
            "health_connect" -> "Synchronizacja z telefonu"
            "manual_csv" -> "Import pliku CSV"
            else -> provider
        }
    }
}
