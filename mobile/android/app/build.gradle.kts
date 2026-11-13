import java.io.FileInputStream
import java.util.Properties

plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

// Release signing: env vars (CI) win over git-ignored android/key.properties.
// Falls back to the debug key when neither is present (local / PR builds).
val keyProps = Properties().apply {
    val f = rootProject.file("key.properties")
    if (f.exists()) FileInputStream(f).use { load(it) }
}
fun signingValue(env: String, prop: String): String? =
    System.getenv(env)?.takeIf { it.isNotBlank() } ?: keyProps.getProperty(prop)
val releaseStoreFile = signingValue("NEXARA_KEYSTORE_PATH", "storeFile")
val hasReleaseKey = releaseStoreFile != null &&
    signingValue("NEXARA_KEYSTORE_PASSWORD", "storePassword") != null &&
    signingValue("NEXARA_KEY_ALIAS", "keyAlias") != null &&
    signingValue("NEXARA_KEY_PASSWORD", "keyPassword") != null

android {
    namespace = "dev.jmolabs.nexara_mobile"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }

    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_11.toString()
    }

    defaultConfig {
        applicationId = "dev.jmolabs.nexara_mobile"
        // local_auth / camera / firebase_messaging need API 23+.
        minSdk = maxOf(flutter.minSdkVersion, 23)
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    signingConfigs {
        if (hasReleaseKey) {
            create("release") {
                storeFile = rootProject.file(releaseStoreFile!!)
                storePassword = signingValue("NEXARA_KEYSTORE_PASSWORD", "storePassword")
                keyAlias = signingValue("NEXARA_KEY_ALIAS", "keyAlias")
                keyPassword = signingValue("NEXARA_KEY_PASSWORD", "keyPassword")
            }
        }
    }

    buildTypes {
        release {
            signingConfig = signingConfigs.getByName(if (hasReleaseKey) "release" else "debug")
        }
    }
}

flutter {
    source = "../.."
}
