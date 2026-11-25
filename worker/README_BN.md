# Cloudflare Worker Setup

1. Cloudflare Dashboard → Workers & Pages → Create Worker.
2. Worker editor-এ `src/index.js` কোড paste করে Deploy করুন; অথবা Wrangler দিয়ে deploy করুন।
3. Settings → Variables and Secrets-এ নিচের মান দিন।

## Secrets
- `GH_TOKEN`: Fine-grained GitHub token; শুধু `siftifybd/-wevlo-android-builder` repository এবং Actions: Read and write permission।
- `FIREBASE_API_KEY`: Firebase Project Settings → General থেকে Web API Key।

## Variables
- `FIREBASE_PROJECT_ID`: Firebase project ID
- `GH_OWNER`: `siftifybd`
- `GH_REPO`: `-wevlo-android-builder`
- `GH_BRANCH`: `main`
- `ALLOWED_ORIGIN`: WEVLO site-এর exact origin, যেমন `https://your-project.pages.dev`

Worker URL-টি WEVLO-র External Android Build Server URL হবে। `GH_TOKEN` কখনো frontend-এ রাখবেন না।

## Frontend request
```js
const idToken = await auth.currentUser.getIdToken();
const response = await fetch(`${BUILD_API_URL}/build`, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${idToken}`
  },
  body: JSON.stringify({
    mode: "url",
    websiteUrl: "https://example.com",
    appName: "Example",
    packageName: "com.example.website"
  })
});
const result = await response.json();
```

ZIP mode-এ `mode: "zip"` এবং `websiteZipUrl` পাঠাতে হবে। এই starter ZIP সরাসরি upload করে না; ZIP-টি আগে HTTPS direct-download host-এ রাখতে হবে। পরে R2 upload integration যোগ করতে হবে।
