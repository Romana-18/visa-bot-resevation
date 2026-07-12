let currentProcessId = null;
let logInterval = null;

// Tab switching
document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', (e) => {
    e.preventDefault();
    const tab = item.dataset.tab;
    
    // Update nav
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    item.classList.add('active');
    
    // Update content
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.getElementById(tab + 'Tab').classList.add('active');
    
    // Update title
    const titles = {
      config: 'Bot Configuration',
      logs: 'Live Logs',
      help: 'Help & Guide'
    };
    document.getElementById('pageTitle').textContent = titles[tab];
  });
});

async function startBot() {
  const email = document.getElementById('email').value;
  const password = document.getElementById('password').value;

  if (!email || !password) {
    alert('⚠️ Please enter email and password');
    return;
  }

  const config = {
    email,
    password,
    office: document.getElementById('office').value,
    pricing: document.getElementById('pricing').value,
    visaType: document.getElementById('visaType').value,
    city: document.getElementById('city').value,
    tripDate: document.getElementById('tripDate').value,
    daysAhead: document.getElementById('daysAhead').value,
    maxRps: document.getElementById('maxRps').value,
    autoCheck: document.getElementById('autoCheck').checked,
    autoProceed: document.getElementById('autoProceed').checked,
    haltOnFound: document.getElementById('haltOnFound').checked,
    beepOnFound: document.getElementById('beepOnFound').checked,
    alertOnFound: document.getElementById('alertOnFound').checked,
    proxyServer: document.getElementById('proxyServer').value.trim(),
    proxyUser: document.getElementById('proxyUser').value.trim(),
    proxyPass: document.getElementById('proxyPass').value.trim(),
  };

  const startBtn = document.getElementById('startBtn');
  startBtn.disabled = true;
  startBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Starting...';

  try {
    const response = await fetch('/api/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });

    const data = await response.json();

    if (data.success) {
      currentProcessId = data.processId;
      startBtn.innerHTML = '<i class="fas fa-play"></i> Start Bot';
      document.getElementById('stopBtn').disabled = false;
      
      // Update status
      document.getElementById('statusDot').classList.add('active');
      document.getElementById('statusText').textContent = 'Running';
      
      // Switch to logs tab
      document.querySelector('[data-tab="logs"]').click();
      
      // Start polling logs
      logInterval = setInterval(fetchLogs, 1000);
    } else {
      alert('❌ Failed to start: ' + (data.error || 'Unknown error'));
      startBtn.disabled = false;
      startBtn.innerHTML = '<i class="fas fa-play"></i> Start Bot';
    }
  } catch (error) {
    alert('❌ Error: ' + error.message);
    startBtn.disabled = false;
    startBtn.innerHTML = '<i class="fas fa-play"></i> Start Bot';
  }
}

async function stopBot() {
  if (!currentProcessId) return;

  const stopBtn = document.getElementById('stopBtn');
  stopBtn.disabled = true;
  stopBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Stopping...';

  try {
    const response = await fetch(`/api/stop/${currentProcessId}`, {
      method: 'POST'
    });

    const data = await response.json();

    if (data.success) {
      clearInterval(logInterval);
      document.getElementById('startBtn').disabled = false;
      stopBtn.innerHTML = '<i class="fas fa-stop"></i> Stop';
      
      // Update status
      document.getElementById('statusDot').classList.remove('active');
      document.getElementById('statusText').textContent = 'Stopped';
      
      currentProcessId = null;
    }
  } catch (error) {
    alert('❌ Error: ' + error.message);
    stopBtn.disabled = false;
    stopBtn.innerHTML = '<i class="fas fa-stop"></i> Stop';
  }
}

async function fetchLogs() {
  if (!currentProcessId) return;

  try {
    const response = await fetch(`/api/logs/${currentProcessId}`);
    const data = await response.json();

    const logsContainer = document.getElementById('logsContainer');
    logsContainer.innerHTML = '';

    if (data.logs.length === 0) {
      logsContainer.innerHTML = '<div class="log-entry">No logs yet...</div>';
      return;
    }

    data.logs.forEach(log => {
      const entry = document.createElement('div');
      entry.className = 'log-entry';
      
      const text = log.text;
      
      // Color coding based on log content
      if (text.includes('[FOUND]') || text.includes('[HIT]') || text.includes('SLOTS') || text.includes('✓')) {
        entry.classList.add('success');
      } else if (text.includes('[ERR]') || text.includes('ERROR') || text.includes('Failed') || text.includes('✗')) {
        entry.classList.add('error');
      } else if (text.includes('[WARN]') || text.includes('WARNING') || text.includes('⚠')) {
        entry.classList.add('warning');
      } else if (text.includes('[INFO]') || text.includes('[OK]') || text.includes('[BOOT]') || text.includes('[LOGIN]') || text.includes('[API]')) {
        entry.classList.add('info');
      }

      const time = new Date(log.time).toLocaleTimeString();
      entry.textContent = `[${time}] ${text}`;
      logsContainer.appendChild(entry);
    });

    // Auto-scroll to bottom
    logsContainer.scrollTop = logsContainer.scrollHeight;

    if (data.finished) {
      clearInterval(logInterval);
      document.getElementById('startBtn').disabled = false;
      document.getElementById('stopBtn').disabled = true;
      document.getElementById('statusDot').classList.remove('active');
      document.getElementById('statusText').textContent = 'Finished';
    }
  } catch (error) {
    console.error('Error fetching logs:', error);
  }
}

function clearLogs() {
  document.getElementById('logsContainer').innerHTML = '<div class="log-entry">Logs cleared...</div>';
}

// Auto-focus email on load
window.addEventListener('load', () => {
  document.getElementById('email').focus();
});
