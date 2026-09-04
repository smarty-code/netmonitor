import {gettext as _} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

import {formatRate} from './format.js';
import {createProcessRow} from './processRow.js';

export class MonitorMenu {
    constructor(menu, callbacks) {
        this._menu = menu;
        this._callbacks = callbacks;
        this._rows = new Map();

        this._title = new PopupMenu.PopupMenuItem(_('Network Monitor'), {
            reactive: false,
        });
        this._title.label.add_style_class_name('netmonitor-header-title');
        menu.addMenuItem(this._title);

        this._downItem = new PopupMenu.PopupMenuItem('↓ 0 B/s', {reactive: false});
        this._downItem.label.add_style_class_name('netmonitor-header-rate');
        menu.addMenuItem(this._downItem);

        this._upItem = new PopupMenu.PopupMenuItem('↑ 0 B/s', {reactive: false});
        this._upItem.label.add_style_class_name('netmonitor-header-rate');
        menu.addMenuItem(this._upItem);

        menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem(_('Applications')));

        this._statusItem = new PopupMenu.PopupMenuItem(_('Connecting…'), {
            reactive: false,
        });
        this._statusItem.label.clutter_text.line_wrap = true;
        menu.addMenuItem(this._statusItem);

        this._processSection = new PopupMenu.PopupMenuSection();
        menu.addMenuItem(this._processSection);

        menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        this._retryItem = menu.addAction(_('Retry'), () => this._callbacks.onRetry());
        this._prefsItem = menu.addAction(_('Settings'), () => this._callbacks.onPrefs());

        this.showConnecting();
    }

    showConnecting() {
        this._setStatus(_('Connecting…'), true);
        this._clearRows();
    }

    showUnavailable() {
        this._setStatus(_('Agent unavailable'), true);
        this._clearRows();
    }

    showStatus(message, canRetry = true) {
        this._setStatus(message, canRetry);
        this._clearRows();
    }

    updateStats(stats) {
        const total = stats.total || {download: 0, upload: 0};
        this._downItem.label.text = `↓ ${formatRate(total.download)}`;
        this._upItem.label.text = `↑ ${formatRate(total.upload)}`;

        const status = stats.status || 'ok';
        if (status === 'nethogs_missing') {
            this.showStatus(_('NetHogs not found'), false);
            return;
        }
        if (status === 'permission_denied') {
            this.showStatus(_('Network monitoring requires additional permissions.'), false);
            return;
        }
        if (status !== 'ok' && status !== 'starting') {
            this.showStatus(stats.status_message || _('Agent unavailable'), true);
            return;
        }

        this._statusItem.visible = false;
        this._retryItem.visible = false;
        this._syncProcesses(stats.processes || []);
    }

    _setStatus(text, canRetry) {
        this._statusItem.label.text = text;
        this._statusItem.visible = true;
        this._retryItem.visible = canRetry;
    }

    _syncProcesses(processes) {
        const seen = new Set();
        processes.forEach((process, index) => {
            seen.add(process.pid);
            let row = this._rows.get(process.pid);
            if (!row) {
                row = createProcessRow(process, this._callbacks);
                this._rows.set(process.pid, row);
                this._processSection.addMenuItem(row);
            } else {
                row.update(process);
            }
            this._processSection.moveMenuItem(row, index);
        });

        for (const [pid, row] of this._rows.entries()) {
            if (seen.has(pid))
                continue;
            this._rows.delete(pid);
            row.destroy();
        }

        if (processes.length === 0 && !this._statusItem.visible) {
            this._statusItem.label.text = _('No network activity');
            this._statusItem.visible = true;
        }
    }

    _clearRows() {
        for (const row of this._rows.values())
            row.destroy();
        this._rows.clear();
    }

    destroy() {
        this._clearRows();
    }
}
