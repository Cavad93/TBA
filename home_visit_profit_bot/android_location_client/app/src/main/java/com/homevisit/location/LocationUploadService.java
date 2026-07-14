package com.homevisit.location;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.Build;
import android.os.Bundle;
import android.os.IBinder;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class LocationUploadService extends Service implements LocationListener, SensorEventListener {
    public static final String ACTION_START = "com.homevisit.location.START";
    public static final String ACTION_STOP = "com.homevisit.location.STOP";

    private static final int NOTIFICATION_ID = 7001;
    private static final String CHANNEL_ID = "location_upload";
    // Package-private: StopActionReceiver гасит это уведомление после действия.
    static final int ALERT_NOTIFICATION_ID = 7002;
    // Отдельный id: уведомление о парковке не должно затирать уведомление о том,
    // что пора закрыть заказ, — это разные вещи, и человеку нужны обе.
    static final int PARKING_NOTIFICATION_ID = 7003;
    static final String ALERT_CHANNEL_ID = "location_alerts";

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private LocationManager locationManager;
    private SensorManager sensorManager;
    private Sensor accelerometer;
    private Sensor gyroscope;
    private long lastSensorTimestampNs = 0L;
    private long lastPersistMs = 0L;
    private long lastHarshAccelMs = 0L;
    private long lastHardCornerMs = 0L;
    private long lastLaneChangeMs = 0L;
    private float lastLinearAccel = 0f;
    private float lastSpeedKmh = -1f;
    private long lastSpeedTimeMs = 0L;
    // Номер отрезка пути = сколько адресов уже закрыто. Присылает сервер.
    private int segmentIndex = 0;
    // Время в пути пешком — логистика. Манера ходьбы не измеряется: у неё нет
    // операционного смысла, кроме вывода о состоянии, а это спецкатегория ПДн.
    // Поэтому и частота датчика остаётся экономной — 50 Гц больше не нужны.
    private final WalkDetector walk = new WalkDetector();
    private int samplesCount = 0;
    private double sensorSeconds = 0;
    private int harshAccelerationCount = 0;
    private int harshBrakingCount = 0;
    private int hardCorneringCount = 0;
    private int laneChangeProxyCount = 0;
    private int stopGoCount = 0;
    private double jerkTotal = 0;
    private double speedDeltaTotal = 0;
    private int speedDeltaSamples = 0;

    @Override
    public void onCreate() {
        super.onCreate();
        locationManager = (LocationManager) getSystemService(Context.LOCATION_SERVICE);
        sensorManager = (SensorManager) getSystemService(Context.SENSOR_SERVICE);
        if (sensorManager != null) {
            accelerometer = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);
            gyroscope = sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE);
        }
        loadAggregate();
        createNotificationChannel();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent != null ? intent.getAction() : ACTION_START;
        if (ACTION_STOP.equals(action)) {
            stopSelf();
            return START_NOT_STICKY;
        }

        startForeground(NOTIFICATION_ID, notification("GPS отправляется на сервер"));
        startLocationUpdates();
        startSensorUpdates();
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        stopLocationUpdates();
        stopSensorUpdates();
        persistAggregate();
        executor.shutdownNow();
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private void startLocationUpdates() {
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            stopSelf();
            return;
        }
        SharedPreferences prefs = getSharedPreferences(MainActivity.PREFS, MODE_PRIVATE);
        long intervalMs = Math.max(60, prefs.getInt(MainActivity.KEY_INTERVAL_SECONDS, 60)) * 1000L;
        try {
            locationManager.requestLocationUpdates(LocationManager.GPS_PROVIDER, intervalMs, 15f, this);
        } catch (RuntimeException ignored) {
        }
        try {
            locationManager.requestLocationUpdates(LocationManager.NETWORK_PROVIDER, intervalMs, 25f, this);
        } catch (RuntimeException ignored) {
        }
    }

    private void stopLocationUpdates() {
        if (locationManager != null) {
            locationManager.removeUpdates(this);
        }
    }

    private void startSensorUpdates() {
        if (sensorManager == null) {
            return;
        }
        if (accelerometer != null) {
            sensorManager.registerListener(this, accelerometer, SensorManager.SENSOR_DELAY_NORMAL);
        }
        if (gyroscope != null) {
            sensorManager.registerListener(this, gyroscope, SensorManager.SENSOR_DELAY_NORMAL);
        }
    }

    private void stopSensorUpdates() {
        if (sensorManager != null) {
            sensorManager.unregisterListener(this);
        }
    }

    @Override
    public void onLocationChanged(Location location) {
        updateSpeedAggregate(location);
        sendLocation(location);
    }

    @Override
    public void onProviderEnabled(String provider) {
    }

    @Override
    public void onProviderDisabled(String provider) {
    }

    @Override
    public void onStatusChanged(String provider, int status, Bundle extras) {
    }

    @Override
    public void onSensorChanged(SensorEvent event) {
        resetDailyIfNeeded();
        long nowMs = System.currentTimeMillis();
        if (event.sensor.getType() == Sensor.TYPE_ACCELEROMETER) {
            float magnitude = (float) Math.sqrt(
                    event.values[0] * event.values[0]
                            + event.values[1] * event.values[1]
                            + event.values[2] * event.values[2]
            );
            float linear = Math.abs(magnitude - SensorManager.GRAVITY_EARTH);
            double dt = 0.02;
            if (lastSensorTimestampNs > 0 && event.timestamp > lastSensorTimestampNs) {
                dt = Math.min(1.0, Math.max(0.01, (event.timestamp - lastSensorTimestampNs) / 1_000_000_000.0));
            }
            lastSensorTimestampNs = event.timestamp;
            samplesCount += 1;
            sensorSeconds += dt;
            double jerk = Math.abs(linear - lastLinearAccel) / dt;
            jerkTotal += Math.min(50.0, jerk);
            lastLinearAccel = linear;
            if (linear >= 2.8f && nowMs - lastHarshAccelMs > 2500) {
                harshAccelerationCount += 1;
                lastHarshAccelMs = nowMs;
            }
            walk.onSample(linear, event.timestamp / 1_000_000_000.0, lastSpeedKmh < 0 ? 0 : lastSpeedKmh);
        } else if (event.sensor.getType() == Sensor.TYPE_GYROSCOPE) {
            float angular = (float) Math.sqrt(
                    event.values[0] * event.values[0]
                            + event.values[1] * event.values[1]
                            + event.values[2] * event.values[2]
            );
            if (angular >= 1.4f && nowMs - lastHardCornerMs > 2500) {
                hardCorneringCount += 1;
                lastHardCornerMs = nowMs;
            }
            if (Math.abs(event.values[2]) >= 0.8f && nowMs - lastLaneChangeMs > 1800) {
                laneChangeProxyCount += 1;
                lastLaneChangeMs = nowMs;
            }
        }
        if (nowMs - lastPersistMs > 10000) {
            persistAggregate();
            lastPersistMs = nowMs;
        }
    }

    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) {
    }

    private void sendLocation(Location location) {
        SharedPreferences prefs = getSharedPreferences(MainActivity.PREFS, MODE_PRIVATE);
        String serverUrl = normalizeLocationUrl(prefs.getString(MainActivity.KEY_SERVER_URL, ""));
        String apiKey = prefs.getString(MainActivity.KEY_API_KEY, "");
        if (serverUrl.isEmpty() || apiKey.isEmpty()) {
            return;
        }

        executor.submit(() -> {
            HttpURLConnection connection = null;
            try {
                JSONObject payload = new JSONObject();
                payload.put("lat", location.getLatitude());
                payload.put("lon", location.getLongitude());
                payload.put("accuracy_m", location.hasAccuracy() ? location.getAccuracy() : 0);
                payload.put("provider", location.getProvider());
                payload.put("timestamp_ms", location.getTime());

                byte[] body = payload.toString().getBytes(StandardCharsets.UTF_8);
                URL url = new URL(serverUrl);
                connection = (HttpURLConnection) url.openConnection();
                connection.setRequestMethod("POST");
                connection.setConnectTimeout(10000);
                connection.setReadTimeout(10000);
                connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                connection.setRequestProperty("Authorization", "Bearer " + apiKey);

                try (OutputStream outputStream = connection.getOutputStream()) {
                    outputStream.write(body);
                }
                int code = connection.getResponseCode();
                int serverSegment = segmentIndex;
                if (code >= 200 && code < 300) {
                    String responseText = readResponse(connection);
                    handleLocationResponse(responseText);
                    showParkingAlert(responseText);
                    serverSegment = readSegmentIndex(responseText, segmentIndex);
                }
                // Сначала досылаем то, что накопили на прошлом отрезке, и только потом
                // переключаемся: иначе телеметрия последнего куска дороги к адресу
                // потерялась бы вместе со счётчиками.
                sendDrivingAggregateSync(serverUrl, apiKey);
                if (serverSegment != segmentIndex) {
                    startSegment(serverSegment);
                }
            } catch (Exception ignored) {
            } finally {
                if (connection != null) {
                    connection.disconnect();
                }
            }
        });
    }

    private void updateSpeedAggregate(Location location) {
        resetDailyIfNeeded();
        if (!location.hasSpeed()) {
            return;
        }
        float speedKmh = location.getSpeed() * 3.6f;
        long timeMs = location.getTime() > 0 ? location.getTime() : System.currentTimeMillis();
        if (lastSpeedKmh >= 0 && lastSpeedTimeMs > 0 && timeMs > lastSpeedTimeMs) {
            double dt = (timeMs - lastSpeedTimeMs) / 1000.0;
            if (dt >= 1 && dt <= 180) {
                double deltaKmh = speedKmh - lastSpeedKmh;
                double accelMps2 = (speedKmh / 3.6 - lastSpeedKmh / 3.6) / dt;
                if (accelMps2 <= -2.2) {
                    harshBrakingCount += 1;
                }
                if ((lastSpeedKmh < 5 && speedKmh > 15) || (lastSpeedKmh > 15 && speedKmh < 5)) {
                    stopGoCount += 1;
                }
                speedDeltaTotal += Math.abs(deltaKmh);
                speedDeltaSamples += 1;
            }
        }
        lastSpeedKmh = speedKmh;
        lastSpeedTimeMs = timeMs;
    }

    /**
     * Телеметрия отправляется отрезком пути между адресами, а не одним итогом за сутки.
     * Дневной агрегат не различает «устал к вечеру» и «весь день ехал одинаково», а
     * именно это и есть самый ценный сигнал: стиль портится не равномерно, а после
     * какого-то адреса.
     *
     * Границу отрезка телефон сам не видит — заказ закрывается на сервере. Поэтому номер
     * текущего отрезка сервер присылает в ответе на /location, и мы отправляем накопленное
     * под тем номером, под которым его собирали.
     */
    private void sendDrivingAggregateSync(String locationUrl, String apiKey) {
        persistAggregate();
        HttpURLConnection connection = null;
        try {
            JSONObject payload = new JSONObject();
            payload.put("segment_index", segmentIndex);
            payload.put("samples_count", samplesCount);
            payload.put("sensor_minutes", sensorSeconds / 60.0);
            payload.put("harsh_acceleration_count", harshAccelerationCount);
            payload.put("harsh_braking_count", harshBrakingCount);
            payload.put("hard_cornering_count", hardCorneringCount);
            payload.put("lane_change_proxy_count", laneChangeProxyCount);
            payload.put("stop_go_count", stopGoCount);
            payload.put("jerk_score", calculateJerkScore());
            payload.put("speed_variability_score", calculateSpeedVariabilityScore());
            payload.put("aggressive_score", calculateAggressiveScore());

            // Время в пути пешком на отрезке — сколько занимает дорога от машины до
            // двери. Никаких характеристик самой походки: они бы описывали состояние
            // человека, а это специальная категория персональных данных.
            if (!walk.isEmpty()) {
                payload.put("walk_bouts", walk.bouts());
                payload.put("walk_seconds", walk.walkSeconds());
            }

            byte[] body = payload.toString().getBytes(StandardCharsets.UTF_8);
            URL url = new URL(normalizeDrivingUrl(locationUrl));
            connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("POST");
            connection.setConnectTimeout(10000);
            connection.setReadTimeout(10000);
            connection.setDoOutput(true);
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            connection.setRequestProperty("Authorization", "Bearer " + apiKey);
            try (OutputStream outputStream = connection.getOutputStream()) {
                outputStream.write(body);
            }
            connection.getResponseCode();
        } catch (Exception ignored) {
        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }

    private String readResponse(HttpURLConnection connection) {
        try (InputStream stream = connection.getInputStream();
             BufferedReader reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))) {
            StringBuilder builder = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                builder.append(line);
            }
            return builder.toString();
        } catch (Exception ignored) {
            return "";
        }
    }

    private int readSegmentIndex(String responseText, int fallback) {
        if (responseText == null || responseText.isEmpty()) {
            return fallback;
        }
        try {
            return new JSONObject(responseText).optInt("segment_index", fallback);
        } catch (Exception ignored) {
            return fallback;
        }
    }

    /**
     * «Вы встали в платной зоне».
     *
     * Решение принимает сервер: он знает и зоны, и часы оплаты, и что скорость упала
     * ниже 5 км/ч дольше пяти минут. Телефону остаётся показать. Так и правильно:
     * скорость, присланную телефоном, пришлось бы проверять, а карту зон — держать
     * в APK и обновлять с каждой сборкой.
     *
     * Оплату мы на себя не берём: платит человек в приложении своего города.
     */
    private void showParkingAlert(String responseText) {
        if (responseText == null || responseText.isEmpty()) {
            return;
        }
        JSONObject alert;
        try {
            alert = new JSONObject(responseText).optJSONObject("parking_alert");
        } catch (Exception ignored) {
            return;
        }
        if (alert == null) {
            return;
        }
        NotificationManager manager = getSystemService(NotificationManager.class);
        if (manager == null) {
            return;
        }

        Intent openIntent = new Intent(this, MainActivity.class);
        openIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent openPending = PendingIntent.getActivity(
                this, 0, openIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(this, ALERT_CHANNEL_ID)
                : new Notification.Builder(this);
        builder.setContentTitle(alert.optString("title", "Вы встали в платной зоне"))
                .setContentText(alert.optString("text", ""))
                .setStyle(new Notification.BigTextStyle().bigText(alert.optString("text", "")))
                .setSmallIcon(android.R.drawable.ic_menu_mylocation)
                .setAutoCancel(true)
                .setContentIntent(openPending);
        manager.notify(PARKING_NOTIFICATION_ID, builder.build());
    }

    /** Закрыт очередной адрес — начинаем новый отрезок пути с чистыми счётчиками. */
    private void startSegment(int index) {
        segmentIndex = index;
        walk.resetSegment();
        samplesCount = 0;
        sensorSeconds = 0;
        harshAccelerationCount = 0;
        harshBrakingCount = 0;
        hardCorneringCount = 0;
        laneChangeProxyCount = 0;
        stopGoCount = 0;
        jerkTotal = 0;
        speedDeltaTotal = 0;
        speedDeltaSamples = 0;
        lastLinearAccel = 0f;
        lastSpeedKmh = -1f;
        lastSpeedTimeMs = 0L;
        persistAggregate();
    }

    private void handleLocationResponse(String responseText) {
        if (responseText == null || responseText.isEmpty()) {
            return;
        }
        try {
            JSONObject response = new JSONObject(responseText);
            // ready_to_complete == should_notify на сервере: длительная стоянка у
            // незакрытого заказа (с cooldown). Показываем пуш с действиями.
            if (!response.optBoolean("ready_to_complete", false)) {
                return;
            }
            int visitId = response.optInt("visit_id", -1);
            double distance = response.optDouble("distance_m", 0);
            double dwell = response.optDouble("dwell_minutes", 0);
            showStopNotification(visitId, distance, dwell);
        } catch (Exception ignored) {
        }
    }

    private void showStopNotification(int visitId, double distance, double dwell) {
        NotificationManager manager = getSystemService(NotificationManager.class);
        if (manager == null) {
            return;
        }
        String title = dwell > 0
                ? String.format(Locale.US, "Долгая остановка · %.0f мин", dwell)
                : "Долгая остановка у адреса";
        String text = distance > 0
                ? String.format(Locale.US, "Вы рядом (%.0f м). Закрыть заказ или отметить остановку?", distance)
                : "Закрыть заказ или отметить тип остановки?";

        Intent openIntent = new Intent(this, MainActivity.class);
        openIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent openPending = PendingIntent.getActivity(
                this, 0, openIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(this, ALERT_CHANNEL_ID)
                : new Notification.Builder(this);
        builder.setContentTitle(title)
                .setContentText(text)
                .setSmallIcon(android.R.drawable.ic_menu_mylocation)
                .setAutoCancel(true)
                .setContentIntent(openPending);

        // Действия прямо из шторки (лимит Android — 3 кнопки).
        if (visitId > 0) {
            builder.addAction(stopAction("Закрыть по GPS", visitId, "complete", null));
            builder.addAction(stopAction("Обед/пауза", visitId, "label", "pause"));
            builder.addAction(stopAction("Ожидание", visitId, "label", "waiting"));
        }
        manager.notify(ALERT_NOTIFICATION_ID, builder.build());
    }

    private Notification.Action stopAction(String title, int visitId, String kind, String label) {
        Intent intent = new Intent(this, StopActionReceiver.class);
        // Разный action у каждой кнопки — чтобы PendingIntent'ы не перезаписывали extras.
        intent.setAction("stop_action:" + kind + ":" + (label == null ? "" : label));
        intent.putExtra(StopActionReceiver.EXTRA_VISIT_ID, visitId);
        intent.putExtra(StopActionReceiver.EXTRA_KIND, kind);
        if (label != null) {
            intent.putExtra(StopActionReceiver.EXTRA_LABEL, label);
        }
        int requestCode = visitId * 10 + (kind + ":" + label).hashCode();
        PendingIntent pending = PendingIntent.getBroadcast(
                this, requestCode, intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        return new Notification.Action.Builder(0, title, pending).build();
    }

    private String normalizeLocationUrl(String value) {
        String url = value == null ? "" : value.trim();
        if (url.isEmpty()) {
            return "";
        }
        if (url.endsWith("/location")) {
            return url;
        }
        if (url.endsWith("/")) {
            return url + "location";
        }
        return url + "/location";
    }

    private String normalizeDrivingUrl(String locationUrl) {
        String url = locationUrl == null ? "" : locationUrl.trim();
        if (url.endsWith("/location")) {
            return url.substring(0, url.length() - "/location".length()) + "/driving";
        }
        if (url.endsWith("/")) {
            return url + "driving";
        }
        return url + "/driving";
    }

    private double calculateJerkScore() {
        if (samplesCount <= 0) {
            return 0;
        }
        return Math.min(100.0, jerkTotal / samplesCount * 2.0);
    }

    private double calculateSpeedVariabilityScore() {
        if (speedDeltaSamples <= 0) {
            return 0;
        }
        return Math.min(100.0, speedDeltaTotal / speedDeltaSamples * 4.0);
    }

    private double calculateAggressiveScore() {
        double hours = Math.max(0.25, sensorSeconds / 3600.0);
        double eventRate = (
                harshAccelerationCount
                        + harshBrakingCount
                        + hardCorneringCount
                        + laneChangeProxyCount * 0.6
                        + stopGoCount * 0.4
        ) / hours;
        return Math.min(100.0, eventRate * 2.5 + calculateJerkScore() * 0.35 + calculateSpeedVariabilityScore() * 0.25);
    }

    private void loadAggregate() {
        SharedPreferences prefs = getSharedPreferences(MainActivity.PREFS, MODE_PRIVATE);
        String today = today();
        String storedDay = prefs.getString("driving_day", today);
        if (!today.equals(storedDay)) {
            resetAggregate(today);
            return;
        }
        segmentIndex = prefs.getInt("driving_segment_index", 0);
        samplesCount = prefs.getInt("driving_samples_count", 0);
        sensorSeconds = Double.longBitsToDouble(prefs.getLong("driving_sensor_seconds", Double.doubleToLongBits(0)));
        harshAccelerationCount = prefs.getInt("driving_harsh_acceleration_count", 0);
        harshBrakingCount = prefs.getInt("driving_harsh_braking_count", 0);
        hardCorneringCount = prefs.getInt("driving_hard_cornering_count", 0);
        laneChangeProxyCount = prefs.getInt("driving_lane_change_proxy_count", 0);
        stopGoCount = prefs.getInt("driving_stop_go_count", 0);
        jerkTotal = Double.longBitsToDouble(prefs.getLong("driving_jerk_total", Double.doubleToLongBits(0)));
        speedDeltaTotal = Double.longBitsToDouble(prefs.getLong("driving_speed_delta_total", Double.doubleToLongBits(0)));
        speedDeltaSamples = prefs.getInt("driving_speed_delta_samples", 0);
    }

    private void persistAggregate() {
        getSharedPreferences(MainActivity.PREFS, MODE_PRIVATE)
                .edit()
                .putString("driving_day", today())
                .putInt("driving_segment_index", segmentIndex)
                .putInt("driving_samples_count", samplesCount)
                .putLong("driving_sensor_seconds", Double.doubleToLongBits(sensorSeconds))
                .putInt("driving_harsh_acceleration_count", harshAccelerationCount)
                .putInt("driving_harsh_braking_count", harshBrakingCount)
                .putInt("driving_hard_cornering_count", hardCorneringCount)
                .putInt("driving_lane_change_proxy_count", laneChangeProxyCount)
                .putInt("driving_stop_go_count", stopGoCount)
                .putLong("driving_jerk_total", Double.doubleToLongBits(jerkTotal))
                .putLong("driving_speed_delta_total", Double.doubleToLongBits(speedDeltaTotal))
                .putInt("driving_speed_delta_samples", speedDeltaSamples)
                .apply();
    }

    private void resetDailyIfNeeded() {
        SharedPreferences prefs = getSharedPreferences(MainActivity.PREFS, MODE_PRIVATE);
        String today = today();
        String storedDay = prefs.getString("driving_day", today);
        if (!today.equals(storedDay)) {
            resetAggregate(today);
        }
    }

    private void resetAggregate(String day) {
        segmentIndex = 0;
        samplesCount = 0;
        sensorSeconds = 0;
        harshAccelerationCount = 0;
        harshBrakingCount = 0;
        hardCorneringCount = 0;
        laneChangeProxyCount = 0;
        stopGoCount = 0;
        jerkTotal = 0;
        speedDeltaTotal = 0;
        speedDeltaSamples = 0;
        lastLinearAccel = 0f;
        lastSpeedKmh = -1f;
        lastSpeedTimeMs = 0L;
        getSharedPreferences(MainActivity.PREFS, MODE_PRIVATE)
                .edit()
                .putString("driving_day", day)
                .apply();
        persistAggregate();
    }

    private String today() {
        return new SimpleDateFormat("yyyy-MM-dd", Locale.US).format(new Date());
    }

    private Notification notification(String text) {
        Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(this, CHANNEL_ID)
                : new Notification.Builder(this);
        return builder
                .setContentTitle("VizitorKrut GPS")
                .setContentText(text)
                .setSmallIcon(android.R.drawable.ic_menu_mylocation)
                .setOngoing(true)
                .build();
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            return;
        }
        NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "GPS upload",
                NotificationManager.IMPORTANCE_LOW
        );
        NotificationChannel alertChannel = new NotificationChannel(
                ALERT_CHANNEL_ID,
                "Подсказки по адресам",
                NotificationManager.IMPORTANCE_HIGH
        );
        alertChannel.setDescription("Уведомления, когда вы дошли до адреса и можно закрыть его по GPS");
        NotificationManager manager = getSystemService(NotificationManager.class);
        if (manager != null) {
            manager.createNotificationChannel(channel);
            manager.createNotificationChannel(alertChannel);
        }
    }
}
