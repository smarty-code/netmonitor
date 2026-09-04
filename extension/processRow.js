import Clutter from 'gi://Clutter';
import Pango from 'gi://Pango';
import St from 'gi://St';

import {gettext as _} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

import {formatPair, formatRate} from './format.js';
import {setTextIfChanged, stabilizeRateLabel} from './ui.js';

export function createProcessRow(process, actions) {
    const item = new PopupMenu.PopupSubMenuMenuItem('', false);
    item._netPid = process.pid;

    item.label.add_style_class_name('netmonitor-process-name');
    item.label.x_align = Clutter.ActorAlign.START;
    item.label.clutter_text.ellipsize = Pango.EllipsizeMode.END;

    const rateLabel = new St.Label({
        style_class: 'netmonitor-process-total',
        y_align: Clutter.ActorAlign.CENTER,
        x_align: Clutter.ActorAlign.END,
        x_expand: false,
    });
    stabilizeRateLabel(rateLabel);
    item.insert_child_below(rateLabel, item._triangleBin);

    const ratesItem = new PopupMenu.PopupMenuItem('', {reactive: false});
    ratesItem.label.add_style_class_name('netmonitor-process-rates');
    stabilizeRateLabel(ratesItem.label);
    item.menu.addMenuItem(ratesItem);
    item.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
    item.menu.addAction(_('Details'), () => actions.onDetails(item._netPid));
    if (process.pid > 1) {
        item.menu.addAction(_('Kill Process'), () => actions.onKill(item._netPid, false));
        item.menu.addAction(_('Force Kill'), () => actions.onKill(item._netPid, true));
    }

    item.update = proc => {
        item._netPid = proc.pid;
        setTextIfChanged(item.label, proc.name);
        setTextIfChanged(rateLabel, formatRate(proc.total));
        setTextIfChanged(ratesItem.label, formatPair(proc.download, proc.upload));
    };
    Object.defineProperty(item, 'pid', {
        get() {
            return item._netPid;
        },
    });
    item.update(process);
    return item;
}
