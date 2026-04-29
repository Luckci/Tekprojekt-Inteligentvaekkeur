#include <Adafruit_NeoPixel.h>
#include <SPI.h>
#include <MFRC522.h>
#include <Wire.h>
#include "RTClib.h"
#include "SoftwareSerial.h"
#include "DFRobotDFPlayerMini.h"

// --- Pin Definitions ---
#define PIXEL_PIN      6
#define NUMPIXELS     10
#define RFID_RST_PIN   9
#define RFID_SS_PIN    8
#define MP3_RX_PIN     2 
#define MP3_TX_PIN     3 
#define MP3_GATE_PIN   5  // IRL540 MOSFET Gate

// --- Object Initialization ---
Adafruit_NeoPixel strip(NUMPIXELS, PIXEL_PIN, NEO_GRB + NEO_KHZ800);
MFRC522 mfrc522(RFID_SS_PIN, RFID_RST_PIN);
SoftwareSerial mp3Serial(MP3_RX_PIN, MP3_TX_PIN);
DFRobotDFPlayerMini myDFPlayer;
RTC_DS3231 rtc;

// --- Alarm Settings ---
bool isRunning = false; 
bool alarmTriggeredToday = false; 
const int alarmHour = 6;
const int alarmMinute = 15;

void setup() {
  // 1. MOSFET Gate Setup
  pinMode(MP3_GATE_PIN, OUTPUT);
  digitalWrite(MP3_GATE_PIN, HIGH); // Power ON the MP3 player

  // 2. Communications
  Serial.begin(9600);
  mp3Serial.begin(9600);
  SPI.begin();
  
  // 3. Component Init
  strip.begin();
  strip.show(); 
  mfrc522.PCD_Init();
  mfrc522.PCD_SetAntennaGain(mfrc522.RxGain_max);

  if (!rtc.begin()) {
    Serial.println(F("RTC Error: Check A4/A5 wiring!"));
  }

  // --- TIME SETTING ---
  // Uncomment the line below ONCE to set time, then comment it out and re-upload.
  rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));

  delay(500); 
  if (!myDFPlayer.begin(mp3Serial)) {
    Serial.println(F("DFPlayer Error: Check SD/Wiring"));
  } else {
    myDFPlayer.volume(40);
    Serial.println(F("DFPlayer Online."));
  }

  Serial.println(F("System Ready. Alarm: 06:15"));
}

void loop() {
  DateTime now = rtc.now();

  // 1. Live Clock Display (Every second when idle)
  if (!isRunning) {
    static int lastSec = -1;
    if (now.second() != lastSec) {
      displayTime(now);
      lastSec = now.second();
    }
  }

  // 2. Check Serial Commands
  if (Serial.available() > 0) {
    handleSerial();
  }

  // 3. Check RFID (only if idle)
  if (!isRunning && mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
    checkRFID();
  }

  // 4. Check RTC Alarm Time
  if (!isRunning && !alarmTriggeredToday && now.hour() == alarmHour && now.minute() == alarmMinute) {
    Serial.println(F("ALARM TIME REACHED!"));
    alarmTriggeredToday = true;
    triggerAlarm();
  }

  // 5. Reset Daily Flag at midnight
  if (now.hour() == 0 && now.minute() == 0) {
    alarmTriggeredToday = false;
  }
}

void displayTime(DateTime t) {
  Serial.print(F("Time: "));
  if (t.hour() < 10) Serial.print('0');
  Serial.print(t.hour());
  Serial.print(':');
  if (t.minute() < 10) Serial.print('0');
  Serial.print(t.minute());
  Serial.print(':');
  if (t.second() < 10) Serial.print('0');
  Serial.println(t.second());
}

void handleSerial() {
  String command = Serial.readStringUntil('\n');
  command.trim();
  if (command == "start" || command == "test") triggerAlarm();
  else if (command == "stop") stopAlarm();
}

void checkRFID() {
  byte buffer[18];
  byte size = sizeof(buffer);
  bool found = false;

  for (byte block = 4; block < 13; block++) {
    if (mfrc522.MIFARE_Read(block, buffer, &size) == MFRC522::STATUS_OK) {
      String data = "";
      for (uint8_t i = 0; i < 16; i++) {
        if (buffer[i] >= 32 && buffer[i] <= 126) data += (char)buffer[i];
      }
      if (data.indexOf("ALARM") != -1) {
        found = true;
        break;
      }
    }
  }
  if (found) triggerAlarm();
  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();
}

void triggerAlarm() {
  if (isRunning) return; 
  isRunning = true;

  Serial.println(F("Phase 1: Starting Sunrise..."));
  
  // 1. Run the Sunrise first
  // We capture if it finished naturally (true) or was stopped (false)
  bool completed = runSunrise(50); 

  // 2. Only start phase 2 (Music) if the sunrise wasn't manually stopped
  if (completed) {
    Serial.println(F("Phase 2: Sunrise Complete. Starting Music..."));
    
    digitalWrite(MP3_GATE_PIN, HIGH); // Power up MOSFET
    delay(300);                       // Boot time
    myDFPlayer.begin(mp3Serial);
    myDFPlayer.volume(20);
    myDFPlayer.play(2); 
  }
}

void stopAlarm() {
  // 1. MOSFET KILL
  digitalWrite(MP3_GATE_PIN, LOW); 
  
  // 2. LED KILL
  strip.setBrightness(0);
  strip.fill(strip.Color(0,0,0), 0, NUMPIXELS);
  strip.show();
  
  isRunning = false;
  Serial.println(F(">>> STOPPED: SYSTEM DISARMED <<<"));
}

// We change this to a 'bool' so it can tell triggerAlarm if it finished
bool runSunrise(int speedDelay) {
  for (int i = 0; i <= 255; i++) {
    if (Serial.available() > 0) {
      char c = Serial.read(); 
      if (c == 's' || c == 'S') { 
        while(Serial.available() > 0) Serial.read(); 
        stopAlarm();
        return false; // Return FALSE because we interrupted it
      }
    }

    int g = map(i, 0, 255, 15, 130);
    int b = map(i, 0, 255, 0, 80);
    int bri = map(i, 0, 255, 1, 255);

    strip.setBrightness(bri);
    strip.fill(strip.Color(255, g, b), 0, NUMPIXELS);
    strip.show();
    
    delay(speedDelay);
  }
  return true; // Return TRUE because it reached 100% brightness
}