## LayConnector Overview

**LayConnector** is a lightweight Qt‑based desktop application that bridges live chat between TikTok and Twitch, with support for custom chat‑triggered actions.

- **Mirror chats**: forwards every TikTok comment into your Twitch channel.
- **Custom actions**: configure triggers (e.g. `!hello`) and multiple dynamic responses.
- **Easy setup**: guided wizard for first run, plus a GUI to add/edit actions.


---

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Actions](#actions)

---

## Installation

### Notice information for Windows

People who use Windows can download it directly from the releases tab.

### Prerequisites

- Python 3.8 or newer
- A valid Twitch OAuth token (see below)
- A Windows, macOS or Linux machine with GUI support

### Install Dependencies

```bash
pip install PySide6 TikTokLive twitchio
```

### Clone Repository

```bash
git clone https://github.com/vcmikuu/layconnector.git
cd layconnector
```

### Run

```bash
python main.py
```

On first start you’ll see the Setup Wizard; enter your TikTok username (without `@`), Twitch username, and paste your Twitch OAuth token.

---

## Configuration

LayConnector stores its settings in:

- **Windows:** `%APPDATA%/layconnector/config.json`  
- **Linux/macOS:** `~/.config/layconnector/config.json`  

### config.json Schema

```json
{
  "tiktok_username": "your_tiktok_name",
  "twitch_username": "your_twitch_name",
  "twitch_token": "oauth:abcd1234",
  "actions": [
    {
      "trigger": "!hello",
      "responses": ["Hello {username}!", "Welcome to the stream, {username}!"]
    }
    // more actions...
  ]
}
```

- **tiktok_username**: TikTok handle (no `@`).  
- **twitch_username**: Twitch channel name.  
- **twitch_token**: OAuth token with `chat:read chat:edit` scopes.  
- **actions**: Array of trigger/response objects.  

> **Tip**: Use the GUI **Settings** to add or edit actions without touching this file directly.

---

## Usage

### Launching

1. Run `python main.py`.  
2. If first run, fill in credentials via the Setup Wizard.  
3. On the main dashboard, click **Start** to connect both TikTok and Twitch.  

### Dashboard

- **Start**: Connects to TikTok Live and Twitch chat.  
- **Settings**: Opens the Actions manager.  
- **Exit**: Closes the application.  

All incoming TikTok comments will be relayed to your Twitch chat in the format:

```text
<username>: <comment text>
```

### Stopping

Simply close the window or click **Exit**; the background thread will terminate on app exit.

---

## Actions

Actions let you match chat messages against custom triggers and send automated responses.

### Adding an Action

1. Open **Settings**.  
2. Click **Add**.  
3. In **Trigger**, enter the exact prefix (e.g. `!joke`).  
4. In **Responses**, enter one or more semicolon‑separated messages, for example:

```text
This is a test text;This is another test text seperated
```

5. Click **OK**, then **Save & Close**.

### Editing / Deleting

- **Edit**: Select an action, click **Edit**, modify fields, then **OK**.  
- **Delete**: Select an action, click **Delete**.

### Placeholder Variables

| Variable      | Description                                |
|---------------|--------------------------------------------|
| `{username}`  | Name of the TikTok user who triggered it.  |
| `{userinput}` | The text after the trigger word in comment.|

#### Example

- **Trigger**: `!shoutout`  
- **Responses**:  
  - `Check out {userinput} at https://twitch.tv/{userinput}`  
  - `Huge shoutout to {userinput}!`  

When a viewer comments:

```text
!shoutout CoolStreamer
```

LayConnector will post in Twitch:

```text
Check out CoolStreamer at https://twitch.tv/CoolStreamer
Huge shoutout to CoolStreamer!
```


