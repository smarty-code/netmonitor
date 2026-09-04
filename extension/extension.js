import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

import {NetMonitorIndicator} from './indicator.js';

const PANEL_BOXES = new Set(['left', 'center', 'right']);

export default class NetMonitorExtension extends Extension {
    enable() {
        this._settings = this.getSettings();
        this._indicator = null;
        this._addToPanel();
        this._settings.connectObject(
            'changed::panel-position', () => this._addToPanel(),
            'changed::panel-index', () => this._addToPanel(),
            this
        );
    }

    _addToPanel() {
        this._indicator?.destroy();
        this._indicator = new NetMonitorIndicator(this);
        const raw = this._settings.get_string('panel-position');
        const box = PANEL_BOXES.has(raw) ? raw : 'right';
        const index = Math.max(0, this._settings.get_int('panel-index'));
        Main.panel.addToStatusArea(this.uuid, this._indicator, index, box);
    }

    disable() {
        this._settings?.disconnectObject(this);
        this._indicator?.destroy();
        this._indicator = null;
        this._settings = null;
    }
}
