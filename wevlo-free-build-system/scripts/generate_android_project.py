import os, re, shutil, zipfile, urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path("generated-android")
MODE = os.getenv("BUILD_MODE", "url").strip().lower()
APP_NAME = os.getenv("APP_NAME", "My Website").strip()[:40]
PACKAGE = os.getenv("PACKAGE_NAME", "com.example.mywebsite").strip()
WEBSITE_URL = os.getenv("WEBSITE_URL", "").strip()
ZIP_URL = os.getenv("WEBSITE_ZIP_URL", "").strip()

if MODE not in ("url", "zip"):
    raise SystemExit("BUILD_MODE must be url or zip")
if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*){1,5}", PACKAGE):
    raise SystemExit("Invalid package_name")
if not APP_NAME:
    raise SystemExit("app_name is required")

def validate_https(value):
    if not value.startswith("https://") or len(value) > 2048 or any(c in value for c in "\r\n\t "):
        raise SystemExit("Only valid HTTPS URLs are allowed")

if MODE == "url":
    validate_https(WEBSITE_URL)
else:
    validate_https(ZIP_URL)

if ROOT.exists():
    shutil.rmtree(ROOT)
package_path = Path(*PACKAGE.split("."))
java_dir = ROOT / "app/src/main/java" / package_path
assets_dir = ROOT / "app/src/main/assets/www"
java_dir.mkdir(parents=True, exist_ok=True)
assets_dir.mkdir(parents=True, exist_ok=True)

local_start = ""
if MODE == "zip":
    archive_path = Path("website-upload.zip")
    req = urllib.request.Request(ZIP_URL, headers={"User-Agent": "WEVLO-Builder/1.0"})
    total = 0
    with urllib.request.urlopen(req, timeout=30) as response, archive_path.open("wb") as out:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > 40 * 1024 * 1024:
                raise SystemExit("ZIP download exceeds 40 MB")
            out.write(chunk)
    count = 0
    expanded = 0
    with zipfile.ZipFile(archive_path) as archive:
        for item in archive.infolist():
            name = item.filename.replace("\\", "/")
            p = Path(name)
            if p.is_absolute() or ".." in p.parts:
                raise SystemExit("Unsafe ZIP path")
            if item.is_dir():
                continue
            count += 1
            expanded += item.file_size
            if count > 3000 or expanded > 100 * 1024 * 1024:
                raise SystemExit("ZIP contains too many/large files")
            destination = (assets_dir / p).resolve()
            if assets_dir.resolve() not in destination.parents:
                raise SystemExit("ZIP path escapes assets")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(item) as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target)
    archive_path.unlink(missing_ok=True)
    if (assets_dir / "index.html").exists():
        local_start = "index.html"
    else:
        indexes = list(assets_dir.rglob("index.html"))
        if len(indexes) != 1:
            raise SystemExit("ZIP must contain root index.html or exactly one nested index.html")
        local_start = indexes[0].relative_to(assets_dir).as_posix()

url_literal = WEBSITE_URL.replace("\\", "\\\\").replace('"', '\\"')
start_literal = local_start.replace("\\", "\\\\").replace('"', '\\"')

(ROOT / "settings.gradle.kts").write_text(
    'pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }\n'
    'dependencyResolutionManagement { repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS); repositories { google(); mavenCentral() } }\n'
    'rootProject.name = "WEVLOWebsiteApp"\ninclude(":app")\n'
)
(ROOT / "build.gradle.kts").write_text(
    'plugins {\n'
    '    id("com.android.application") version "8.7.3" apply false\n'
    '    id("org.jetbrains.kotlin.android") version "2.0.21" apply false\n'
    '}\n'
)
(ROOT / "gradle.properties").write_text(
    "org.gradle.jvmargs=-Xmx2g -Dfile.encoding=UTF-8\n"
    "android.useAndroidX=true\nkotlin.code.style=official\n"
)
(ROOT / "app/build.gradle.kts").write_text(f'''plugins {{
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}}
android {{
    namespace = "{PACKAGE}"
    compileSdk = 35
    defaultConfig {{
        applicationId = "{PACKAGE}"
        minSdk = 23
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"
        buildConfigField("String", "WEBSITE_URL", "\\"{url_literal}\\"")
        buildConfigField("String", "LOCAL_START_PATH", "\\"{start_literal}\\"")
    }}
    buildFeatures {{ buildConfig = true }}
}}
dependencies {{
    implementation("androidx.webkit:webkit:1.12.1")
    implementation("androidx.activity:activity-ktx:1.10.0")
}}
''')
manifest = f'''<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.INTERNET" />
    <application android:allowBackup="false" android:label="{escape(APP_NAME)}"
        android:supportsRtl="true" android:theme="@android:style/Theme.Material.Light.NoActionBar"
        android:usesCleartextTraffic="false">
        <activity android:name=".MainActivity" android:exported="true"
            android:configChanges="orientation|screenSize|keyboardHidden">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
'''
(ROOT / "app/src/main/AndroidManifest.xml").write_text(manifest)
main = f'''package {PACKAGE}

import android.net.Uri
import android.os.Bundle
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import androidx.activity.ComponentActivity
import androidx.webkit.WebViewAssetLoader
import androidx.webkit.WebViewClientCompat

class MainActivity : ComponentActivity() {{
    private lateinit var webView: WebView

    override fun onCreate(savedInstanceState: Bundle?) {{
        super.onCreate(savedInstanceState)
        webView = WebView(this)
        setContentView(webView)

        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.settings.allowFileAccess = false
        webView.settings.allowContentAccess = false
        webView.settings.javaScriptCanOpenWindowsAutomatically = false
        webView.settings.setSupportMultipleWindows(false)

        val loader = WebViewAssetLoader.Builder()
            .addPathHandler("/assets/", WebViewAssetLoader.AssetsPathHandler(this))
            .build()

        webView.webViewClient = object : WebViewClientCompat() {{
            override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest) =
                loader.shouldInterceptRequest(request.url)

            @Suppress("DEPRECATION")
            override fun shouldInterceptRequest(view: WebView, url: String) =
                loader.shouldInterceptRequest(Uri.parse(url))

            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {{
                return request.url.scheme !in listOf("https", "http")
            }}
        }}
        webView.webChromeClient = WebChromeClient()

        if (BuildConfig.LOCAL_START_PATH.isNotBlank()) {{
            webView.loadUrl("https://appassets.androidplatform.net/assets/www/${{BuildConfig.LOCAL_START_PATH}}")
        }} else {{
            webView.loadUrl(BuildConfig.WEBSITE_URL)
        }}
    }}

    @Deprecated("Deprecated in Android")
    override fun onBackPressed() {{
        if (::webView.isInitialized && webView.canGoBack()) webView.goBack()
        else super.onBackPressed()
    }}
}}
'''
(java_dir / "MainActivity.kt").write_text(main)
(ROOT / "README.md").write_text("# WEVLO generated Android project\\nOpen this folder in Android Studio.\\n")
print("Android project generated successfully")
