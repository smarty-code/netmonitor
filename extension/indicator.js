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
import {setTextIfChanged, stabilizeRateLabel} from './ui.js';

export const NetMonitorIndicator = GObject.registerClass({
    GTypeName: 'NetMonitorIndicatorV4',
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
            text: formatPair(0, 0),
            style_class: 'netmonitor-indicator-label',
            y_align: Clutter.ActorAlign.CENTER,
            x_expand: false,
        });
        stabilizeRateLabel(this._label, ' font-size: 9pt;');
        this.add_child(this._label);

        this._monitorMenu = new MonitorMenu(this.menu, {
            onRetry: () => this._poll(true),
            onPrefs: () => this._openPrefs(),
            onSelect: process => this._showDetails(process),
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

    _openPrefs() {
        this.menu.close();
        GLib.timeout_add(GLib.PRIORITY_DEFAULT, 150, () => {
            try {
                this._extension.openPreferences();
            } catch (error) {
                logError(error, '[netmonitor] openPreferences');
                Main.notifyError(_('NetMonitor'), _('Could not open settings'));
            }
            return GLib.SOURCE_REMOVE;
        });
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
            setTextIfChanged(this._label, formatPair(
                stats.total?.download || 0,
                stats.total?.upload || 0
            ));
            if (this._menuOpen || forceMenu) {
                this._monitorMenu.updateStats(stats, {
                    syncProcesses: true,
                });
            }
        } catch (error) {
            logError(error, '[netmonitor] poll failed');
            this._failCount += 1;
            setTextIfChanged(
                this._label,
                this._failCount >= 3 ? _('Unavailable') : _('Connecting…')
            );
            if (this._menuOpen || forceMenu) {
                if (this._failCount >= 3)
                    this._monitorMenu.showUnavailable();
                else
                    this._monitorMenu.showConnecting();
            }
        }
    }

    _afterMenuClose(callback) {
        this.menu.close();
        GLib.timeout_add(GLib.PRIORITY_DEFAULT, 150, () => {
            try {
                callback();
            } catch (error) {
                logError(error, '[netmonitor] after menu close');
            }
            return GLib.SOURCE_REMOVE;
        });
    }

    _showDetails(process) {
        this._afterMenuClose(() => {
            this._openDetails(process).catch(error => {
                const message = error instanceof AgentError
                    ? error.message
                    : _('Could not open process details');
                Main.notifyError(_('NetMonitor'), message);
            });
        });
    }

    async _openDetails(process) {
        let proc = process;
        if (process?.pid > 1) {
            try {
                const response = await this._client.getProcess(process.pid);
                proc = response.process;
            } catch (error) {
                logError(error, '[netmonitor] get_process');
            }
        }
        if (!proc)
            throw new AgentError('not_found', _('Process is no longer available'));

        const dialog = new ModalDialog.ModalDialog();
        const total = Number(proc.total);
        const totalRate = Number.isFinite(total)
            ? total
            : (Number(proc.download) || 0) + (Number(proc.upload) || 0);
        const body = [
            proc.name,
            `${_('PID')}: ${proc.pid}`,
            `${_('Command')}: ${proc.command || '—'}`,
            `${_('Download')}: ${formatRate(proc.download)}`,
            `${_('Upload')}: ${formatRate(proc.upload)}`,
            `${_('Total')}: ${formatRate(totalRate)}`,
        ].join('\n');
        dialog.contentLayout.add_child(new St.Label({
            text: body,
            style_class: 'netmonitor-status',
        }));

        const buttons = [];
        if (proc.pid > 1) {
            buttons.push({
                label: _('Kill Process'),
                action: () => {
                    dialog.close();
                    this._killNow(proc.pid, false);
                },
            });
            buttons.push({
                label: _('Force Kill'),
                action: () => {
                    dialog.close();
                    this._killNow(proc.pid, true);
                },
            });
        }
        buttons.push({
            label: _('Close'),
            action: () => dialog.close(),
            default: true,
        });
        dialog.setButtons(buttons);
        if (!dialog.open())
            throw new AgentError('unavailable', _('Could not open process details'));
    }

    _killNow(pid, force) {
        const target = Number.parseInt(pid, 10);
        log(`[netmonitor] ${force ? 'force_kill' : 'kill'} pid=${target}`);
        this._client.killProcess(target, force).then(() => {
            Main.notify(
                _('NetMonitor'),
                force ? _('Process killed') : _('Stop signal sent')
            );
            this._poll(true);
        }).catch(error => {
            const message = error instanceof AgentError
                ? error.message
                : _('Could not terminate the process');
            Main.notifyError(_('NetMonitor'), message);
        });
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
