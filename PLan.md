Absolutely. Since you're starting from essentially zero with this type of Linux desktop development, I’d treat this as a **small real product**, not just a GNOME extension script.

Below is a development requirements document you can use as the project's blueprint.

# Network Monitor for Ubuntu — Development Requirements Document

**Project name:** `NetMonitor`
**Target platform:** Ubuntu + GNOME Shell
**Primary data source:** NetHogs
**Initial implementation:** Python + GJS
**Architecture:** GNOME Shell Extension + User-level Monitoring Agent
**Version:** MVP v1.0

---

## 1. Product Goal

Build a lightweight Ubuntu top-bar network monitor that continuously displays:

```text
↓ 8.42 MB/s   ↑ 1.21 MB/s
```

and, when clicked, provides a detailed list of applications/processes consuming network bandwidth.

Example:

```text
┌─────────────────────────────────────┐
│ Network Monitor                     │
│                                     │
│       ↓ 8.42 MB/s   ↑ 1.21 MB/s    │
│                                     │
│ Applications                        │
│                                     │
│ 🌐 Chrome             5.21 MB/s     │
│    ↓ 4.82 MB/s  ↑ 0.39 MB/s        │
│                                     │
│ 🐳 Docker             1.82 MB/s     │
│    ↓ 1.42 MB/s  ↑ 0.40 MB/s        │
│                                     │
│ 📝 VS Code             0.91 MB/s     │
│    ↓ 0.71 MB/s  ↑ 0.20 MB/s        │
└─────────────────────────────────────┘
```

The user should also be able to select a process and terminate it.

---

# 2. Core Product Requirements

## 2.1 Top-bar indicator

The extension must display:

* Download speed
* Upload speed
* Combined network activity
* Connection/status state

Example:

```text
↓ 12.4 MB/s ↑ 2.3 MB/s
```

When there is no traffic:

```text
↓ 0 B/s ↑ 0 B/s
```

---

# 3. Detailed Dropdown

Clicking the indicator opens the monitor.

The dropdown should contain:

### Header

```text
Network Monitor

↓ 12.4 MB/s
↑ 2.3 MB/s
```

### Process list

Each process:

```text
Chrome
↓ 8.2 MB/s ↑ 1.1 MB/s
```

The list should be sorted by total bandwidth by default.

---

# 4. Process Information

Internally, every process should have information similar to:

```json
{
  "pid": 12345,
  "name": "chrome",
  "command": "/usr/bin/google-chrome",
  "download": 8200000,
  "upload": 1100000,
  "total": 9300000
}
```

Possible future fields:

```text
PID
Process name
Executable
User
Download speed
Upload speed
Total speed
Connection count
Remote addresses
```

---

# 5. Process Actions

Right-clicking a process should provide:

```text
Chrome
──────────────
Details
Kill Process
Force Kill
```

### Kill Process

Send:

```text
SIGTERM
```

### Force Kill

Send:

```text
SIGKILL
```

The backend must validate the PID before performing the operation.

---

# 6. Recommended Architecture

This is the most important part.

**Do not put everything inside the GNOME extension.**

Use two components:

```text
                 Ubuntu
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
 GNOME Shell Extension    Monitoring Agent
       GJS                     Python
        │                       │
        └───────────┬───────────┘
                    │
              Unix Socket
                    │
                    ▼
                 NetHogs
```

### Component A — GNOME Extension

Responsible for:

* Top-bar UI
* Dropdown
* Process list
* User interaction
* Kill-process request
* Settings UI

### Component B — Monitoring Agent

Responsible for:

* Starting NetHogs
* Reading NetHogs output
* Parsing data
* Calculating speeds
* Maintaining process state
* Providing API
* Killing processes
* Handling permissions

This separation will save you a **huge amount of pain later**.

---

# 7. Technology Stack

## Desktop UI

### GNOME Shell Extension

Use:

**GJS / JavaScript**

Why?

GNOME Shell extensions are built around JavaScript and GNOME's GObject-based APIs.

You'll interact with things like:

```text
Panel
PopupMenu
St.Label
St.Icon
Clutter
Gio
GLib
```

---

# 8. Backend

For the first version:

### Python 3

Use Python because:

* easy to learn
* excellent process management
* easy JSON handling
* easy Unix sockets
* easy subprocess management
* quick development
* NetHogs integration is straightforward

Later, if performance becomes important, you could rewrite the agent in Rust.

**Don't start with Rust.**

You're trying to build a product, not learn five technologies simultaneously.

---

# 9. Network Monitoring

### NetHogs

NetHogs remains your initial monitoring engine.

Your agent launches it and consumes its output.

Conceptually:

