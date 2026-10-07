#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>

#include "secrets.h"

namespace {
constexpr uint8_t kButtons[] = {4, 5, 6, 7};
constexpr const char *kEvents[] = {"understood", "need_help", "task_done", "anonymous_help"};
constexpr unsigned long kDebounceMs = 350;
unsigned long lastPressMs[4] = {0, 0, 0, 0};
uint32_t eventCounter = 0;

String makeEventId() {
  return String(PLEX_DEVICE_ID) + "-" + String(millis()) + "-" + String(++eventCounter);
}

bool postEvent(const char *eventType, bool anonymous) {
  if (WiFi.status() != WL_CONNECTED) return false;

  WiFiClientSecure client;
  // 工程骨架：正式版本必须配置受信 CA，不得使用 setInsecure()。
  client.setInsecure();

  HTTPClient http;
  if (!http.begin(client, PLEX_API_URL)) return false;
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Authorization", String("Bearer ") + PLEX_DEVICE_TOKEN);

  JsonDocument payload;
  payload["device_id"] = PLEX_DEVICE_ID;
  payload["session_id"] = "unbound-test-session";
  payload["event_id"] = makeEventId();
  payload["event_type"] = eventType;
  payload["anonymous"] = anonymous;
  payload["firmware_version"] = "0.1.0-proposal";

  String body;
  serializeJson(payload, body);
  const int status = http.POST(body);
  http.end();
  return status >= 200 && status < 300;
}

void connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(PLEX_WIFI_SSID, PLEX_WIFI_PASSWORD);
  const unsigned long started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < 15000) {
    delay(250);
  }
}
}  // namespace

void setup() {
  Serial.begin(115200);
  for (const auto pin : kButtons) pinMode(pin, INPUT_PULLUP);
  connectWifi();
  Serial.println(WiFi.status() == WL_CONNECTED ? "PLEX Edge online" : "PLEX Edge offline");
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) connectWifi();
  for (size_t i = 0; i < 4; ++i) {
    if (digitalRead(kButtons[i]) == LOW && millis() - lastPressMs[i] > kDebounceMs) {
      lastPressMs[i] = millis();
      const bool ok = postEvent(kEvents[i], i == 3);
      Serial.printf("event=%s result=%s\n", kEvents[i], ok ? "accepted" : "queued-needed");
    }
  }
  delay(20);
}
