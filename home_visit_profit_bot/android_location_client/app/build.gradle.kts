plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("org.jetbrains.kotlin.kapt")
}

android {
    namespace = "com.homevisit.location"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.homevisit.location"
        minSdk = 26
        targetSdk = 35
        // versionCode берётся из номера сборки CI (монотонно растёт) — чтобы каждое
        // обновление было «новее» предыдущего. Локально (без CI) — 1.
        val buildNumber = System.getenv("GITHUB_RUN_NUMBER")?.toIntOrNull() ?: 1
        versionCode = buildNumber
        versionName = "1.0.$buildNumber"
        // Инструментальные тесты (androidTest) гоняются на эмуляторе в CI и на живых
        // телефонах Firebase Test Lab — это проверка клиента без физического устройства.
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildFeatures {
        compose = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    signingConfigs {
        create("release") {
            val keystorePath = System.getenv("ANDROID_KEYSTORE_FILE")
            if (keystorePath != null && file(keystorePath).exists()) {
                storeFile = file(keystorePath)
                storePassword = System.getenv("ANDROID_KEYSTORE_PASSWORD")
                keyAlias = System.getenv("ANDROID_KEY_ALIAS")
                keyPassword = System.getenv("ANDROID_KEY_PASSWORD")
            }
        }
    }

    buildTypes {
        getByName("release") {
            isMinifyEnabled = false
            // Ключ передан через окружение (CI-секреты) — подписываем релизным ключом;
            // иначе (локально/форки без секретов) — debug-подпись, чтобы сборка не падала.
            val keystorePath = System.getenv("ANDROID_KEYSTORE_FILE")
            signingConfig = if (keystorePath != null && file(keystorePath).exists()) {
                signingConfigs.getByName("release")
            } else {
                signingConfigs.getByName("debug")
            }
        }
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.12.01")
    implementation(composeBom)
    androidTestImplementation(composeBom)

    implementation("androidx.activity:activity-compose:1.9.3")
    // NotificationCompat/NotificationManagerCompat для плановых уведомлений (Ф7).
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.room:room-ktx:2.6.1")
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    implementation("androidx.work:work-runtime-ktx:2.9.1")
    kapt("androidx.room:room-compiler:2.6.1")
    debugImplementation("androidx.compose.ui:ui-tooling")

    // JVM unit-тесты: золотые векторы выгодности (Фаза 3.1) гоняются на сборке через
    // `gradlew testReleaseUnitTest`. org.json — та же реализация, что в Android рантайме.
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20240303")

    // Инструментальные тесты: краши, UI-сценарии, share-target. Гоняются на эмуляторе
    // в GitHub Actions (без внешних кредов) и на живых телефонах Firebase Test Lab.
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test:rules:1.6.1")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.6.1")
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    // Пустой манифест для createAndroidComposeRule — обязателен, иначе тест не поднимет Activity.
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}
