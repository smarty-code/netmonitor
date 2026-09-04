import Clutter from 'gi://Clutter';
import Pango from 'gi://Pango';
import St from 'gi://St';

import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

import {formatRate} from './format.js';
import {setTextIfChanged, stabilizeRateLabel} from './ui.js';

export function processKey(process) {
    if (process.pid > 1)
        return String(process.pid);
    return `0:${process.name}:${process.command}`;
}

export function createProcessRow(process, actions) {
    const item = new PopupMenu.PopupMenuItem('');
    item._netPid = process.pid;
    item._process = process;

    item.label.add_style_class_name('netmonitor-process-name');
    item.label.x_expand = true;
    item.label.x_align = Clutter.ActorAlign.START;
    item.label.clutter_text.ellipsize = Pango.EllipsizeMode.END;

    const rateLabel = new St.Label({
        style_class: 'netmonitor-process-total',
        y_align: Clutter.ActorAlign.CENTER,
        x_align: Clutter.ActorAlign.END,
        x_expand: false,
    });
    stabilizeRateLabel(rateLabel);
    item.add_child(rateLabel);

    item.connect('activate', () => actions.onSelect(item._process));

    item.update = proc => {
        item._netPid = proc.pid;
        item._process = proc;
        setTextIfChanged(item.label, proc.name);
        setTextIfChanged(rateLabel, formatRate(proc.total));
    };
    Object.defineProperty(item, 'pid', {
        get() {
            return item._netPid;
        },
    });
    item.update(process);
    return item;
}
