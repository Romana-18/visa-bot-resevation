// server.mjs - Web GUI for Almaviva Visa Bot
import express from 'express';
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();
const PORT = 3000;

// Store running processes
const runningProcesses = new Map();

app.use(express.json());
app.use(express.static('public'));

// API endpoint to start bot
app.post('/api/start', (req, res) => {
  const {
    email,
    password,
    office,
    pricing,
    visaType,
    city,
    tripDate,
    daysAhead,
    maxRps,
    autoCheck,
    autoProceed,
    haltOnFound,
    beepOnFound,
    alertOnFound,
    proxyServer,
    proxyUser,
    proxyPass
  } = req.body;

  if (!email || !password) {
    return res.status(400).json({ error: 'Email and password required' });
  }

  const env = {
    ...process.env,
    APP_EMAIL: email,
    APP_PASS: password,
    OFFICE_NAME: office || 'Cairo',
    PRICING_NAME: pricing || 'Standard',
    VISA_NAME: visaType || 'Employment Visa (D)',
    CITY: city || 'milano',
    TRIP_DATE: tripDate || '25/08/2025',
    DAYS_AHEAD: daysAhead || '14',
    MAX_RPS: maxRps || '6',
    AUTO_CHECK: autoCheck ? '1' : '0',
    AUTO_PROCEED: autoProceed ? '1' : '0',
    HALT_ON_FOUND: haltOnFound ? '1' : '0',
    BEEP_ON_FOUND: beepOnFound ? '1' : '0',
    ALERT_ON_FOUND: alertOnFound ? '1' : '0',
    USE_CHROME: process.env.USE_CHROME || '0',
    PROXY_SERVER: proxyServer || '',
    PROXY_USER: proxyUser || '',
    PROXY_PASS: proxyPass || '',
  };

  // Use the correct script path (visa-bot.js in root)
  const scriptPath = join(__dirname, 'visa-bot.js');
  
  if (!fs.existsSync(scriptPath)) {
    console.error('❌ Script not found at:', scriptPath);
    return res.status(500).json({ 
      error: 'visa-bot.js not found in project root. Please check the file exists.' 
    });
  }
  
  console.log('✅ Using script:', scriptPath);

  const proc = spawn('node', ['--', scriptPath], {
    env,
    cwd: __dirname,
  });

  const processId = Date.now().toString();
  runningProcesses.set(processId, { proc, email, logs: [] });

  proc.stdout.on('data', (data) => {
    const log = data.toString();
    const lines = log.split('\n').filter(line => line.trim());
    const process = runningProcesses.get(processId);
    if (process) {
      lines.forEach(line => {
        if (line.trim()) {
          process.logs.push({ time: new Date().toISOString(), text: line });
        }
      });
      // Keep only last 1000 logs
      if (process.logs.length > 1000) {
        process.logs = process.logs.slice(-1000);
      }
    }
  });

  proc.stderr.on('data', (data) => {
    const log = data.toString();
    const lines = log.split('\n').filter(line => line.trim());
    const process = runningProcesses.get(processId);
    if (process) {
      lines.forEach(line => {
        if (line.trim()) {
          process.logs.push({ time: new Date().toISOString(), text: `[ERROR] ${line}` });
        }
      });
    }
  });

  proc.on('close', (code) => {
    const process = runningProcesses.get(processId);
    if (process) {
      process.logs.push({ 
        time: new Date().toISOString(), 
        text: `[EXIT] Process finished with code ${code}` 
      });
      process.finished = true;
    }
  });

  res.json({ 
    success: true, 
    processId,
    message: 'Bot started successfully' 
  });
});

// API endpoint to get logs
app.get('/api/logs/:processId', (req, res) => {
  const { processId } = req.params;
  const process = runningProcesses.get(processId);
  
  if (!process) {
    return res.status(404).json({ error: 'Process not found' });
  }

  res.json({ 
    logs: process.logs,
    finished: process.finished || false
  });
});

// API endpoint to stop bot
app.post('/api/stop/:processId', (req, res) => {
  const { processId } = req.params;
  const process = runningProcesses.get(processId);
  
  if (!process) {
    return res.status(404).json({ error: 'Process not found' });
  }

  try {
    process.proc.kill();
    res.json({ success: true, message: 'Bot stopped' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// API endpoint to list running processes
app.get('/api/processes', (req, res) => {
  const processes = Array.from(runningProcesses.entries()).map(([id, data]) => ({
    id,
    email: data.email,
    running: !data.finished,
    logCount: data.logs.length
  }));
  
  res.json({ processes });
});

app.listen(PORT, () => {
  console.log(`🚀 Almaviva Visa Bot Web GUI running at http://localhost:${PORT}`);
  console.log(`📱 Open your browser and navigate to the URL above`);
});
