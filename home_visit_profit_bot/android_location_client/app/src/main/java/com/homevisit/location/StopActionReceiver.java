package com.homevisit.location;

import android.app.NotificationManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

/**
 * Обрабатывает кнопки push-уведомления о длительной остановке:
 * «Закрыть по GPS» (complete) и типы остановки (stop-label). Сервер/ключ берём из
 * тех же SharedPreferences, что и сервис загрузки локаций; запрос выполняем в
 * фоне через goAsync(). После действия гасим уведомление.
 */
public class StopActionReceiver extends BroadcastReceiver {

    static final String EXTRA_VISIT_ID = "visit_id";
    static final String EXTRA_KIND = "kind";   // "complete" | "label"
    static final String EXTRA_LABEL = "label"; // apiValue типа остановки

    @Override
    public void onReceive(Context context, Intent intent) {
        final int visitId = intent.getIntExtra(EXTRA_VISIT_ID, -1);
        final String kind = intent.getStringExtra(EXTRA_KIND);
        final String label = intent.getStringExtra(EXTRA_LABEL);

        NotificationManager manager = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager != null) {
            manager.cancel(LocationUploadService.ALERT_NOTIFICATION_ID);
        }
        if (visitId <= 0 || kind == null) {
            return;
        }

        SharedPreferences prefs = context.getSharedPreferences(MainActivity.PREFS, Context.MODE_PRIVATE);
        final String base = apiBase(prefs.getString(MainActivity.KEY_SERVER_URL, ""));
        final String apiKey = prefs.getString(MainActivity.KEY_API_KEY, "");
        if (base.isEmpty() || apiKey.isEmpty()) {
            return;
        }

        final String endpoint = "complete".equals(kind)
                ? base + "/api/visits/" + visitId + "/complete"
                : base + "/api/visits/" + visitId + "/stop-label";
        final String body = "label".equals(kind)
                ? "{\"label\":\"" + (label == null ? "" : label) + "\"}"
                : "{}";

        final PendingResult pending = goAsync();
        new Thread(() -> {
            try {
                post(endpoint, apiKey, body);
            } catch (Exception ignored) {
                // Сеть могла быть недоступна — молча, пуш уже погашен.
            } finally {
                pending.finish();
            }
        }).start();
    }

    /**
     * База API из сохранённого адреса (как normalizeApiUrl в Kotlin): срезаем
     * суффиксы /location и /driving и завершающий слэш. Пути дальше идут через
     * "/api/...". Пример: "https://api.vizitorkrut.ru" → без изменений.
     */
    private static String apiBase(String value) {
        String base = value == null ? "" : value.trim();
        if (base.endsWith("/location")) {
            base = base.substring(0, base.length() - "/location".length());
        } else if (base.endsWith("/driving")) {
            base = base.substring(0, base.length() - "/driving".length());
        }
        while (base.endsWith("/")) {
            base = base.substring(0, base.length() - 1);
        }
        return base;
    }

    private static void post(String urlStr, String apiKey, String body) throws Exception {
        URL url = new URL(urlStr);
        HttpURLConnection connection = (HttpURLConnection) url.openConnection();
        try {
            connection.setRequestMethod("POST");
            connection.setConnectTimeout(10000);
            connection.setReadTimeout(10000);
            connection.setRequestProperty("Authorization", "Bearer " + apiKey);
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            connection.setDoOutput(true);
            try (OutputStream stream = connection.getOutputStream()) {
                stream.write(body.getBytes(StandardCharsets.UTF_8));
            }
            connection.getResponseCode();
        } finally {
            connection.disconnect();
        }
    }
}
