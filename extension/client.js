import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

Gio._promisify(Gio.SocketClient.prototype, 'connect_async', 'connect_finish');
Gio._promisify(Gio.OutputStream.prototype, 'write_all_async', 'write_all_finish');
Gio._promisify(Gio.DataInputStream.prototype, 'read_line_async', 'read_line_finish_utf8');

export class AgentError extends Error {
    constructor(code, message) {
        super(message);
        this.name = 'AgentError';
        this.code = code;
    }
}

export function defaultSocketPath() {
    return GLib.build_filenamev([GLib.get_user_runtime_dir(), 'netmonitor.sock']);
}

function unixAddress(path) {
    if (Gio.UnixSocketAddress?.new)
        return Gio.UnixSocketAddress.new(path);
    throw new AgentError('unavailable', `Cannot create Unix socket address for ${path}`);
}

function decodeLine(value) {
    if (value === null || value === undefined)
        return null;
    if (Array.isArray(value))
        return decodeLine(value[0]);
    if (value instanceof Uint8Array)
        return new TextDecoder().decode(value);
    return String(value);
}

export class AgentClient {
    constructor(socketPath = defaultSocketPath()) {
        this._path = socketPath;
        this._connection = null;
        this._input = null;
        this._output = null;
        this._nextId = 1;
        this._queue = Promise.resolve();
    }

    close() {
        try {
            this._connection?.close(null);
        } catch {
        }
        this._connection = null;
        this._input = null;
        this._output = null;
    }

    async ping() {
        return this.request({action: 'ping'});
    }

    async getStats() {
        return this.request({action: 'get_stats'});
    }

    async getProcess(pid) {
        return this.request({action: 'get_process', pid});
    }

    async killProcess(pid, force = false) {
        const n = Number.parseInt(pid, 10);
        if (!Number.isInteger(n) || n <= 1)
            throw new AgentError('invalid_pid', 'pid must be greater than 1');
        return this.request({
            action: force ? 'force_kill_process' : 'kill_process',
            pid: n,
        });
    }

    request(payload, timeoutMs = 2000) {
        const run = () => this._request(payload, timeoutMs);
        this._queue = this._queue.then(run, run);
        return this._queue;
    }

    async _request(payload, timeoutMs) {
        const body = Object.assign({id: this._nextId++}, payload);
        const cancellable = new Gio.Cancellable();
        let timeoutId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, timeoutMs, () => {
            timeoutId = 0;
            cancellable.cancel();
            return GLib.SOURCE_REMOVE;
        });
        try {
            if (!GLib.file_test(this._path, GLib.FileTest.EXISTS))
                throw new AgentError('unavailable', 'Agent unavailable');
            await this._ensureConnected(cancellable);
            const encoded = `${JSON.stringify(body)}\n`;
            const bytes = new TextEncoder().encode(encoded);
            await this._output.write_all_async(bytes, GLib.PRIORITY_DEFAULT, cancellable);
            const raw = await this._input.read_line_async(
                GLib.PRIORITY_DEFAULT,
                cancellable
            );
            const line = decodeLine(raw);
            if (!line)
                throw new AgentError('disconnected', 'Agent closed the connection');
            const parsed = JSON.parse(line);
            if (parsed.ok === false) {
                throw new AgentError(
                    parsed.error || 'error',
                    parsed.message || parsed.error || 'Request failed'
                );
            }
            return parsed;
        } catch (error) {
            this.close();
            if (error instanceof AgentError)
                throw error;
            if (error.matches?.(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED))
                throw new AgentError('timeout', 'Agent did not respond');
            throw new AgentError('unavailable', error.message || 'Agent unavailable');
        } finally {
            if (timeoutId)
                GLib.source_remove(timeoutId);
        }
    }

    async _ensureConnected(cancellable) {
        if (this._connection && !this._connection.is_closed())
            return;
        const client = new Gio.SocketClient();
        try {
            this._connection = await client.connect_async(
                unixAddress(this._path),
                cancellable
            );
        } catch (error) {
            throw new AgentError(
                'unavailable',
                error.message || 'Agent unavailable'
            );
        }
        this._output = this._connection.get_output_stream();
        this._input = new Gio.DataInputStream({
            base_stream: this._connection.get_input_stream(),
            close_base_stream: false,
        });
    }
}
