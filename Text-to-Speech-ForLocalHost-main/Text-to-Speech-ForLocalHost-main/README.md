# Vocaly - AI Voice Generator

A minimal, modern local web application built with Django that converts text into realistic speech using `edge-tts`.

## Features

- **Realistic Voices**: Powered by `edge-tts` (Microsoft Edge's TTS API). NoAPI key required.
- **Customizable**: Choose between different voices (genders/accents) and speech speeds.
- **Modern UI**: Clean, responsive layout with glassmorphism design, dark mode toggle, and character count.
- **Local History**: Automatically saves your recent generated audio snippets locally in your browser.
- **AJAX Generation**: Generates voice seamlessly without page reloads.

## Setup Instructions

### Prerequisites

- Python 3.8+
- internet connection (for `edge-tts` to fetch voices from the remote API)

### 1. Clone/Navigate to the directory

If you haven't already, navigate to the project directory:

```bash
cd django_tts
```

### 2. Create a Virtual Environment (Optional but recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Apply Migrations (Not strictly needed for this app as it uses no DB models, but good practice for Django)

```bash
python manage.py migrate
```

### 5. Run the Local Development Server

```bash
python manage.py runserver
```

### 6. Usage

- Open your browser and navigate to `http://127.0.0.1:8000/`
- Type the text you want to convert to speech.
- Select your preferred voice and speed.
- Click "Generate Voice" and wait for the AI to process it.
- Listen to the playback or download the MP3 file using the "Download Audio" button.

> **Note**: The generated MP3 files are stored locally in the `media/tts_audio/` directory. You may clear them periodically if they take up too much space.
