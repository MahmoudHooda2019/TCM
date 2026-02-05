## T C M – Telegram Channel Migrator

**TCM** is a command‑line tool that helps you migrate messages between Telegram channels using the Telegram API.  
It supports:
- **Text only** messages
- **Media only** (photos/documents)
- **Media + caption** (the program now copies the caption correctly)
- Resuming interrupted transfers using a `resume.txt` log

---

### Requirements

- **Python 3.10+**
- `pip` and a working internet connection
- Telegram **API ID** and **API Hash** from [my.telegram.org](https://my.telegram.org)
- Dependencies from `requirements.txt`:
  - `telethon`
  - `InquirerPy`
  - `colorama`

---

### Setup

- **Create & activate a virtual environment (recommended)**  
  Windows (PowerShell):

```bash
cd TCM
python -m venv .venv
.venv\Scripts\activate
```

- **Install dependencies**  

```bash
pip install -r requirements.txt
```

---

### Usage

1. **Run the main program**

```bash
python main.py
```

2. **Follow the steps in the terminal**
   - Enter your **API ID** and **API Hash**
   - Enter the **source channel** link
   - Enter the **destination channel** link
   - Choose **content type**:
     - `all` – text + media
     - `text` – text messages only
     - `media` – photos / documents (with caption if present)
   - Choose the delay between messages (to avoid spam limits)
   - Confirm, then wait for the transfer to finish

3. **Resume file**
   - All messages (pending / success / failed) are logged in `resume.txt`
   - If the script stops, you can rerun it and it will **skip** already‑successful messages.

---

### Project Structure

- `main.py` – Entry point; collects user input and starts the transfer.
- `transfer.py` – Core logic for migrating messages between channels.
- `ui.py` – Banner and colored terminal output helpers.
- `utils.py` – Handling of the `resume.txt` file and transfer state.
- `config.py` – Simple runtime configuration values used by the transfer code.

---

### Notes

- Make sure the Telegram account you use has access to both the **source** and **destination** channels.
- Do **not** share the `TCM_session` file or any session data with anyone.
