package com.sleepwatch.mobile

import android.content.Context
import android.os.Bundle
import android.view.View
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.health.connect.client.PermissionController
import androidx.lifecycle.lifecycleScope
import java.time.LocalDate
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : ComponentActivity() {

    private enum class AuthMode {
        LOGIN,
        SIGNUP,
    }

    private enum class AppSection {
        DASHBOARD,
        HISTORY,
        ADD,
        SYNC,
        ACCOUNT,
    }

    private lateinit var authContainer: LinearLayout
    private lateinit var appContainer: LinearLayout
    private lateinit var signupFieldsContainer: LinearLayout
    private lateinit var authSubtitleText: TextView
    private lateinit var summaryText: TextView
    private lateinit var dashboardHighlightText: TextView
    private lateinit var accountDetailsText: TextView
    private lateinit var statusText: TextView
    private lateinit var sourceHintText: TextView
    private lateinit var recentNightsText: TextView

    private lateinit var backendUrlInput: EditText
    private lateinit var loginInput: EditText
    private lateinit var passwordInput: EditText
    private lateinit var passwordRepeatInput: EditText
    private lateinit var parentEmailInput: EditText
    private lateinit var manualDateInput: EditText
    private lateinit var manualBedtimeInput: EditText
    private lateinit var manualWakeTimeInput: EditText
    private lateinit var manualAwakeningsInput: EditText
    private lateinit var apiTokenInput: TextView

    private lateinit var ageGroupSpinner: Spinner

    private lateinit var loginModeButton: Button
    private lateinit var signupModeButton: Button
    private lateinit var authActionButton: Button
    private lateinit var dashboardTabButton: Button
    private lateinit var historyTabButton: Button
    private lateinit var addTabButton: Button
    private lateinit var syncTabButton: Button
    private lateinit var accountTabButton: Button

    private lateinit var dashboardSection: LinearLayout
    private lateinit var historySection: LinearLayout
    private lateinit var addSection: LinearLayout
    private lateinit var syncSection: LinearLayout
    private lateinit var accountSection: LinearLayout

    private lateinit var healthConnectManager: SleepHealthConnectManager

    private var authMode: AuthMode = AuthMode.LOGIN
    private var currentSection: AppSection = AppSection.DASHBOARD

    private val preferences by lazy {
        getSharedPreferences("sleepwatch_mobile", Context.MODE_PRIVATE)
    }

    companion object {
        private const val KEY_BACKEND_URL = "backend_url"
        private const val KEY_API_TOKEN = "api_token"
        private const val KEY_LOGIN = "login"
        private const val SYNC_PROVIDER = "health_connect"
        private const val DEFAULT_BACKEND_URL = "https://sleepwatch.onrender.com"
    }

    private val ageGroupValues = listOf(
        "" to "Wybierz",
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
        dashboardHighlightText = findViewById(R.id.dashboardHighlightText)
        accountDetailsText = findViewById(R.id.accountDetailsText)
        statusText = findViewById(R.id.statusText)
        sourceHintText = findViewById(R.id.sourceHintText)
        recentNightsText = findViewById(R.id.recentNightsText)

        backendUrlInput = findViewById(R.id.backendUrlInput)
        loginInput = findViewById(R.id.loginInput)
        passwordInput = findViewById(R.id.passwordInput)
        passwordRepeatInput = findViewById(R.id.passwordRepeatInput)
        parentEmailInput = findViewById(R.id.parentEmailInput)
        manualDateInput = findViewById(R.id.manualDateInput)
        manualBedtimeInput = findViewById(R.id.manualBedtimeInput)
        manualWakeTimeInput = findViewById(R.id.manualWakeTimeInput)
        manualAwakeningsInput = findViewById(R.id.manualAwakeningsInput)
        apiTokenInput = findViewById(R.id.apiTokenInput)

        ageGroupSpinner = findViewById(R.id.ageGroupSpinner)

        loginModeButton = findViewById(R.id.loginModeButton)
        signupModeButton = findViewById(R.id.signupModeButton)
        authActionButton = findViewById(R.id.authActionButton)
        dashboardTabButton = findViewById(R.id.dashboardTabButton)
        historyTabButton = findViewById(R.id.historyTabButton)
        addTabButton = findViewById(R.id.addTabButton)
        syncTabButton = findViewById(R.id.syncTabButton)
        accountTabButton = findViewById(R.id.accountTabButton)

        dashboardSection = findViewById(R.id.dashboardSection)
        historySection = findViewById(R.id.historySection)
        addSection = findViewById(R.id.addSection)
        syncSection = findViewById(R.id.syncSection)
        accountSection = findViewById(R.id.accountSection)

        healthConnectManager = SleepHealthConnectManager(this)
        manualDateInput.setText(LocalDate.now().toString())
    }

    private fun setupAdapters() {
        val ageGroupAdapter = ArrayAdapter(
            this,
            R.layout.spinner_item_sleepwatch,
            ageGroupValues.map { it.second },
        )
        ageGroupAdapter.setDropDownViewResource(R.layout.spinner_dropdown_item_sleepwatch)
        ageGroupSpinner.adapter = ageGroupAdapter
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
        findViewById<Button>(R.id.checkAvailabilityButton).setOnClickListener {
            checkAvailability()
        }
        findViewById<Button>(R.id.requestPermissionsButton).setOnClickListener {
            requestHealthPermissions()
        }
        findViewById<Button>(R.id.syncButton).setOnClickListener {
            syncSleep()
        }
        findViewById<Button>(R.id.refreshHistoryButton).setOnClickListener {
            refreshHistoryIfPossible()
        }
        findViewById<Button>(R.id.addManualSleepButton).setOnClickListener {
            addManualSleep()
        }
        findViewById<Button>(R.id.dashboardSyncButton).setOnClickListener {
            showSection(AppSection.SYNC)
        }
        findViewById<Button>(R.id.dashboardHistoryButton).setOnClickListener {
            showSection(AppSection.HISTORY)
        }
        dashboardTabButton.setOnClickListener { showSection(AppSection.DASHBOARD) }
        historyTabButton.setOnClickListener { showSection(AppSection.HISTORY) }
        addTabButton.setOnClickListener { showSection(AppSection.ADD) }
        syncTabButton.setOnClickListener { showSection(AppSection.SYNC) }
        accountTabButton.setOnClickListener { showSection(AppSection.ACCOUNT) }
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
            showSection(currentSection)
            refreshSummaryIfPossible()
            refreshHistoryIfPossible()
        } else {
            summaryText.text = "Zaloguj sie, aby zobaczyc podsumowanie dnia."
            dashboardHighlightText.text = "Po zalogowaniu zobaczysz tu ostatnia noc, cel snu i szybka wskazowke."
            accountDetailsText.text = "Konto: niepolaczone"
            recentNightsText.text = "Po zalogowaniu zobaczysz tutaj ostatnie zapisane noce."
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
                preferences.edit().putString(KEY_API_TOKEN, result.token).apply()
                saveLocalConfiguration()
                passwordInput.setText("")
                summaryText.text = "Witaj, ${result.displayName}."
                dashboardHighlightText.text = "Za chwile pobieram Twoje podsumowanie dnia."
                accountDetailsText.text = "Konto: ${result.displayName} (@${result.username})"
                updateStatus("Zalogowano. Token zapisano automatycznie.")
                currentSection = AppSection.DASHBOARD
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
        if (ageGroup.isBlank()) {
            updateStatus("Wybierz grupe wiekowa.")
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
                        provider = SYNC_PROVIDER,
                        deviceName = "Android Health Connect",
                    )
                }
            }.onSuccess { result ->
                updateStatus(
                    "Synchronizacja zakonczona. Dodano ${result.addedCount}, zaktualizowano ${result.updatedCount}, odebrano ${result.receivedCount}.",
                )
                refreshSummaryIfPossible()
                refreshHistoryIfPossible()
            }.onFailure { error ->
                updateStatus("Blad synchronizacji: ${error.message}")
            }
        }
    }

    private fun addManualSleep() {
        val backendUrl = backendUrlInput.text.toString().trim()
        val apiToken = preferences.getString(KEY_API_TOKEN, "").orEmpty()
        val sleepDate = manualDateInput.text.toString().trim()
        val bedtime = manualBedtimeInput.text.toString().trim()
        val wakeTime = manualWakeTimeInput.text.toString().trim()
        val awakeningsCount = manualAwakeningsInput.text.toString().trim().toIntOrNull()

        if (backendUrl.isBlank() || apiToken.isBlank()) {
            updateStatus("Najpierw zaloguj sie do konta.")
            return
        }
        if (sleepDate.isBlank() || bedtime.isBlank() || wakeTime.isBlank()) {
            updateStatus("Uzupelnij date nocy, zasniecie i pobudke.")
            return
        }

        lifecycleScope.launch {
            runCatching {
                updateStatus("Zapisywanie nocy...")
                withContext(Dispatchers.IO) {
                    MobileSessionApiClient(backendUrl).createManualSleep(
                        apiToken = apiToken,
                        sleepDate = sleepDate,
                        bedtime = bedtime,
                        wakeTime = wakeTime,
                        awakeningsCount = awakeningsCount,
                    )
                }
            }.onSuccess { result ->
                updateStatus("Dodano noc ${result.sleepDate}. Czas snu: ${result.durationDisplay}.")
                manualAwakeningsInput.setText("")
                refreshSummaryIfPossible()
                refreshHistoryIfPossible()
            }.onFailure { error ->
                updateStatus("Blad zapisu nocy: ${error.message}")
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
        currentSection = AppSection.DASHBOARD
        refreshSessionUi()
        updateStatus("Wylogowano z aplikacji mobilnej.")
    }

    private fun updateStatus(message: String) {
        statusText.text = "Status: $message"
    }

    private fun showSection(section: AppSection) {
        currentSection = section
        dashboardSection.visibility = if (section == AppSection.DASHBOARD) View.VISIBLE else View.GONE
        historySection.visibility = if (section == AppSection.HISTORY) View.VISIBLE else View.GONE
        addSection.visibility = if (section == AppSection.ADD) View.VISIBLE else View.GONE
        syncSection.visibility = if (section == AppSection.SYNC) View.VISIBLE else View.GONE
        accountSection.visibility = if (section == AppSection.ACCOUNT) View.VISIBLE else View.GONE

        updateTabState(dashboardTabButton, section == AppSection.DASHBOARD)
        updateTabState(historyTabButton, section == AppSection.HISTORY)
        updateTabState(addTabButton, section == AppSection.ADD)
        updateTabState(syncTabButton, section == AppSection.SYNC)
        updateTabState(accountTabButton, section == AppSection.ACCOUNT)
    }

    private fun updateTabState(button: Button, selected: Boolean) {
        button.setBackgroundResource(
            if (selected) R.drawable.sleepwatch_button_primary else R.drawable.sleepwatch_button_secondary,
        )
        button.setTextColor(
            getColor(if (selected) android.R.color.white else R.color.sleepwatch_text),
        )
    }

    private fun updateSourceUi() {
        sourceHintText.text =
            "SleepWatch synchronizuje dane przez Health Connect. Jesli telefon lub polaczona aplikacja zapisuje tam sen, mozemy go pobrac do Twojego konta."
    }

    private fun saveLocalConfiguration() {
        preferences.edit()
            .putString(KEY_BACKEND_URL, backendUrlInput.text.toString().trim())
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
    }

    private fun refreshSummaryIfPossible() {
        val backendUrl = backendUrlInput.text.toString().trim()
        val apiToken = preferences.getString(KEY_API_TOKEN, "").orEmpty()
        if (backendUrl.isBlank() || apiToken.isBlank()) {
            summaryText.text = "Zaloguj sie, aby zobaczyc podsumowanie dnia."
            dashboardHighlightText.text = "Po zalogowaniu zobaczysz tu ostatnia noc, cel snu i szybka wskazowke."
            accountDetailsText.text = "Konto: niepolaczone"
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
                    "${summary.lastSleepDuration} (${summary.lastSleepDate})"
                } else {
                    "brak danych"
                }
                val dashboardText =
                    "Ostatnia noc\n$lastSleepText\n\n" +
                    "Cel snu\n${summary.sleepGoalHours} godzin"
                val dashboardHint = if (summary.lastSleepDuration != null) {
                    "Masz juz zapisana ostatnia noc. Mozesz przejsc do zakladki Noce albo uruchomic synchronizacje, jesli chcesz dograc nowsze dane."
                } else {
                    "Nie masz jeszcze zadnej nocy. Zacznij od synchronizacji z telefonu albo dodaj pierwsza noc recznie."
                }
                val accountText =
                    "Konto: ${summary.displayName} (@${summary.username})\n" +
                    "Preferowane zrodlo: $sourceLabel\n" +
                    "Cel snu: ${summary.sleepGoalHours} h\n" +
                    "Ostatnia noc: $lastSleepText\n" +
                    "Integracje: ${summary.connectionCount}"
                summaryText.text = dashboardText
                dashboardHighlightText.text = dashboardHint
                accountDetailsText.text = accountText
            }.onFailure {
                summaryText.text = "Nie udalo sie pobrac podsumowania dnia."
                dashboardHighlightText.text = "Sprobuj ponownie za chwile albo przejdz do synchronizacji."
                accountDetailsText.text = "Konto: polaczone, ale nie udalo sie pobrac podsumowania"
            }
        }
    }

    private fun refreshHistoryIfPossible() {
        val backendUrl = backendUrlInput.text.toString().trim()
        val apiToken = preferences.getString(KEY_API_TOKEN, "").orEmpty()
        if (backendUrl.isBlank() || apiToken.isBlank()) {
            recentNightsText.text = "Po zalogowaniu zobaczysz tutaj ostatnie zapisane noce."
            return
        }

        lifecycleScope.launch {
            runCatching {
                withContext(Dispatchers.IO) {
                    MobileSessionApiClient(backendUrl).fetchSleepHistory(apiToken)
                }
            }.onSuccess { records ->
                recentNightsText.text = if (records.isEmpty()) {
                    "Nie masz jeszcze zapisanych nocy. Mozesz zsynchronizowac sen z telefonu albo dodac pierwsza noc recznie."
                } else {
                    buildString {
                        append("Ostatnie zapisane noce:\n\n")
                        records.take(5).forEach { record ->
                            append("${record.sleepDate}  ${record.durationDisplay}")
                            if (record.bedtime.isNotBlank() && record.wakeTime.isNotBlank()) {
                                append("\n${record.bedtime} - ${record.wakeTime}")
                            }
                            record.awakeningsCount?.let {
                                append("  |  wybudzenia: $it")
                            }
                            append("\n\n")
                        }
                    }.trim()
                }
            }.onFailure {
                recentNightsText.text = "Nie udalo sie pobrac historii nocy."
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
