export function formatRate(bytesPerSec) {
    const value = Math.abs(Number(bytesPerSec) || 0);
    if (value < 1024)
        return `${value.toFixed(0)} B/s`;
    if (value < 1024 * 1024)
        return `${(value / 1024).toFixed(1)} KB/s`;
    return `${(value / (1024 * 1024)).toFixed(2)} MB/s`;
}

export function formatPair(download, upload) {
    return `↓ ${formatRate(download)}   ↑ ${formatRate(upload)}`;
}
