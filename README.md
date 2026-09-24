# <img src="https://api.iconify.design/lucide:gamepad-2.svg?color=%238b949e" width="30" height="30" align="center" alt="Gamepad"> Whack-a-Bunny Keyboard

A keyboard-driven game where your **RGB keyboard becomes part of the game interface**.

The game was primarily designed around the **Logitech G PRO line on Windows**, while Linux uses **OpenRGB**, allowing many other compatible RGB keyboards to be used.

---

## <img src="https://upload.wikimedia.org/wikipedia/commons/8/87/Windows_logo_-_2021.svg" width="25" height="25" align="center" alt="Windows"> Windows Users — READ THIS FIRST

> [!CAUTION]
> **The following section applies ONLY to Windows users.**
>
> If you do not follow these steps, **keyboard integration will not work correctly.**

### <img src="./assets/LOGITECHGHUBLOGO.svg" width="24" height="24" align="center" alt="Logitech G HUB"> Logitech G HUB is required

On Windows, this game communicates with your Logitech keyboard through **Logitech G HUB**.

G HUB must therefore be:

- Installed
- Running
- Able to detect your keyboard

> [!WARNING]
> **Keep Logitech G HUB open in the background while playing.**
>
> Closing G HUB may prevent the game from communicating with your keyboard.

---

## <img src="https://api.iconify.design/lucide:file-cog.svg?color=%238b949e" width="23" height="23" align="center" alt="DLL"> Required Windows DLL

This repository contains:

```text
LogitechLedEnginesWrapper.dll
```

This file is required for communication between the game and Logitech G HUB.

It **MUST remain in the root directory of the project**.

### Correct

```text
whack-a-bunny-keyboard/
├── assets/
│   ├── LOGITECHGHUBLOGO.svg
│   └── OPENRGBLOGO.svg
├── LogitechLedEnginesWrapper.dll
├── README.md
└── ...
```

### Incorrect

```text
whack-a-bunny-keyboard/
├── dll/
│   └── LogitechLedEnginesWrapper.dll
├── README.md
└── ...
```

Do **NOT**:

- Move the DLL into another folder
- Rename it
- Delete it
- Hide it elsewhere in the project

The game expects:

```text
./LogitechLedEnginesWrapper.dll
```

---

## <img src="./assets/OPENRGBLOGO.svg" width="26" height="26" align="center" alt="OpenRGB"> Linux Support

Linux uses **OpenRGB** as the RGB backend instead of Logitech G HUB.

Because of this, Linux users are **not restricted to the Logitech G PRO line**.

You can use another RGB keyboard as long as:

- It is supported by OpenRGB
- OpenRGB detects it correctly
- The keyboard exposes the required lighting controls

> [!NOTE]
> Keyboard compatibility on Linux depends on **OpenRGB support for your specific device**.

---

# <img src="https://api.iconify.design/lucide:keyboard.svg?color=%238b949e" width="29" height="29" align="center" alt="Keyboard"> Controls

| Key | Action |
|:---:|---|
| `ENTER` | Start the game |
| `ENTER` | Retry after winning or losing |
| `TAB` | Pause / Resume |
| `ESC` | Exit the game |
| `F1` - `F5` | Lives indicator |
| `F9` | Pause combo counter |

---

## <img src="https://api.iconify.design/lucide:pause.svg?color=%23f0a020" width="23" height="23" align="center" alt="Pause"> Pause Indicator

Press:

```text
TAB
```

to pause the game.

When the game has been paused successfully:

> **Your entire keyboard will turn AMBER.**

This acts as the visual confirmation that the game is currently paused.

Press `TAB` again to resume.

---

# <img src="https://api.iconify.design/lucide:heart.svg?color=%23ff4d5a" width="28" height="28" align="center" alt="Lives"> Lives System

Your function keys act as the game's visual life indicator:

```text
F1    F2    F3    F4    F5
│     │     │     │     │
L1    L2    L3    L4    L5
```

The game uses the lighting of these keys to represent your remaining lives.

As lives are lost, the keyboard will visually reflect the change.

---

# <img src="https://api.iconify.design/lucide:gauge.svg?color=%238b949e" width="28" height="28" align="center" alt="Combo"> Combo Counter

