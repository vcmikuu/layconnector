## LayConnector Overview

**LayConnector** is a lightweight Qt‑based desktop application that bridges live chat between TikTok and Twitch, with support for custom chat‑triggered actions and DumbRequestManager integration.

- **Mirror chats**: forwards every TikTok comment into your Twitch channel.
- **Custom actions**: configure triggers (e.g. `!hello`) and multiple dynamic responses.
- **DumbRequestManager integration**: interact with the song request system directly from TikTok.
- **Enhanced GUI**: improved action management with tabbed interface and better feedback.
- **Easy setup**: guided wizard for first run, plus a GUI to add/edit actions.


---

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Actions](#actions)
- [DumbRequestManager Integration](#dumbrequestmanager-integration)

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

Actions let you match chat messages against custom triggers and send automated responses or DumbRequestManager commands.

### Adding an Action

1. Open **Settings**.
2. Go to the **Actions** tab.  
3. Click **Add Action**.  
4. In **Trigger**, enter the exact prefix (e.g. `!joke`).  
5. In the **Standard Responses** tab, add one or more response messages by clicking the **Add** button.
6. Alternatively, switch to the **DumbRequestManager Integration** tab to set up mod actions (requires mod to be enabled in settings first).
7. Click **OK**, then **Save & Close**.

### Editing / Deleting

- **Edit**: Select an action, click **Edit Action**, modify fields, then **OK**.  
- **Delete**: Select an action, click **Delete Action**.

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

---

## DumbRequestManager Integration

LayConnector now supports integration with DumbRequestManager, a Beat Saber mod that allows for song requests and queue management.

### Setting up DumbRequestManager

1. First, you need to install DumbRequestManager in your Beat Saber installation.
2. Download and install from: [https://github.com/TheBlackParrot/DumbRequestManager](https://github.com/TheBlackParrot/DumbRequestManager)
3. Follow the mod installation instructions on the GitHub page.

### Enabling the Integration

1. Open **Settings** in LayConnector.
2. Switch to the **DumbRequestManager** tab.
3. Check the **Enable DumbRequestManager integration** box.
4. Verify the HTTP and WebSocket URLs (default: http://localhost:13337 and ws://localhost:13338).
5. Click **Test Connection** to verify that LayConnector can communicate with the mod.
6. Click **Save & Close** when done.

### Available DumbRequestManager Actions

When creating or editing an action, you can enable DumbRequestManager integration and choose from various action types:

| Action Type | Description |
|-------------|-------------|
| Query Map | Searches for a map by key/ID |
| Add to Queue | Adds a song to the request queue |
| Check Queue | Shows the current queue status |
| Clear Queue | Empties the entire queue |
| Open/Close Queue | Controls whether requests are accepted |
| Move in Queue | Repositions a song within the queue |
| Shuffle Queue | Randomizes the order of songs |
| View History | Shows recently played songs |

### Example Use Cases

1. **Song Requests from TikTok**:
   - Set up a trigger like `!bsr`
   - Enable DumbRequestManager integration
   - Choose "Add to Queue" action type
   - When viewers type `!bsr 1a2b3c`, the song will be added to the Beat Saber queue

2. **Queue Management**:
   - Create triggers like `!queue`, `!clear`, `!open`, `!close`
   - Each can perform different queue management functions

### Important Notes

- DumbRequestManager must be running in Beat Saber for the integration to work
- The integration is disabled by default and must be explicitly enabled
- Actions using the integration will not function if DumbRequestManager is disabled
- The Beat Saber game must be running with the mod installed for the API to work