```text
NetHogs
   ↓
raw output
   ↓
Python parser
   ↓
normalized data
   ↓
Unix socket
   ↓
GNOME extension
```

---

# 10. IPC — Communication

Use:

### Unix Domain Socket

For example:

```text
$XDG_RUNTIME_DIR/netmonitor.sock
```

The extension connects to it.

Example request:

```json
{
  "action": "get_stats"
}
```

Response:

```json
{
  "timestamp": 1725440000,
  "total": {
    "download": 12400000,
    "upload": 2100000
  },
  "processes": [
    {
      "pid": 1234,
      "name": "chrome",
      "download": 7200000,
      "upload": 600000
    }
  ]
}
```

---

# 11. API Design

Even though this is a local application, design the agent like a proper service.

### `GET_STATS`

Returns current statistics.

### `GET_PROCESSES`

Returns process list.

### `GET_PROCESS`

Returns information about a specific process.

### `KILL_PROCESS`

Terminates a process.

### `FORCE_KILL_PROCESS`

Force terminates a process.

### `PING`

Checks whether the agent is alive.

Example:

```json
{
  "action": "ping"
}
```

Response:

```json
{
  "status": "ok"
}
```

---

# 12. Agent Project Structure

I'd start with:

```text
netmonitor/
│
├── agent/
│   ├── main.py
│   ├── server.py
│   ├── nethogs.py
│   ├── parser.py
│   ├── process_manager.py
│   ├── models.py
│   ├── config.py
│   └── logger.py
│
├── extension/
│   ├── extension.js
│   ├── indicator.js
│   ├── menu.js
│   ├── processRow.js
│   ├── client.js
│   ├── prefs.js
│   ├── stylesheet.css
│   └── metadata.json
│
├── systemd/
│   └── netmonitor.service
│
├── tests/
│   ├── test_parser.py
│   ├── test_process.py
│   └── test_api.py
│
├── docs/
│   ├── architecture.md
│   ├── api.md
│   └── development.md
│
├── README.md
└── LICENSE
```

---

# 13. Responsibilities of Each File

### `nethogs.py`

Responsible for launching NetHogs.

```text
start()
stop()
restart()
read()
```

---

### `parser.py`

Converts NetHogs output into your internal format.

```text
raw NetHogs
     ↓
parser
     ↓
ProcessStats
```

---

### `models.py`

Defines your data structures.

For example:

```text
ProcessStats
NetworkStats
NetworkSnapshot
```

---

### `process_manager.py`

Responsible for:

```text
find process
validate PID
SIGTERM
SIGKILL
process existence
```

---

### `server.py`

Unix socket server.

Responsible for:

```text
receive request
validate request
call appropriate service
return JSON
```

---

### `main.py`

Application entry point.

```text
start agent
 ↓
start NetHogs
 ↓
start socket server
 ↓
monitor continuously
```

---

# 14. GNOME Extension Structure

The extension should be similarly modular.

```text
extension/
│
├── extension.js
├── indicator.js
├── menu.js
├── processRow.js
├── client.js
├── prefs.js
├── stylesheet.css
└── metadata.json
```

### `extension.js`

Lifecycle:

```text
enable()
disable()
```

---

### `indicator.js`

Top bar:

```text
↓ 8.4 MB/s ↑ 1.2 MB/s
```

---

### `menu.js`

Dropdown.

---

### `processRow.js`

Individual process UI.

---

### `client.js`

Communication with Python agent.

---

### `prefs.js`

Settings UI.

---

# 15. Systemd Service

The backend should run automatically.

Create:

```text
netmonitor.service
```

under the user's systemd configuration.

Conceptually:

```text
login
  ↓
systemd user service
  ↓
netmonitor-agent
  ↓
NetHogs
```

The user shouldn't have to manually execute:

```bash
python main.py
```

every time Ubuntu starts.

---

# 16. Startup Requirements

On login:

```text
Ubuntu login
     ↓
systemd
     ↓
NetMonitor Agent
     ↓
NetHogs
     ↓
GNOME Extension
```

The extension should gracefully handle the agent not being available.

For example:

```text
Network Monitor
────────────────────

Agent unavailable

Retry
```

rather than crashing GNOME Shell.

---

# 17. Error Handling

You absolutely need this.

Possible situations:

### NetHogs isn't installed

Display:

```text
NetHogs not found
```

### NetHogs exits

Agent should attempt restart.

### Socket unavailable

Extension displays:

```text
Connecting...
```

### Permission denied

Display:

```text
Network monitoring requires additional permissions.
```

### Process disappeared

Don't show an error.

Simply remove it from the list.

### Invalid PID

Reject the operation.

---

# 18. Security Requirements

This application will have the ability to kill processes, so security matters.

