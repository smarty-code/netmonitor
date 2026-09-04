import {gettext as _} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

import {formatPair, formatRate} from './format.js';

export function createProcessRow(process, actions) {
    const item = new PopupMenu.PopupSubMenuMenuItem('', false);
    item._netPid = process.pid;

    const ratesItem = new PopupMenu.PopupMenuItem('', {reactive: false});
    ratesItem.label.add_style_class_name('netmonitor-process-rates');
    item.menu.addMenuItem(ratesItem);
    item.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
    item.menu.addAction(_('Details'), () => actions.onDetails(item._netPid));
    item.menu.addAction(_('Kill Process'), () => actions.onKill(item._netPid, false));
    item.menu.addAction(_('Force Kill'), () => actions.onKill(item._netPid, true));

    item.update = proc => {
        item._netPid = proc.pid;
        item.label.text = `${proc.name}   ${formatRate(proc.total)}`;
        item.label.add_style_class_name('netmonitor-process-name');
        ratesItem.label.text = formatPair(proc.download, proc.upload);
    };
    Object.defineProperty(item, 'pid', {
        get() {
            return item._netPid;
        },
    });
    item.update(process);
    return item;
}
