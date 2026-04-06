# Wishing Jar

An interactive capacitive-touch device built with an ESP32 TTGO T-Display. The user rubs the outside of a glass jar to awaken it, speaks a wish into the lid, then taps the lid to send it. The TTGO's onboard screen glows yellow while rubbing, transitions to blue when the jar is ready, and bursts into random colors when the wish is granted. A companion Python visualizer on the laptop mirrors the lighting effects and plays synchronized audio.

---

## Demo

| State    | Screen color         | What's happening                                  |
_______________________________________________________________________________________
| Idle     | Off                  | Waiting for interaction                           |
| Rubbing  | Warm yellow flicker  | User rubs jar — must hold 3 continuous seconds    |
| Ready    | Steady blue pulse    | Jar is ready — user speaks wish into lid          |
| Granting | Random color flashes | Lid tapped — wish sent, returns to Ready after 3s |

---

## Hardware

### Components

1. ESP32 TTGO T-Display: Screen faces up into the jar base
2. Mini breadboard
3. Copper tape (conductive adhesive, ~1 inch wide): 5x, Touch interface on outside of jar
4. Jumper wires: 5x
5. Wide-mouth glass Mason jar
6. USB-C cable

### Pin Mapping

| ESP32 Pin | Touch Pin | Connected to |

| GPIO4 | T0 | Copper strip 1 (side) |
| GPIO2 | T2 | Copper strip 2 (side) |
| GPIO15 | T3 | Copper strip 3 (side) |
| GPIO13 | T4 | Copper strip 4 (side) |
| GPIO32 | T9 | Copper strip 5 (lid) |

---

## Software

### Repository Structure

```
TouchCapacity/
├── src/
│   └── wishing_jar.py      # Python laptop visualizer
│   └── wishing_jar.ino     # ESP32 Arduino sketch
├── audio/
│   ├── chime.wav           # Plays while rubbing (not included — see below)
│   ├── ready.wav           # Loops when jar turns blue
│   └── granted.wav         # One-shot burst when wish granted
├── platformio.ini
└── README.md
```

### ESP32 Firmware

#### Requirements

- [PlatformIO](https://platformio.org/)
- Board: TTGO T-Display (ESP32)
- Library: `TFT_eSPI` (install via Library Manager)

---

### Python Visualizer

#### Requirements

- Python 3.12 (pygame's mixer module is broken on Python 3.14)
- Libraries: `pyserial`, `pygame`

#### Installation

```bash
# Install Python 3.12 if needed
brew install python@3.12

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install pyserial pygame
```

#### Configuration

Before running, set your serial port in `src/wishing_jar.py`:

```python
SERIAL_PORT = "/dev/cu.usbserial-XXXX"   # Mac
# SERIAL_PORT = "COM3"                   # Windows
# SERIAL_PORT = "/dev/ttyUSB0"           # Linux
```

To find your port on Mac:

```bash
ls /dev/cu.*
```

Plug and unplug the TTGO — the entry that appears/disappears is your port. On Windows, check Device Manager under "Ports (COM & LPT)".

## How It Works

### State Machine

```
IDLE → (rub for 5 continuous seconds) → RUBBING → READY → (tap lid) → GRANTING → READY
                                           ↑ touch breaks → IDLE
```

The ESP32 manages all state transitions locally and sends state updates over USB serial to the laptop. The Python visualizer reads this stream and generates corresponding visuals and audio.
