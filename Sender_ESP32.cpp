#include "Button2.h"
#include <esp_now.h>
#include <WiFi.h>

// PLAYER 1

// Pin tanımları
#define LASER_CONTROL_PIN 21
#define MOTOR_CONTROL_PIN 22
#define BUZZER_CONTROL_PIN 23
#define BUTTON_A1_PIN 2
#define BUTTON_A2_PIN 11

Button2 buttonA1(BUTTON_A1_PIN);
Button2 buttonA2(BUTTON_A2_PIN);

// ESP-NOW hedef MAC adresi (receiver'ın MAC adresi)
uint8_t broadcastAddress[]  {0x40, 0x4C, 0xCA, 0x5F, 0xB4, 0xDC};

esp_now_peer_info_t peerInfo;

// Durum değişkenleri
unsigned long laserStart = 0;
unsigned long motorStart = 0;
unsigned long buzzerStart = 0;

bool laserActive = false;
bool motorActive = false;
bool buzzerActive = false;

// Süreler (ms cinsinden)
const unsigned long LASER_DURATION = 50;
const unsigned long MOTOR_DURATION = 100;
const unsigned long BUZZER_DURATION = 200;

void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
  Serial.print("Send Status: ");
  Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Success" : "Fail");
}

void sendSignal(String dataToSend) {
  esp_err_t result = esp_now_send(broadcastAddress, (uint8_t *) &dataToSend, sizeof(dataToSend));
  if (result == ESP_OK) {
    Serial.println("Sent with success");
  } else {
    Serial.println("Error sending the data");
  }
}

void onButtonA1Released(Button2 &btn) {
  Serial.println("A1 bırakıldı → lazer + motor + buzzer");
  sendSignal("A1");

  digitalWrite(LASER_CONTROL_PIN, HIGH);
  laserStart = millis();
  laserActive = true;

  digitalWrite(MOTOR_CONTROL_PIN, HIGH);
  motorStart = millis();
  motorActive = true;

  digitalWrite(BUZZER_CONTROL_PIN, HIGH);
  buzzerStart = millis();
  buzzerActive = true;
}

void onButtonA2Released(Button2 &btn) {
  Serial.println("A2 bırakıldı → lazer + motor + buzzer ");
  sendSignal("A2");

  digitalWrite(LASER_CONTROL_PIN, HIGH);
  laserStart = millis();
  laserActive = true;

  digitalWrite(MOTOR_CONTROL_PIN, HIGH);
  motorStart = millis();
  motorActive = true;

  digitalWrite(BUZZER_CONTROL_PIN, HIGH);
  buzzerStart = millis();
  buzzerActive = true;
}

void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init error");
    return;
  }

  esp_now_register_send_cb(OnDataSent);
  memcpy(peerInfo.peer_addr, broadcastAddress, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;
  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Peer add failed");
    return;
  }

  buttonA1.setPressedHandler(onButtonA1Released);
  buttonA2.setPressedHandler(onButtonA2Released);
  buttonA1.setDebounceTime(20);
  buttonA2.setDebounceTime(20);

  pinMode(LASER_CONTROL_PIN, OUTPUT);
  pinMode(MOTOR_CONTROL_PIN, OUTPUT);
  pinMode(BUZZER_CONTROL_PIN, OUTPUT);

  digitalWrite(LASER_CONTROL_PIN, LOW);
  digitalWrite(MOTOR_CONTROL_PIN, LOW);
  digitalWrite(BUZZER_CONTROL_PIN, LOW);
}

void loop() {
  buttonA1.loop();
  buttonA2.loop();

  unsigned long now = millis();

  if (laserActive && (now - laserStart >= LASER_DURATION)) {
    digitalWrite(LASER_CONTROL_PIN, LOW);
    laserActive = false;
  }

  if (motorActive && (now - motorStart >= MOTOR_DURATION)) {
    digitalWrite(MOTOR_CONTROL_PIN, LOW);
    motorActive = false;
  }

  if (buzzerActive && (now - buzzerStart >= BUZZER_DURATION)) {
    digitalWrite(BUZZER_CONTROL_PIN, LOW);
    buzzerActive = false;
  }
}
