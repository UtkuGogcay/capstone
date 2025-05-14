#include <esp_now.h>
#include <WiFi.h>

void OnDataRecv(const esp_now_recv_info *recv_info, const uint8_t *incomingData, int len) {
  String receivedString = "";
  for (int i = 0; i < 2; i++) {
    receivedString += (char)incomingData[i];
  }
    Serial.println(receivedString);
}

void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);

  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  esp_now_register_recv_cb(OnDataRecv);  // klasik callback
  Serial.println("Receiver ready!");
}

void loop() {
  // gelen veriler callback içinde işleniyor
}
