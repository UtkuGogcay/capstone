#include "Button2.h"
#include <esp_now.h>
#include <WiFi.h>

#define LASER_CONTROL_PIN 21
#define BUTTON_A_PIN 2
#define BUTTON_B_PIN 11

Button2 buttonA(BUTTON_A_PIN);
Button2 buttonB(BUTTON_B_PIN);


uint8_t broadcastAddress[] = {0x40, 0x4C, 0xCA, 0x5F, 0xA4, 0x54};

esp_now_peer_info_t peerInfo;

void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
  Serial.print("\r\nLast Packet Send Status:\t");
  Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Delivery Success" : "Delivery Fail");
}

void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);
  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  // Once ESPNow is successfully Init, we will register for Send CB to
  // get the status of Transmitted packet
  esp_now_register_send_cb(OnDataSent);

  // Register peer
  memcpy(peerInfo.peer_addr, broadcastAddress, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;

  // Add peer
  if (esp_now_add_peer(&peerInfo) != ESP_OK){
    Serial.println("Failed to add peer");
    return;
  }
  buttonA.setClickHandler(onClickA);
  buttonB.setClickHandler(onClickB);
  pinMode(LASER_CONTROL_PIN, OUTPUT);
  delay(1000);
}

void loop() {
  buttonA.loop();
  buttonB.loop();
}
void sendSignal(char dataToSend){

  esp_err_t result = esp_now_send(broadcastAddress, (uint8_t *) &dataToSend, sizeof(dataToSend));

  if (result == ESP_OK) {
    Serial.println("Sent with success");
  }
  else {
    Serial.println("Error sending the data");
  }
}
void onClickA(Button2& btn) {
  Serial.println("ir laser fired from gun a");
  sendSignal('a');
  digitalWrite(LASER_CONTROL_PIN, HIGH);
  delay(50);
  digitalWrite(LASER_CONTROL_PIN, LOW);
}
void onClickB(Button2& btn) {
  Serial.println("ir laser fired from gun b");
  sendSignal('b');
  digitalWrite(LASER_CONTROL_PIN, HIGH);
  delay(50);
  digitalWrite(LASER_CONTROL_PIN, LOW);
}