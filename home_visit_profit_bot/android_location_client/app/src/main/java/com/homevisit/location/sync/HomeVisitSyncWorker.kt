package com.homevisit.location.sync

import android.content.Context
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.homevisit.location.MainActivity
import com.homevisit.location.data.HomeVisitRepository
import java.util.concurrent.TimeUnit

class HomeVisitSyncWorker(
    appContext: Context,
    params: WorkerParameters,
) : CoroutineWorker(appContext, params) {
    override suspend fun doWork(): Result {
        val prefs = applicationContext.getSharedPreferences(MainActivity.PREFS, Context.MODE_PRIVATE)
        val serverUrl = prefs.getString(MainActivity.KEY_SERVER_URL, "").orEmpty()
        val apiKey = prefs.getString(MainActivity.KEY_API_KEY, "").orEmpty()
        if (serverUrl.isBlank() || apiKey.isBlank()) {
            return Result.success()
        }
        val sent = HomeVisitRepository.create(applicationContext).syncPending(serverUrl, apiKey)
        return if (sent >= 0) Result.success() else Result.retry()
    }
}

object SyncScheduler {
    private const val PERIODIC_WORK_NAME = "home_visit_periodic_sync"
    private const val ONE_TIME_WORK_NAME = "home_visit_sync_now"

    fun schedule(context: Context) {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()
        val request = PeriodicWorkRequestBuilder<HomeVisitSyncWorker>(15, TimeUnit.MINUTES)
            .setConstraints(constraints)
            .build()
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            PERIODIC_WORK_NAME,
            ExistingPeriodicWorkPolicy.KEEP,
            request,
        )
    }

    fun runOnce(context: Context) {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()
        val request = OneTimeWorkRequestBuilder<HomeVisitSyncWorker>()
            .setConstraints(constraints)
            .build()
        WorkManager.getInstance(context).enqueueUniqueWork(
            ONE_TIME_WORK_NAME,
            ExistingWorkPolicy.REPLACE,
            request,
        )
    }
}
