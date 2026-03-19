# 🧵 Cloth Simulation

A real-time interactive cloth physics simulation built with Python and Pygame. Grab, drag, rotate, and tear a cloth using your mouse — with wind, gravity, and turbulence controls.

---

## 📸 Preview

> A 55×35 grid cloth pinned at the top, reacting to gravity, wind, and mouse interaction in real time.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.7+
- Pygame

### Installation

```bash
# Clone the repo
git clone https://github.com/yourusername/cloth-simulation.git
cd cloth-simulation

# Install dependency
pip install pygame

# Run
python cloth_simulation.py
```

---

## 🎮 Controls

### Mouse

| Action | Result |
|---|---|
| `Left Click + Drag` (Hold mode) | Grabs all cloth points within the radius and drags them with you |
| Rotate cursor around grab centre | Rotates the grabbed cloth section to follow the cursor's arc |
| `Left Click + Drag` (Tear mode) | Cuts through cloth wherever the cursor passes |

### Keyboard

| Key | Action |
|---|---|
| `H` | Switch to **Hold** mode |
| `T` | Switch to **Tear** mode |
| `R` | Reset cloth to original state |
| `W` | Toggle wind on / off |
| `U` | Toggle turbulence (random gusts) |
| `↑` / `↓` | Increase / decrease gravity |
| `←` / `→` | Adjust wind direction & strength |
| `+` / `-` | Increase / decrease grab radius |
| `ESC` | Quit |

---

## ⚙️ Features

### Physics
- **Verlet integration** — stable, realistic cloth movement
- **Constraint solving** — 5 iterations per frame to maintain cloth structure
- **Auto-tear** — sticks break automatically when stretched beyond 2.8× their rest length
- **Gravity control** — adjustable from −1.5 (float upward) to +3.0 (heavy drop)

### Hold Mode
- Grabs **all points within the grab radius** at once — not just the nearest point
- Points follow the cursor in their **original formation** (polar offset preserved)
- **Rotation detection** — moving your cursor in an arc around the grab centre rotates the held cloth section to match
- Smooth **weight falloff** — points at the centre follow fully, edge points follow softly for a natural feel
- Grab radius is adjustable live with `+` / `-`

### Tear Mode
- Click and drag to **cut through** the cloth along your cursor path
- Cloth reacts physically after being torn — sections fall freely under gravity

### Simulations
- **Wind** — directional force applied per-frame, controlled with arrow keys
- **Turbulence** — randomised gusts layered on top of wind for organic movement
- **Negative gravity** — cloth floats upward, useful for balloon/flag effects

### Visual Feedback
- Cloth colour shifts **green → yellow → red** based on how stretched each segment is
- **Gold pins** mark the fixed anchor points at the top row
- Grab cursor shows the **influence radius ring** and spinning tick marks while dragging
- Tear cursor shows a **crosshair** symbol
- Wind direction shown as a **live arrow indicator** (top right)
- HUD displays current mode, gravity value, wind strength, and turbulence state

---

## 🏗️ Project Structure

```
cloth-simulation/
│
├── cloth_simulation.py   # Main simulation file
└── README.md
```

---

## 🔧 Configuration

At the top of `cloth_simulation.py` you can tweak these constants:

```python
COLS = 55              # Number of cloth columns
ROWS = 35              # Number of cloth rows
SPACING = 14           # Pixel distance between points
DAMPING = 0.98         # Velocity damping (lower = more drag)
CONSTRAINT_ITERATIONS = 5   # Physics solve iterations per frame
TEAR_DISTANCE = SPACING * 2.8  # Stretch ratio before a stick tears
```

---

## 🧠 How It Works

The cloth is modelled as a grid of **points** connected by **sticks**.

- Each **Point** stores its current and previous position. Velocity is derived implicitly each frame (`current − previous`), which is the core of Verlet integration.
- Each **Stick** tries to maintain its rest length by pushing its two endpoints apart or together. Running this multiple times per frame (constraint iterations) produces stable cloth.
- The **grab system** captures the polar coordinates (distance + angle) of every point within the grab radius at the moment of click. Each frame, those coordinates are rotated by the angle the cursor has swept around the grab centre, then translated to the new cursor position — giving both drag and rotation in one pass.
- **Tearing** works by deactivating any stick whose current length exceeds `TEAR_DISTANCE`.

---

## 📄 License

MIT — free to use, modify, and distribute.

---

## 🙌 Acknowledgements

Physics approach inspired by classic Verlet cloth simulations. Built entirely with [Pygame](https://www.pygame.org/).
