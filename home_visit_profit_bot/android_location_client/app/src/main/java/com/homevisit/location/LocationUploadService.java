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

import org.json.JSONObject;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class LocationUploadService extends Service implements LocationListener {
    static final String ACTION_START = "com.homevisit.location.START";
    static final String ACTION_STOP = "com.homevisit.location.STOP";

    private static final int NOTIFICATION_ID = 7001;
    private static final String CHANNEL_ID = "location_upload";

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private LocationManager locationManager;

    @Override
    public void onCreate() {
        super.onCreate();
        locationManager = (LocationManager) getSystemService(Context.LOCATION_SERVICE);
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
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        stopLocationUpdates();
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

    @Override
    public void onLocationChanged(Location location) {
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
            } catch (Exception ignored) {
            } finally {
                if (connection != null) {
                    connection.disconnect();
                }
            }
        });
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
