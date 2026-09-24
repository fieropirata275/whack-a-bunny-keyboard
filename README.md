# <img src="https://api.iconify.design/lucide:gamepad-2.svg?color=%238b949e" width="30" height="30" align="center" alt="Gamepad"> Keyboard Game — Setup & Controls

> [!IMPORTANT]
> This game was designed primarily with the **Logitech G PRO line on Windows** in mind.
>
> On **Linux**, you can use essentially any compatible RGB keyboard, as the game uses **OpenRGB** as its backend.

---

## <img src="https://upload.wikimedia.org/wikipedia/commons/8/87/Windows_logo_-_2021.svg" width="25" height="25" align="center" alt="Windows"> Windows Users — READ THIS FIRST

> [!CAUTION]
> **The following section applies ONLY to Windows users.**
>
> If you do not follow these steps, **keyboard integration will not work correctly.**

### <img src="https://api.iconify.design/lucide:file-cog.svg?color=%238b949e" width="22" height="22" align="center" alt="DLL"> Required Logitech LED Wrapper

Inside this project you will find the following file:

```text
LogitechLedEnginesWrapper.dll
```

This file **MUST be located directly in the root directory of the project**.

### Correct

```text
YourGame/
├── LogitechLedEnginesWrapper.dll
├── game.exe
├── README.md
├── assets/
│   └── logitech-g.svg
└── ...
```

### Incorrect

```text
YourGame/
├── dll/
│   └── LogitechLedEnginesWrapper.dll
├── game.exe
└── README.md
```

Do **not**:

* Move it into another folder.
* Rename it.
* Hide it somewhere else in the project.
* Delete it.

The game uses `LogitechLedEnginesWrapper.dll` to communicate with your Logitech keyboard through **Logitech G HUB**.

---

## <img src="./assets/logitech-g.svg" width="24" height="24" align="center" alt="Logitech G"> Logitech G HUB Requirement

> [!WARNING]
> **Logitech G HUB must be installed AND running in the background while playing.**

The game communicates with your keyboard through G HUB in order to:

* Control the keyboard lighting.
* Map the correct physical keys.
* Display game states using RGB effects.
* Display lives.
* Indicate pause states.
* React to gameplay events.

If G HUB is closed, the game may be unable to communicate with your keyboard.

---

## <img src="https://cdn.simpleicons.org/linux/FCC624" width="27" height="27" align="center" alt="Linux"> Linux Support

Linux uses **OpenRGB** instead of Logitech G HUB.

<img src="https://api.iconify.design/lucide:rainbow.svg?color=%23ff4fd8" width="20" height="20" align="center" alt="RGB"> **OpenRGB** provides the RGB backend used by the game on Linux.

This means you are not restricted to the Logitech G PRO keyboard line.

As long as your keyboard is properly detected and supported by OpenRGB, it can potentially be used with the game.

---

# <img src="https://api.iconify.design/lucide:keyboard.svg?color=%238b949e" width="28" height="28" align="center" alt="Keyboard"> Controls

| Key         | Action                                         |
| ----------- | ---------------------------------------------- |
| `ENTER`     | Start the game / Retry after winning or losing |
| `TAB`       | Pause / Resume the game                        |
| `ESC`       | Exit the game                                  |
| `F1` – `F5` | Lives indicator                                |
| `F9`        | Pause combo counter                            |

---

### <img src="https://api.iconify.design/lucide:pause.svg?color=%23ffb020" width="21" height="21" align="center" alt="Pause"> Pause Indicator

When the game has been successfully paused using `TAB`:

> **Your entire keyboard will turn AMBER.**

This is the visual confirmation that the game is currently paused.

---

# <img src="https://api.iconify.design/lucide:heart.svg?color=%23ff4b55" width="27" height="27" align="center" alt="Lives"> Lives System

The function keys represent your remaining lives:

```text
F1    F2    F3    F4    F5
LIVE  LIVE  LIVE  LIVE  LIVE
```

The lighting on these keys is used by the game to visually communicate your current life count.

---

# <img src="https://api.iconify.design/lucide:list-checks.svg?color=%238b949e" width="27" height="27" align="center" alt="Checklist"> Windows Setup Checklist

Before launching the game on Windows, make sure:

* [ ] Logitech G HUB is installed.
* [ ] Logitech G HUB is running.
* [ ] Your Logitech keyboard is detected by G HUB.
* [ ] `LogitechLedEnginesWrapper.dll` exists.
* [ ] The DLL is located in the **root directory of the project**.
* [ ] The DLL has not been renamed.
* [ ] The game has permission to access the required files.

If all of the above are correct, you're ready to play.

---

# <img src="https://api.iconify.design/lucide:terminal.svg?color=%238b949e" width="27" height="27" align="center" alt="Terminal"> Quick Start

## <img src="https://upload.wikimedia.org/wikipedia/commons/8/87/Windows_logo_-_2021.svg" width="22" height="22" align="center" alt="Windows"> Windows

```text
1. Install Logitech G HUB
2. Connect your Logitech keyboard
3. Open Logitech G HUB
4. Make sure LogitechLedEnginesWrapper.dll is in the project root
5. Launch the game
6. Press ENTER
```

## <img src="https://cdn.simpleicons.org/linux/FCC624" width="22" height="22" align="center" alt="Linux"> Linux

```text
1. Install and configure OpenRGB
2. Make sure your keyboard is detected
3. Launch the game
4. Press ENTER
```

---

# <img src="https://api.iconify.design/lucide:triangle-alert.svg?color=%23ffb020" width="27" height="27" align="center" alt="Important"> Important

The RGB keyboard isn't just decoration.

**It is part of the game's interface.**

Your keyboard is used to communicate gameplay information such as:

* Lives
* Pause state
* Game events
* Key mapping
* Combo state
* Other visual feedback

So for the intended experience:

> **Keep your RGB software running and your keyboard connected.**

---

<p align="center">
  <img src="https://api.iconify.design/lucide:keyboard.svg?color=%238b949e" width="34" height="34" alt="Keyboard">
</p>

<p align="center">
  <strong>Your keyboard is the game interface.</strong>
</p>