The combo system can be paused using:

```text
F9
```

This pauses the **combo counter** independently from the main game pause control.

The main game itself is paused using:

```text
TAB
```

---

# <img src="https://api.iconify.design/lucide:list-checks.svg?color=%238b949e" width="28" height="28" align="center" alt="Checklist"> Windows Setup Checklist

Before launching the game on Windows, verify all of the following:

- [ ] Logitech G HUB is installed
- [ ] Logitech G HUB is running
- [ ] Your Logitech keyboard appears inside G HUB
- [ ] `LogitechLedEnginesWrapper.dll` exists
- [ ] `LogitechLedEnginesWrapper.dll` is in the project root
- [ ] The DLL has not been renamed
- [ ] Your keyboard RGB is working correctly in G HUB

If all checks pass, you're ready to launch the game.

---

# <img src="https://api.iconify.design/lucide:terminal.svg?color=%238b949e" width="28" height="28" align="center" alt="Terminal"> Quick Start

## <img src="https://upload.wikimedia.org/wikipedia/commons/8/87/Windows_logo_-_2021.svg" width="22" height="22" align="center" alt="Windows"> Windows

### 1. Install Logitech G HUB

Install and configure Logitech G HUB.

### 2. Connect your keyboard

Make sure your Logitech keyboard appears correctly inside G HUB.

### 3. Keep G HUB running

Do not close it while playing.

### 4. Check the DLL

Make sure this exists in the root of the project:

```text
LogitechLedEnginesWrapper.dll
```

### 5. Launch the game

Start the game normally.

### 6. Press ENTER

```text
ENTER
```

starts the game.

---

## <img src="./assets/OPENRGBLOGO.svg" width="23" height="23" align="center" alt="OpenRGB"> Linux / OpenRGB

### 1. Install OpenRGB

Install OpenRGB for your Linux distribution.

### 2. Check keyboard detection

Make sure your keyboard appears correctly inside OpenRGB.

### 3. Start OpenRGB

Ensure the RGB backend is available before launching the game.

### 4. Launch the game

Start the game normally.

### 5. Press ENTER

```text
ENTER
```

starts the game.

---

# <img src="https://api.iconify.design/lucide:lightbulb.svg?color=%23f0c040" width="28" height="28" align="center" alt="Lighting"> The Keyboard IS the Interface

The RGB effects are **not just decoration**.

Your keyboard is used by the game to communicate gameplay information directly to you.

This includes:

- Remaining lives
- Pause state
- Game state
- Key mapping
- Combo state
- Gameplay feedback
- Visual events

The intended experience therefore requires an RGB keyboard with working software support.

---

## <img src="./assets/LOGITECHGHUBLOGO.svg" width="24" height="24" align="center" alt="Logitech G HUB"> Windows Backend

```text
GAME
  │
  ▼
LogitechLedEnginesWrapper.dll
  │
  ▼
Logitech G HUB
  │
  ▼
Logitech RGB Keyboard
```

---

## <img src="./assets/OPENRGBLOGO.svg" width="24" height="24" align="center" alt="OpenRGB"> Linux Backend

```text
GAME
  │
  ▼
OpenRGB
  │
  ▼
Compatible RGB Keyboard
```

---

# <img src="https://api.iconify.design/lucide:triangle-alert.svg?color=%23f0a020" width="28" height="28" align="center" alt="Important"> Important

### Windows

Keep:

<img src="./assets/LOGITECHGHUBLOGO.svg" width="20" height="20" align="center" alt="Logitech G HUB"> **Logitech G HUB**

running while playing.

### Linux

Make sure:

<img src="./assets/OPENRGBLOGO.svg" width="20" height="20" align="center" alt="OpenRGB"> **OpenRGB**

can detect and communicate with your keyboard.

---

<p align="center">
  <img src="https://api.iconify.design/lucide:keyboard.svg?color=%238b949e" width="44" height="44" alt="Keyboard">
</p>

<h3 align="center">
  Your keyboard is the game interface.
</h3>

<p align="center">
  Press <code>ENTER</code> and start playing.
</p>
