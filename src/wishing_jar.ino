#include <TFT_eSPI.h>
#include <SPI.h>

// ============================================================
//  WISHING JAR — ESP32 TTGO T-Display
//  All lighting via TFT screen. No LEDs.
//
//  State flow:
//    IDLE        Screen is black/off
//    RUBBING     Screen glows warm yellow ONLY while touch active
//                Must hold touch for 3 continuous seconds
//    READY       Screen glows steady blue — jar ready for wish
//    GRANTING    Lid tapped — random color flashes for 3s
//                then returns to READY
// ============================================================

TFT_eSPI tft = TFT_eSPI();

// ── PINS ────────────────────────────────────────────────────
#define TOUCH_RUB_1 T5 // GPIO12 — side strip 1
#define TOUCH_RUB_2 T2 // GPIO2  — side strip 2
#define TOUCH_RUB_3 T3 // GPIO15 — side strip 3
#define TOUCH_RUB_4 T4 // GPIO13 — side strip 4
#define TOUCH_LID T9   // GPIO17 — lid strip

// ── TUNING ──────────────────────────────────────────────────
#define TOUCH_THRESH 40        // lower = more sensitive
#define RUB_HOLD_MS 6000       // ms of continuous touch to reach READY
#define GRANT_DURATION_MS 7000 // ms of color flashes after lid tap

// ── STATES ──────────────────────────────────────────────────
enum State
{
  IDLE,
  RUBBING,
  READY,
  GRANTING
};
State currentState = IDLE;

unsigned long rubStartTime = 0;   // when continuous rub began
unsigned long grantStartTime = 0; // when lid was tapped

// ── COLOR HELPER ────────────────────────────────────────────
uint16_t rgb(uint8_t r, uint8_t g, uint8_t b)
{
  return tft.color565(r, g, b);
}

// Scale brightness 0.0–1.0
uint16_t dimRGB(uint8_t r, uint8_t g, uint8_t b, float br)
{
  br = constrain(br, 0.0f, 1.0f);
  return tft.color565(
      (uint8_t)(r * br),
      (uint8_t)(g * br),
      (uint8_t)(b * br));
}

// ── SETUP ───────────────────────────────────────────────────
void setup()
{
  Serial.begin(115200);

  tft.init();
  tft.setRotation(1); // landscape, screen faces up into jar
  tft.fillScreen(TFT_BLACK);

  // Brief splash
  tft.setTextDatum(MC_DATUM);
  tft.setTextSize(2);
  tft.setTextColor(rgb(255, 200, 30), TFT_BLACK);
  tft.drawString("Wishing Jar", tft.width() / 2, tft.height() / 2);
  delay(1200);
  tft.fillScreen(TFT_BLACK);
  ledcWrite(0, 255);
}

// ── MAIN LOOP ───────────────────────────────────────────────
void loop()
{
  unsigned long now = millis();

  bool rubbed = (touchRead(TOUCH_RUB_1) < TOUCH_THRESH ||
                 touchRead(TOUCH_RUB_2) < TOUCH_THRESH ||
                 touchRead(TOUCH_RUB_3) < TOUCH_THRESH ||
                 touchRead(TOUCH_RUB_4) < TOUCH_THRESH);
  bool lidTapped = (touchRead(TOUCH_LID) < TOUCH_THRESH);

  // ── State transitions ──────────────────────────────────────

  // IDLE: start rubbing timer when first touched
  if (currentState == IDLE)
  {
    if (rubbed)
    {
      currentState = RUBBING;
      rubStartTime = now;
    }
  }

  // RUBBING: track continuous touch — reset timer if touch breaks
  else if (currentState == RUBBING)
  {
    if (!rubbed)
    {
      // Touch broke — reset back to IDLE, screen off
      currentState = IDLE;
      rubStartTime = 0;
    }
    else if (now - rubStartTime >= RUB_HOLD_MS)
    {
      // Held for 3 seconds — jar is ready
      currentState = READY;
    }
  }

  // READY: wait for lid tap
  else if (currentState == READY)
  {
    if (lidTapped)
    {
      currentState = GRANTING;
      grantStartTime = now;
    }
  }

  // GRANTING: flash for 3 seconds then return to READY
  else if (currentState == GRANTING)
  {
    if (now - grantStartTime >= GRANT_DURATION_MS)
    {
      currentState = IDLE; // back to listening, not IDLE
    }
  }

  // ── Serial output to laptop ────────────────────────────────
  // Format: STATE,RUBBED,LID
  // STATE: 0=IDLE 1=RUBBING 2=READY 3=GRANTING
  Serial.print(currentState);
  Serial.print(",");
  Serial.print(rubbed ? 1 : 0);
  Serial.print(",");
  Serial.println(lidTapped ? 1 : 0);

  // ── Update display ─────────────────────────────────────────
  updateScreen(currentState, rubbed, now);

  delay(20);
}

// ── SCREEN RENDERING ────────────────────────────────────────
void updateScreen(State s, bool rubbed, unsigned long now)
{

  switch (s)
  {

  case IDLE:
    // Screen off — no light
    tft.fillScreen(TFT_BLACK);
    break;

  case RUBBING:
  {
    if (rubbed)
    {
      // Warm yellow flicker while actively touching
      float brightness = random(60, 100) / 100.0f;
      // Alternate between yellow and amber for organic flicker
      bool amber = (random(3) == 0);
      if (amber)
      {
        tft.fillScreen(dimRGB(255, 140, 0, brightness)); // amber
      }
      else
      {
        tft.fillScreen(dimRGB(255, 200, 30, brightness)); // warm yellow
      }

      // Progress bar at bottom showing how close to 3 seconds
      unsigned long held = now - rubStartTime;
      int pct = constrain((int)(held * tft.width() / RUB_HOLD_MS), 0, tft.width());
      tft.fillRect(0, tft.height() - 6, pct, 6, rgb(255, 255, 200));
    }
    else
    {
      tft.fillScreen(TFT_BLACK);
    }
    break;
  }

  case READY:
  {
    // Calm blue pulse — gentle sine wave brightness
    float pulse = (sin(now / 1400.0f * PI) + 1.0f) / 2.0f;
    float brightness = 0.65f + pulse * 0.35f;
    tft.fillScreen(dimRGB(30, 110, 255, brightness));

    // Small label
    tft.setTextDatum(BC_DATUM);
    tft.setTextSize(1);
    tft.setTextColor(rgb(180, 210, 255));
    tft.drawString("speak your wish", tft.width() / 2, tft.height() - 6);
    break;
  }

  case GRANTING:
  {
    // Random full-screen color flash each frame
    uint8_t r = random(50, 255);
    uint8_t g = random(50, 255);
    uint8_t b = random(50, 255);
    tft.fillScreen(rgb(r, g, b));

    // Countdown bar
    unsigned long elapsed = now - grantStartTime;
    int remaining = tft.width() - constrain(
                                      (int)(elapsed * tft.width() / GRANT_DURATION_MS), 0, tft.width());
    tft.fillRect(0, tft.height() - 6, remaining, 6, TFT_WHITE);
    break;
  }
  }
}
