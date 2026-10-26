# Vistara Vision — Assistive Vision & Spatial Memory for the Visually Impaired

An assistive AI vision system that transforms a standard camera and laptop/desktop into an intelligent auditory guide for visually impaired users.

---

## 🌟 Key Features

### 1. 💵 Multi-Modal Indian Banknote Recognition & Continuous Counting
- **Dual-Sided Matching**: Full Mahatma Gandhi New Series reference templates for ₹10, ₹20, ₹50, ₹100, ₹200, and ₹500 (both Gandhi front and cultural heritage motif backs).
- **Multi-Modal Ensemble Decision Engine**:
  - High-precision ORB keypoint feature matching.
  - Native Windows Media OCR for numeral verification (`10`, `20`, `50`, `100`, `200`, `500`), enabling recognition of folded, crumpled, or angled notes.
  - Dominant color profile verification (fluorescent blue for ₹50, stone gray for ₹500, lavender for ₹100, etc.).
- **Smart Counting Session**:
  - Running session totals with hands-free **Auto-Count mode** (`X`).
  - **Undo Note** (`U`) to remove misidentified or accidentally scanned notes.
  - **Session Breakdown** (`Breakdown` button or API) detailing total denomination counts (e.g. *“Total 250 rupees across 3 notes: two 100 rupee notes, one 50 rupee note”*).

### 2. 📍 Spatial Memory & Proximity ("What Left Where")
- **Clock-Face Direction Guidance**:
  - Objects are reported using natural spatial clock positions: `10 o'clock` (left), `12 o'clock` (directly ahead), `2 o'clock` (right).
- **Proximity Depth Awareness**:
  - Estimates object distance into tactile bands: `right in front of you` (close), `nearby` (arm's length), and `further away` (table edge).
- **Targeted Belongings Search**:
  - Ask *"Where is my phone?"* or *"Where are my keys?"* via the search bar or quick tags (`[🔍 Phone]`, `[🔍 Keys]`, `[🔍 Wallet]`).
- **Departure Audit & Auto-Watch**:
  - Press `R` upon arrival to remember table belongings.
  - Press `L` when leaving: audits table state, announcing both what was safely packed and what was left behind.
  - **Auto-Watch**: If the user leaves the camera frame without picking up their belongings, an auditory alarm warns them before they walk away.

### 3. 📖 High-Speed Offline Text Reader (OCR)
- Uses native Windows Media OCR (`winrt-Windows.Media.Ocr`).
- Runs in **~40ms on CPU** without internet connection or external binaries.
- High-contrast CLAHE preprocessing reads medicine boxes, packaging, letters, books, and bills.

### 4. 🎨 Assistive Color Identification
- Recognizes 16 natural color shades with luminance and saturation modifiers (e.g. Navy Blue, Sky Blue, Dark Red, Beige/Cream, Stone Gray).
- Spoken output in both English and Hindi with color swatches and hexadecimal values.

### 5. 🧠 Few-Shot Teachable Machine
- Instantly learn any custom personal item (e.g., custom keychain, earphone case, water bottle) in 2 seconds.
- Stores visual embeddings locally and matches them dynamically in real-time alongside YOLOv8.

### 6. 🌐 Modern Web Dashboard & Mobile Streamer
- Real-time cyber/glassmorphism web interface with dark mode and tactile feedback.
- Accessible locally or over LAN via HTTPS (`https://localhost:5000` or `https://<ip>:5000`).
- Mobile camera streamer at `/cam` turns any iPhone or Android phone into a wireless wearable camera.

### 7. 🗣️ Bilingual Voice Engine
- Seamlessly toggle between natural **English** and **Hindi** (`H`).
- Works completely offline with Windows SAPI / pyttsx3 and cached natural voices.

---

## ⌨️ Controls & Shortcuts

All controls work globally (without needing to focus the application window) or through the Web Dashboard:

| Key | Numpad | Action | Description |
|---|---|---|---|
| **C** | 1 | Check Currency | Identify banknote denomination and add to running total |
| **X** | – | Auto-Count Cash | Continuous hands-free banknote counting mode |
| **U** | – | Undo Note | Undo the last added banknote from session total |
| **O** | 8 | Read Text (OCR) | High-speed offline text reading for packaging and labels |
| **K** | 9 | Identify Color | Spoken color identification (English & Hindi) |
| **T** | 7 | Teach Object | Instant few-shot learning for custom personal items |
| **R** | 2 | Remember Items | Snapshot personal belongings placed on the table |
| **L** | 3 | Leaving Check | Check table before walking away; audits forgotten items |
| **D** | 4 | Describe Scene | Describes items in front with clock direction and distance |
| **W** | 5 | Where was my... | Answers when and where items were last seen |
| **H** | 6 | Switch Language | Toggle bilingual voice between English and Hindi |
| **F1** | 0 | Audio Help | Spoken tutorial of all keyboard shortcuts |
| **Esc** | – | Quit | Gracefully shut down Vistara Vision |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+ on Windows 10/11
- Webcam (built-in, USB, or smartphone camera via `/cam`)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Shivamborn2shine/Eyes-for-blind.git
   cd Eyes-for-blind
   ```

2. **Create and activate a virtual environment:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Run Vistara Vision:**
   ```powershell
   python main.py
   ```
   Or double-click `run.bat`.

5. **Open Dashboard:**
   Visit `https://localhost:5000` in your browser. (Accept the self-signed SSL certificate on first visit).

---

## 📁 Repository Structure

```
├── main.py                     # Main coordinator, worker threads, and hotkeys
├── config.py                   # Configuration options, paths, and thresholds
├── requirements.txt            # Python dependencies
├── run.bat                     # Windows one-click batch launcher
├── yolov8n.pt                  # YOLOv8 nano object detection weights
├── vistara/
│   ├── camera.py               # Video capture & remote smartphone frame receiver
│   ├── color.py                # 16-shade assistive color identifier
│   ├── currency.py             # Multi-modal banknote recognition engine
│   ├── detector.py             # YOLOv8 object detector with multi-frame voting
│   ├── hotkeys.py              # Global keyboard & numpad listeners
│   ├── i18n.py                 # Bilingual translation engine (English & Hindi)
│   ├── memory.py               # Spatial clock direction & proximity memory
│   ├── ocr.py                  # Windows Media OCR high-speed text reader
│   ├── screen_source.py        # Desktop screen source option
│   ├── speech.py               # Speech synthesizer with natural Hindi/English TTS
│   ├── teachable.py            # Few-shot visual feature learning model
│   └── web.py                  # Flask HTTPS web dashboard and REST API
├── web/
│   └── templates/
│       ├── index.html          # Cyber/glassmorphism assistive dashboard
│       └── cam.html            # Mobile smartphone camera streaming client
├── tools/
│   ├── capture_currency.py     # Reference banknote capture tool
│   └── train_currency.py       # Custom classifier training script
└── data/
    └── currency_refs/          # High-resolution dual-sided banknote references
```

---

## 🛡️ License & Acknowledgments
Built with ❤️ for accessibility, independent living, and assistive technology.
