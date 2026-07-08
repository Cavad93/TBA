package com.homevisit.location;

import android.Manifest;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {
    static final String PREFS = "location_client";
    static final String KEY_SERVER_URL = "server_url";
    static final String KEY_API_KEY = "api_key";
    static final String KEY_INTERVAL_SECONDS = "interval_seconds";

    private static final int PERMISSION_REQUEST = 1001;

    private EditText serverUrlInput;
    private EditText apiKeyInput;
    private EditText intervalInput;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(40, 56, 40, 40);
        root.setGravity(Gravity.CENTER_HORIZONTAL);
        setContentView(root);

        TextView title = new TextView(this);
        title.setText("Home Visit GPS");
        title.setTextSize(24);
        title.setGravity(Gravity.CENTER);
        root.addView(title, matchWrap());

        TextView subtitle = new TextView(this);
        subtitle.setText("Отправляет координаты на сервер только когда вы нажали старт.");
        subtitle.setTextSize(15);
        subtitle.setPadding(0, 16, 0, 24);
        root.addView(subtitle, matchWrap());

        serverUrlInput = new EditText(this);
        serverUrlInput.setHint("https://your-server.example.com:8088/location");
        serverUrlInput.setSingleLine(true);
        serverUrlInput.setText(prefs.getString(KEY_SERVER_URL, ""));
        root.addView(label("URL сервера"));
        root.addView(serverUrlInput, matchWrap());

        apiKeyInput = new EditText(this);
        apiKeyInput.setHint("LOCATION_API_KEY");
        apiKeyInput.setSingleLine(true);
        apiKeyInput.setText(prefs.getString(KEY_API_KEY, ""));
        root.addView(label("API ключ"));
        root.addView(apiKeyInput, matchWrap());

        intervalInput = new EditText(this);
        intervalInput.setHint("60");
        intervalInput.setSingleLine(true);
        intervalInput.setText(String.valueOf(prefs.getInt(KEY_INTERVAL_SECONDS, 60)));
        root.addView(label("Интервал отправки, сек"));
        root.addView(intervalInput, matchWrap());

        Button startButton = new Button(this);
        startButton.setText("Начать отправку GPS");
        startButton.setOnClickListener(view -> startTracking());
        root.addView(startButton, matchWrap());

        Button stopButton = new Button(this);
        stopButton.setText("Остановить");
        stopButton.setOnClickListener(view -> stopTracking());
        root.addView(stopButton, matchWrap());
    }

    private TextView label(String text) {
        TextView label = new TextView(this);
        label.setText(text);
        label.setTextSize(14);
        label.setPadding(0, 18, 0, 4);
        return label;
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        );
    }

    private void startTracking() {
        if (!hasRequiredPermissions()) {
            requestRequiredPermissions();
            return;
        }
        String serverUrl = serverUrlInput.getText().toString().trim();
        String apiKey = apiKeyInput.getText().toString().trim();
        int intervalSeconds = parseIntervalSeconds(intervalInput.getText().toString().trim());

        if (serverUrl.isEmpty() || apiKey.isEmpty()) {
            Toast.makeText(this, "Заполните URL сервера и API ключ", Toast.LENGTH_LONG).show();
            return;
        }

        getSharedPreferences(PREFS, MODE_PRIVATE)
                .edit()
                .putString(KEY_SERVER_URL, serverUrl)
                .putString(KEY_API_KEY, apiKey)
                .putInt(KEY_INTERVAL_SECONDS, intervalSeconds)
                .apply();

        Intent intent = new Intent(this, LocationUploadService.class);
        intent.setAction(LocationUploadService.ACTION_START);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent);
        } else {
            startService(intent);
        }
        Toast.makeText(this, "Отправка GPS запущена", Toast.LENGTH_SHORT).show();
    }

    private void stopTracking() {
        Intent intent = new Intent(this, LocationUploadService.class);
        intent.setAction(LocationUploadService.ACTION_STOP);
        startService(intent);
        Toast.makeText(this, "Отправка GPS остановлена", Toast.LENGTH_SHORT).show();
    }

    private int parseIntervalSeconds(String value) {
        try {
            return Math.max(60, Integer.parseInt(value));
        } catch (NumberFormatException ignored) {
            return 60;
        }
    }

    private boolean hasRequiredPermissions() {
        boolean locationGranted = checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED;
        boolean notificationsGranted = Build.VERSION.SDK_INT < 33
                || checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED;
        return locationGranted && notificationsGranted;
    }

    private void requestRequiredPermissions() {
        if (Build.VERSION.SDK_INT >= 33) {
            requestPermissions(
                    new String[]{Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.POST_NOTIFICATIONS},
                    PERMISSION_REQUEST
            );
        } else {
            requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION}, PERMISSION_REQUEST);
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == PERMISSION_REQUEST && hasRequiredPermissions()) {
            startTracking();
        } else {
            Toast.makeText(this, "Нужны разрешения на точную геолокацию и уведомление", Toast.LENGTH_LONG).show();
        }
    }
}
