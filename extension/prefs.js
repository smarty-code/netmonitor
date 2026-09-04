import Adw from 'gi://Adw';
import Gtk from 'gi://Gtk';

import {ExtensionPreferences, gettext as _} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

const POSITIONS = ['left', 'center', 'right'];

export default class NetMonitorPreferences extends ExtensionPreferences {
    async fillPreferencesWindow(window) {
        const settings = this.getSettings();
        window.add(this._appearancePage(settings));
        window.add(this._updatesPage(settings));
    }

    _appearancePage(settings) {
        const page = new Adw.PreferencesPage({
            title: _('Appearance'),
            icon_name: 'preferences-desktop-display-symbolic',
        });
        const group = new Adw.PreferencesGroup({
            title: _('Top bar'),
            description: _('Choose where NetMonitor sits on the GNOME status bar.'),
        });

        const labels = [_('Left'), _('Center'), _('Right')];
        const model = new Gtk.StringList();
        for (const label of labels)
            model.append(label);
        const positionRow = new Adw.ComboRow({
            title: _('Position'),
            subtitle: _('Left, center, or right area of the top bar'),
            model,
        });
        const current = settings.get_string('panel-position');
        positionRow.selected = Math.max(0, POSITIONS.indexOf(current));
        positionRow.connect('notify::selected', () => {
            settings.set_string(
                'panel-position',
                POSITIONS[positionRow.selected] ?? 'right'
            );
        });
        settings.connect('changed::panel-position', () => {
            const value = settings.get_string('panel-position');
            const index = POSITIONS.indexOf(value);
            if (index >= 0 && positionRow.selected !== index)
                positionRow.selected = index;
        });

        const indexRow = new Adw.SpinRow({
            title: _('Order in that area'),
            subtitle: _('0 is first. Raise the number to move it along the bar.'),
            adjustment: new Gtk.Adjustment({
                lower: 0,
                upper: 20,
                step_increment: 1,
                page_increment: 1,
            }),
        });
        indexRow.value = settings.get_int('panel-index');
        indexRow.connect('notify::value', () => {
            settings.set_int('panel-index', Math.round(indexRow.value));
        });
        settings.connect('changed::panel-index', () => {
            const value = settings.get_int('panel-index');
            if (Math.round(indexRow.value) !== value)
                indexRow.value = value;
        });

        group.add(positionRow);
        group.add(indexRow);
        page.add(group);
        return page;
    }

    _updatesPage(settings) {
        const page = new Adw.PreferencesPage({
            title: _('Updates'),
            icon_name: 'emblem-synchronizing-symbolic',
        });
        const group = new Adw.PreferencesGroup({
            title: _('Polling'),
            description: _('How often NetMonitor asks the agent for new speeds.'),
        });

        const values = [1, 2, 5];
        const model = new Gtk.StringList({
            strings: values.map(seconds => `${seconds}s`),
        });
        const row = new Adw.ComboRow({
            title: _('Refresh interval'),
            model,
        });
        const current = settings.get_int('refresh-interval');
        row.selected = Math.max(0, values.indexOf(current));
        row.connect('notify::selected', () => {
            settings.set_int('refresh-interval', values[row.selected] ?? 1);
        });

        group.add(row);
        page.add(group);
        return page;
    }
}
