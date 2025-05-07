#include <esp_now.h>
#include <WiFi.h>

void OnDataRecv(const esp_now_recv_info *recv_info, const uint8_t *incomingData, int len) {

  if (len == 1) {
    char receivedChar = (char)incomingData[0];
    Serial.print("ir laser fired from gun ");
    Serial.println(receivedChar);
  } else {
    Serial.println("Unexpected data length!");
  }

}

void setup() {
  Serial.begin(115200);

  WiFi.mode(WIFI_STA);

  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  esp_now_register_recv_cb(OnDataRecv);
}

void loop() {
}