Never accept something like:

```text
{"command":"kill 1234; rm -rf ~"}
```

Your API should use structured commands:

```json
{
  "action": "kill_process",
  "pid": 1234
}
```

Then validate:

```text
pid is integer
pid > 0
process exists
```

Never pass user-controlled strings directly into:

```text
shell=True
```

Avoid shell execution entirely where possible.

---

# 19. Permissions Architecture

There are two separate problems:

### Monitoring

Can the agent see network traffic?

### Process management

Can it terminate the process?

Don't automatically solve both using root privileges.

Start with the least privilege possible.

If certain operations require elevated privileges, isolate those operations.

---

# 20. UI Requirements

Keep the UI extremely lightweight.

Top bar:

```text
↓ 12.4 MB/s ↑ 2.1 MB/s
```

Dropdown:

```text
Network Monitor

12.4 MB/s ↓
2.1 MB/s ↑

Processes
────────────────

Chrome
↓ 7.2 MB/s ↑ 0.6 MB/s

Docker
↓ 1.6 MB/s ↑ 0.5 MB/s

VS Code
↓ 1.1 MB/s ↑ 0.3 MB/s
```

Don't turn the first version into a giant dashboard.

---

# 21. Sorting

Default:

```text
Total bandwidth ↓
```

Later:

```text
Download ↓
Upload ↓
Name A-Z
```

---

# 22. Process Icons

Eventually, detect the application's icon.

For example:

```text
🌐 Chrome
🐳 Docker
📝 VS Code
```

But don't make icon detection part of the first prototype.

Get network monitoring working first.

---

# 23. Performance Requirements

The extension should have minimal CPU usage.

Target:

```text
Agent:
< 1–2% CPU under normal operation

GNOME Extension:
negligible CPU when menu closed
```

Don't constantly rebuild the entire UI.

Use incremental updates.

---

# 24. Update Frequency

Start with:

```text
1 second
```

Later allow:

```text
500 ms
1 second
2 seconds
5 seconds
```

For MVP, **1 second is enough**.

---

# 25. State Model

The agent should maintain something like:

```text
NetworkState

timestamp
total_download
total_upload

processes[]
```

Every sampling interval:

```text
NetHogs
   ↓
snapshot
   ↓
normalize
   ↓
state
   ↓
extension
```

---

# 26. Important Concept: Speed vs Total Bytes

Be careful here.

NetHogs may provide traffic rates or byte counters depending on how you're consuming it.

Your UI needs:

```text
MB/s
```

not:

```text
MB total
```

If necessary, calculate:

```text
speed = (bytes_now - bytes_previous) / elapsed_time
```

For example:

```text
previous = 100 MB
current  = 110 MB
elapsed  = 2 sec

speed = 10 MB / 2
      = 5 MB/s
```

This should be handled by the backend, not the GNOME UI.

---

# 27. MVP Scope

Your first usable version should contain **only**:

### Must have

* GNOME top-bar indicator
* Download speed
* Upload speed
* NetHogs integration
* Process list
* Process bandwidth
* Unix socket communication
* Automatic agent startup
* Kill process
* Basic error handling

### Don't build yet

* Historical graphs
* Database
* Cloud synchronization
* Notifications
* Network history
* Remote monitoring
* eBPF
* fancy animations
* advanced preferences
* bandwidth limiting

Those are version 2+ features.

---

# 28. Development Roadmap

I'd build it in **10 milestones**.

## Milestone 1 — Environment

Install/configure:

```text
Python 3
NetHogs
GNOME Shell extension development tools
Git
VS Code
```

Verify:

```bash
nethogs
```

works correctly.

---

## Milestone 2 — NetHogs Integration

Create:

```text
agent/nethogs.py
```

Successfully launch NetHogs and read its output.

Goal:

```text
NetHogs
   ↓
Python
```

Nothing else.

---

## Milestone 3 — Parser

Convert NetHogs output:

```text
raw text
```

into:

```json
{
  "pid": 1234,
  "name": "chrome",
  "download": 5000000,
  "upload": 400000
}
```

Write unit tests.

---

## Milestone 4 — Network State Engine

Create:

```text
NetworkState
```

Calculate:

```text
total upload
total download
per-process upload
per-process download
```

Now you have the **actual monitoring engine**.

---

## Milestone 5 — Unix Socket API

Create:

```text
netmonitor.sock
```

Test it using a Python client.

Goal:

```text
client
 ↓
socket
 ↓
agent
 ↓
JSON
```

---

## Milestone 6 — Basic GNOME Extension

Create the simplest possible extension:

```text
Network: ↓ 0 B/s ↑ 0 B/s
```

Get it installed and appearing in the Ubuntu top bar.

