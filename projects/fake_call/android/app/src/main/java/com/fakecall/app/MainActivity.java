package com.fakecall.app;

import android.app.Activity;
import android.os.Bundle;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;

public class MainActivity extends Activity {

    private WebView webView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        getWindow().addFlags(
                WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
                        | WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED
                        | WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON);

        webView = new WebView(this);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setAllowFileAccess(true);

        // The fake ringtone plays via a script-driven <audio>/WebAudio element with
        // no user tap right before it (it's triggered by a countdown timer), so the
        // default "needs a gesture" autoplay policy would silently block it.
        webView.setWebChromeClient(new WebChromeClient());

        // The number-lookup provider has no CORS support, so a page-side fetch()
        // would be blocked by the browser regardless of origin. There's no Flask
        // backend inside the APK to proxy through (unlike the web build), so this
        // bridge performs the HTTP call natively instead — JS calls
        // window.AndroidLookup.lookupNumber(...), see lookupClient.js.
        webView.addJavascriptInterface(new LookupBridge(), "AndroidLookup");

        setContentView(webView);
        webView.loadUrl("file:///android_asset/index.html");
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.destroy();
        }
        super.onDestroy();
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    private class LookupBridge {
        private static final String BASE_URL = "http://apilayer.net/api/validate";

        @JavascriptInterface
        public void lookupNumber(final String number, final String apiKey, final String callbackId) {
            new Thread(() -> {
                String resultJson;
                try {
                    resultJson = normalize(fetchRaw(number, apiKey));
                } catch (Exception e) {
                    resultJson = errorJson(String.valueOf(e.getMessage()));
                }
                deliver(callbackId, resultJson);
            }).start();
        }

        private String fetchRaw(String number, String apiKey) throws Exception {
            String url = BASE_URL
                    + "?access_key=" + URLEncoder.encode(apiKey, "UTF-8")
                    + "&number=" + URLEncoder.encode(number, "UTF-8")
                    + "&format=1";
            HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection();
            conn.setConnectTimeout(10000);
            conn.setReadTimeout(10000);
            BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) sb.append(line);
            reader.close();
            return sb.toString();
        }

        // Mirrors app/lookup.py's normalize_lookup_response — same field
        // names so renderLookupResult() in app.js doesn't need to branch.
        private String normalize(String rawJson) throws Exception {
            JSONObject raw = new JSONObject(rawJson);
            if (raw.has("error")) {
                JSONObject err = raw.optJSONObject("error");
                return errorJson(err != null ? err.optString("info", "Lookup failed.") : "Lookup failed.");
            }
            JSONObject out = new JSONObject();
            out.put("valid", raw.optBoolean("valid", false));
            out.put("number", raw.has("international_format") ? raw.optString("international_format") : raw.opt("number"));
            out.put("localFormat", raw.opt("local_format"));
            out.put("countryName", raw.opt("country_name"));
            out.put("countryCode", raw.opt("country_code"));
            out.put("location", raw.opt("location"));
            out.put("carrier", raw.opt("carrier"));
            out.put("lineType", raw.opt("line_type"));
            return out.toString();
        }

        private String errorJson(String message) {
            try {
                return new JSONObject().put("valid", false).put("error", message).toString();
            } catch (Exception e) {
                return "{\"valid\":false,\"error\":\"Lookup failed.\"}";
            }
        }

        private void deliver(String callbackId, String resultJson) {
            runOnUiThread(() -> webView.evaluateJavascript(
                    "window.__lookupCallback(" + JSONObject.quote(callbackId) + ", " + resultJson + ")", null));
        }
    }
}
