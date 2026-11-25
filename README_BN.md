# WEVLO Free Android Build System (Starter)

এই starter-এ Website URL অথবা HTTPS ZIP URL থেকে Android WebView Debug APK এবং Android Studio source ZIP তৈরি হয়।

## GitHub setup
এই ZIP-এর সব ফাইল `siftifybd/-wevlo-android-builder` repository-র root-এ upload/commit করুন।
Workflow: `.github/workflows/android-build.yml`

Repository → Actions → WEVLO Android Build → Run workflow:
- mode: `url` অথবা `zip`
- website_url: URL mode-এর HTTPS address
- website_zip_url: ZIP mode-এর direct HTTPS ZIP address
- app_name: অ্যাপের নাম
- package_name: যেমন `com.example.mywebsite`

সফল হলে Actions run-এর Artifacts থেকে `wevlo-debug-apk` এবং `wevlo-android-studio-project` পাবেন।

## Cloudflare Worker
`worker/README_BN.md` অনুসরণ করুন। Deploy করা Worker URL-ই WEVLO-র External Android Build Server URL হবে।

## API
`POST /build`, Firebase ID token Bearer header-এ পাঠাতে হবে।
URL mode body:
```json
{"mode":"url","websiteUrl":"https://example.com","appName":"Example","packageName":"com.example.website"}
```
ZIP mode body:
```json
{"mode":"zip","websiteZipUrl":"https://files.example.com/site.zip","appName":"Example","packageName":"com.example.website"}
```

## সীমাবদ্ধতা ও নিরাপত্তা
- Output এখন Debug APK; Play Store/production Release APK নয়।
- ZIP URL সরাসরি HTTPS download link হতে হবে। WEVLO upload UI/R2 integration এই starter-এ নেই।
- GitHub Actions ও Cloudflare free usage limits প্রযোজ্য।
- Public repository-তে secret, signing key বা service-account JSON commit করবেন না।
- Production-এর আগে per-user quota, rate limit, queue, build status callback, malware/content scanning এবং security review যোগ করুন।
