# ⚙️ Installation Guide — Swing Trading System

Follow these steps to set up the system on your local machine.

## 🛠 Prerequisites

Ensure you have the following installed:
-   **Python 3.10 or higher**
-   **pip** (Python package manager)
-   **Internet connection** (for data fetching)

---

## 🚀 Setup Steps

### 1. **Clone the Repository**
```bash
git clone https://github.com/YOUR_USERNAME/swing-trading-system.git
cd swing-trading-system
```

### 2. **Create a Virtual Environment (Recommended)**
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

### 3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

---

## 🧪 Quick Test
Run the screener with default parameters to verify the setup:

```bash
python screener.py
```

If the system scans stocks and prints a "MARKET REGIME" section, you are ready for trading.
