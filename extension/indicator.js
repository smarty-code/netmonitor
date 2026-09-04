import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import St from 'gi://St';

import {gettext as _} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as ModalDialog from 'resource:///org/gnome/shell/ui/modalDialog.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';

import {AgentClient, AgentError} from './client.js';
import {formatPair, formatRate} from './format.js';
import {MonitorMenu} from './menu.js';

export const NetMonitorIndicator = GObject.registerClass({
    GTypeName: 'NetMonitorIndicator',
}, class NetMonitorIndicator extends PanelMenu.Button {
    _init(extension) {
        super._init(0.5, _('Network Monitor'), false);
        this._extension = extension;
        this._settings = extension.getSettings();
        this._client = new AgentClient();
        this._sourceId = 0;
        this._menuOpen = false;
        this._failCount = 0;

        this._label = new St.Label({
            text: '↓ 0 B/s ↑ 0 B/s',
            style_class: 'netmonitor-indicator-label',
            y_align: Clutter.ActorAlign.CENTER,
        });
        this.add_child(this._label);

        this._monitorMenu = new MonitorMenu(this.menu, {
            onRetry: () => this._poll(true),
            onPrefs: () => this._extension.openPreferences(),
            onDetails: pid => this._showDetails(pid),
            onKill: (pid, force) => this._kill(pid, force),
        });

        this.menu.connect('open-state-changed', (_menu, open) => {
            this._menuOpen = open;
            if (open)
                this._poll(true);
        });

        this._settings.connectObject(
            'changed::refresh-interval', () => this._restartTimer(),
            this
        );
        this._restartTimer();
        this._poll(true);
    }

    _intervalSeconds() {
        return Math.max(1, this._settings.get_int('refresh-interval') || 1);
    }

    _restartTimer() {
        if (this._sourceId) {
            GLib.source_remove(this._sourceId);
            this._sourceId = 0;
        }
        this._sourceId = GLib.timeout_add_seconds(
            GLib.PRIORITY_DEFAULT,
            this._intervalSeconds(),
            () => {
                this._poll(false);
                return GLib.SOURCE_CONTINUE;
            }
        );
    }

    async _poll(forceMenu) {
        try {
            const stats = await this._client.getStats();
            this._failCount = 0;
            this._label.text = formatPair(
                stats.total?.download || 0,
                stats.total?.upload || 0
            );
            if (this._menuOpen || forceMenu)
                this._monitorMenu.updateStats(stats);
        } catch (error) {
            logError(error, '[netmonitor] poll failed');
            this._failCount += 1;
            this._label.text = this._failCount >= 3 ? _('Unavailable') : _('Connecting…');
            if (this._menuOpen || forceMenu) {
                if (this._failCount >= 3)
                    this._monitorMenu.showUnavailable();
                else
                    this._monitorMenu.showConnecting();
            }
        }
    }

    async _showDetails(pid) {
        try {
            const response = await this._client.getProcess(pid);
            const proc = response.process;
            const dialog = new ModalDialog.ModalDialog();
            const body = [
                proc.name,
                `${_('PID')}: ${proc.pid}`,
                `${_('Command')}: ${proc.command}`,
                `↓ ${formatRate(proc.download)}`,
                `↑ ${formatRate(proc.upload)}`,
            ].join('\n');
            dialog.contentLayout.add_child(new St.Label({
                text: body,
                style_class: 'netmonitor-status',
            }));
            dialog.setButtons([{
                label: _('Close'),
                action: () => dialog.close(),
                default: true,
            }]);
            dialog.open();
        } catch (error) {
            Main.notifyError(_('NetMonitor'), error.message);
        }
    }

    async _kill(pid, force) {
        try {
            await this._client.killProcess(pid, force);
            this._poll(true);
        } catch (error) {
            const message = error instanceof AgentError
                ? error.message
                : _('Could not terminate the process');
            Main.notifyError(_('NetMonitor'), message);
        }
    }

    destroy() {
        if (this._sourceId) {
            GLib.source_remove(this._sourceId);
            this._sourceId = 0;
        }
        this._settings?.disconnectObject(this);
        this._client?.close();
        this._monitorMenu?.destroy();
        super.destroy();
    }
});
