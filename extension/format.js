const UNITS = ['B/s ', 'KB/s', 'MB/s', 'GB/s', 'TB/s'];
const KIB = 1024;

function fourCharNumber(value, integer) {
    let text;
    if (integer || value >= 99.95)
        text = String(Math.round(value));
    else if (value >= 9.995)
        text = value.toFixed(1);
    else
        text = value.toFixed(2);
    return text.padStart(4, ' ');
}

export function formatRate(bytesPerSec) {
    let value = Math.abs(Number(bytesPerSec) || 0);
    let unit = 0;
    while (value >= KIB && unit < UNITS.length - 1) {
        value /= KIB;
        unit += 1;
    }
    return `${fourCharNumber(value, unit === 0)} ${UNITS[unit]}`;
}

export function formatArrowRate(arrow, bytesPerSec) {
    return `${arrow} ${formatRate(bytesPerSec)}`;
}

export function formatPair(download, upload) {
    return `${formatArrowRate('↓', download)}  ${formatArrowRate('↑', upload)}`;
}
