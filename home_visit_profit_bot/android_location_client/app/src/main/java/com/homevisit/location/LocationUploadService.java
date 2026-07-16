package com.homevisit.location;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
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
                connection.getResponseCode();
                sendDrivingAggregateSync(serverUrl, apiKey);
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

    private void sendDrivingAggregateSync(String locationUrl, String apiKey) {
        persistAggregate();
        HttpURLConnection connection = null;
        try {
            JSONObject payload = new JSONObject();
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
                .setContentTitle("Home Visit GPS")
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
        NotificationManager manager = getSystemService(NotificationManager.class);
        if (manager != null) {
            manager.createNotificationChannel(channel);
        }
    }
}
