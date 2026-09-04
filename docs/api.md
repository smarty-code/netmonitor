# Agent API

Transport: Unix domain stream socket at `$XDG_RUNTIME_DIR/netmonitor.sock` (mode `0600`).

Framing: one JSON object per line. The client writes a request line; the agent writes a response line.

Requests should look like:

```json
{"id": 1, "action": "get_stats"}
```

Never send a shell string. `{"command":"kill 1"}` is rejected.

## Actions

### `ping`

```json
{"action": "ping"}
```

```json
{"ok": true, "status": "ok"}
```

### `get_stats`

Returns the current snapshot. Rates are **bytes per second**.

```json
{
  "ok": true,
  "timestamp": 1725440000.0,
  "status": "ok",
  "status_message": "",
  "total": {"download": 12400000, "upload": 2100000},
  "processes": [
    {
      "pid": 1234,
      "name": "chrome",
      "command": "/usr/bin/google-chrome",
      "download": 7200000,
      "upload": 600000,
      "total": 7800000
    }
  ]
}
```

`status` is one of: `starting`, `ok`, `nethogs_missing`, `permission_denied`, `nethogs_exited`.

### `get_processes`

Same process list without the totals wrapper.

### `get_process`

```json
{"action": "get_process", "pid": 1234}
```

### `kill_process`

Sends `SIGTERM`. `pid` must be a JSON integer greater than 1.

```json
{"action": "kill_process", "pid": 1234}
```

### `force_kill_process`

Sends `SIGKILL`.

```json
{"action": "force_kill_process", "pid": 1234}
```

## Errors

Failed requests return:

```json
{"ok": false, "error": "invalid_pid", "message": "pid must be a positive integer"}
```

| `error` | Meaning |
|---|---|
| `invalid_json` | Body was not a JSON object |
| `invalid_request` | A `command` string was sent |
| `unknown_action` | `action` is not supported |
| `invalid_pid` | PID missing, not an int, `<= 1`, or the agent itself |
| `not_found` | Process is gone or not in the snapshot |
| `permission_denied` | `os.kill` was not allowed |