---

## Milestone 7 — Connect Extension to Agent

Now:

```text
NetHogs
 ↓
Agent
 ↓
Unix socket
 ↓
GNOME
```

The top bar becomes live.

---

## Milestone 8 — Process Dropdown

Implement:

```text
Chrome       5.2 MB/s
Docker       2.1 MB/s
VS Code      0.8 MB/s
```

---

## Milestone 9 — Kill Process

Implement:

```text
Right click
 ↓
Kill
 ↓
Agent
 ↓
SIGTERM
```

Then test thoroughly.

---

## Milestone 10 — Packaging & Polish

Finally:

```text
systemd
startup
permissions
settings
icons
documentation
installation script
```

---

# 29. Testing Strategy

You should have three levels.

### Unit tests

Test:

```text
parser
speed calculation
PID validation
JSON API
```

### Integration tests

Test:

```text
NetHogs → Agent
Agent → Socket
Socket → Extension
```

### Manual UI tests

Test:

```text
extension enable
extension disable
agent unavailable
NetHogs unavailable
process disappears
process killed
Ubuntu restart
```

---

# 30. Git Strategy

Create the repository immediately.

```bash
git init
```

Branches:

```text
main
develop
feature/net-hogs
feature/socket
feature/gnome-ui
feature/process-kill
```

Commit frequently.

For example:

```text
feat: add NetHogs process reader
feat: add NetHogs parser
feat: add network state engine
feat: add unix socket server
feat: create GNOME panel indicator
feat: display live network speed
feat: add process dropdown
feat: add process termination
```

---

# 31. Version Plan

### v0.1 — Proof of Concept

```text
NetHogs
 ↓
Python
 ↓
terminal JSON
```

### v0.2 — Backend

```text
NetHogs
 ↓
Agent
 ↓
Unix socket
```

### v0.3 — GNOME

```text
Top bar
 ↓
live speed
```

### v0.4 — Process UI

```text
Dropdown
 ↓
processes
```

### v0.5 — Actions

```text
Kill process
```

### v1.0 — MVP

```text
stable
automatic startup
error handling
settings
documentation
```

---

# 32. Future Architecture

Once the MVP is stable, you can evolve it into:

```text
                    NetMonitor
                        │
          ┌─────────────┴─────────────┐
          │                           │
       GNOME UI                    Agent
          │                           │
          │                     ┌─────┴─────┐
          │                     │           │
          │                  NetHogs      eBPF
          │
          ├── Current traffic
          ├── Process traffic
          ├── History
          ├── Connections
          └── Process control
```

Then potentially add:

```text
Network history
      ↓
Graphs
      ↓
Top consumers
      ↓
Per-application statistics
      ↓
Connection details
      ↓
Bandwidth alerts
```

---

# 33. The Most Important Development Rule

Because you're new to this kind of application, **don't try to learn GNOME extension development, Linux networking, IPC, systemd, Python, and NetHogs simultaneously.**

We'll build it vertically:

```text
             STEP 1
        NetHogs → Python
              ↓
             STEP 2
        Python parser
              ↓
             STEP 3
       Python → Unix socket
              ↓
             STEP 4
       GNOME top-bar UI
              ↓
             STEP 5
        Live connection
              ↓
             STEP 6
        Process dropdown
              ↓
             STEP 7
         Kill process
              ↓
             STEP 8
      systemd + packaging
```

At every stage, you'll have **something that actually works**.

---

## 34. Final Technology Decision

So, if we're committing to the stack today, I'd use:

```text
┌──────────────────────────────────────┐
│              UI LAYER                │
│                                      │
│       GNOME Shell Extension          │
│              GJS                     │
└──────────────────┬───────────────────┘
                   │
             Unix Socket
                   │
┌──────────────────▼───────────────────┐
│             AGENT LAYER              │
│                                      │
│             Python 3                 │
│                                      │
│  Parser │ State │ API │ Process Mgmt │
└──────────────────┬───────────────────┘
                   │
                subprocess
                   │
┌──────────────────▼───────────────────┐
│          MONITORING ENGINE           │
│                                      │
│              NetHogs                 │
└──────────────────────────────────────┘
```

**That's the architecture I recommend you actually implement.**

And importantly, **we don't need to design the entire thing before writing code**. I'll guide you milestone-by-milestone, including the Linux commands, files to create, code, how to run it, how to debug errors, and how to verify each milestone before moving to the next one.

### Our first development task

We should start with **Milestone 1 + Milestone 2**:

> Set up the development environment and build a tiny Python program that starts NetHogs and reliably extracts its per-process network statistics.

Once that works on your Ubuntu machine, we'll turn that into the proper monitoring agent.
