import Clutter from 'gi://Clutter';
import Pango from 'gi://Pango';

const RATE_STYLE = 'font-family: monospace; font-feature-settings: "tnum";';

export function setTextIfChanged(label, text) {
    if (label.text !== text)
        label.text = text;
}

export function stabilizeRateLabel(label) {
    label.clutter_text.ellipsize = Pango.EllipsizeMode.NONE;
    label.x_expand = false;
    label.x_align = Clutter.ActorAlign.END;
    label.set_style(RATE_STYLE);
}
