async function refreshStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();

    const dot = document.getElementById('status-dot');
    const text = document.getElementById('status-text');

    if (dot && text) {
      dot.className = 'status-dot ' + data.bot_status.toLowerCase();
      const labels = { RUNNING: 'Çalışıyor', PAUSED: 'Duraklatıldı', STOPPED: 'Durduruldu' };
      text.textContent = (labels[data.bot_status] || data.bot_status) + ' | ' +
        (data.market_open ? 'Piyasa Açık' : 'Piyasa Kapalı');
    }

    const mCash = document.getElementById('m-cash');
    const mTotal = document.getElementById('m-total');
    const mPnl = document.getElementById('m-pnl');
    const mPos = document.getElementById('m-positions');

    if (mCash) mCash.textContent = data.cash.toLocaleString('tr-TR') + ' TL';
    if (mTotal) mTotal.textContent = data.total_value.toLocaleString('tr-TR') + ' TL';
    if (mPnl) {
      const sign = data.daily_pnl >= 0 ? '+' : '';
      mPnl.textContent = sign + data.daily_pnl.toFixed(0) + ' TL (' + sign + data.daily_pnl_pct.toFixed(2) + '%)';
      mPnl.className = 'metric-value ' + (data.daily_pnl >= 0 ? 'text-green' : 'text-red');
    }
    if (mPos) mPos.textContent = data.open_positions;
  } catch (e) {
    // sessizce geç
  }
}

refreshStatus();
setInterval(refreshStatus, 10000);
