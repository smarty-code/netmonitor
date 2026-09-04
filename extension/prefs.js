import Adw from 'gi://Adw';
import Gtk from 'gi://Gtk';

import {ExtensionPreferences, gettext as _} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

export default class NetMonitorPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings();
        const page = new Adw.PreferencesPage();
        const group = new Adw.PreferencesGroup({
            title: _('Updates'),
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
        window.add(page);
    }
}
