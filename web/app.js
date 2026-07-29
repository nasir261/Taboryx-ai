const state = {
  dashboard: null,
  inventory: [],
  movements: [],
  insights: [],
  audits: [],
  rooms: [],
  fridges: [],
  token: localStorage.getItem('Taboryx_token') || '',
  currentView: 'login',
  selectedItemId: null,
  error: '',
  searchQuery: '',
  feedback: '',
  feedbackKind: 'info',
  scanCode: '',
};

function formatCurrency(value) {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
    maximumFractionDigits: 2,
  }).format(value || 0);
}

function buildStats(dashboard) {
  return [
    { label: 'Stock value', value: formatCurrency(dashboard.current_stock_value) },
    { label: 'Low stock', value: dashboard.low_stock_count || 0 },
    { label: 'Expired', value: dashboard.expired_count || 0 },
    { label: 'Pending orders', value: dashboard.pending_orders || 0 },
  ];
}

function selectedItem() {
  return state.inventory.find((entry) => String(entry.id) === String(state.selectedItemId)) || null;
}

function getRoomName(roomId) {
  const room = state.rooms.find((entry) => String(entry.id) === String(roomId));
  return room?.room_name || room?.name || `Room ${roomId || 'Unknown'}`;
}

function render() {
  const root = document.getElementById('appRoot');
  if (state.currentView === 'login') {
    root.innerHTML = `
      <div class="form-card">
        <p class="eyebrow">Secure mobile access</p>
        <h1>Taboryx AI</h1>
        <p class="subtle">Sign in with your desktop credentials</p>
        <p class="subtle">Demo: admin / password123</p>
        <form id="loginForm">
          <label for="username">Username</label>
          <input id="username" name="username" autocomplete="username" required />
          <label for="password">Password</label>
          <input id="password" name="password" type="password" autocomplete="current-password" required />
          <button class="pill-button" type="submit">Sign in</button>
        </form>
        ${state.error ? `<div class="error-text">${state.error}</div>` : ''}
      </div>
    `;
    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    return;
  }

  if (state.currentView === 'detail' && state.selectedItemId !== null) {
    const item = selectedItem();
    root.innerHTML = `
      <div class="detail-card">
        <div class="inline-actions">
          <button class="secondary-button" id="backButton">Back</button>
          <button class="pill-button" id="refreshButton">Refresh</button>
        </div>
        <h3>${item ? (item.item_name || 'Item') : 'Item details'}</h3>
        ${item ? `
          <div class="detail-grid">
            <div class="row"><span>Barcode</span><span class="value">${item.barcode || '—'}</span></div>
            <div class="row"><span>Category</span><span class="value">${item.category || '—'}</span></div>
            <div class="row"><span>Quantity</span><span class="value">${item.current_quantity ?? item.quantity ?? 0}</span></div>
            <div class="row"><span>Minimum</span><span class="value">${item.minimum_quantity ?? 0}</span></div>
            <div class="row"><span>Status</span><span class="value">${item.stock_status || item.status || 'Active'}</span></div>
            <div class="row"><span>Expiry</span><span class="value">${item.expiry_date || '—'}</span></div>
            <div class="row"><span>Clinical room</span><span class="value">${item.clinical_room || '—'}</span></div>
          </div>
        ` : '<div class="empty-state">Item not found.</div>'}
      </div>
    `;
    document.getElementById('backButton').addEventListener('click', () => { state.currentView = 'main'; state.error = ''; render(); });
    document.getElementById('refreshButton').addEventListener('click', loadData);
    return;
  }

  if (state.currentView === 'audits') {
    root.innerHTML = `
      <div class="app-shell">
        <header class="app-header">
          <div class="app-title-block">
            <p class="eyebrow">Mobile web</p>
            <h1>Room audits</h1>
            <p class="subtle">Track the latest checks and discrepancies</p>
          </div>
          <button id="backButton" class="secondary-button">Back</button>
        </header>

        <div class="view-nav">
          <button class="view-pill" data-nav-view="main">Overview</button>
          <button class="view-pill active" data-nav-view="audits">Audits</button>
          <button class="view-pill" data-nav-view="ai">AI guidance</button>
        </div>

        <section class="panel">
          <div class="panel-header">
            <h3>Recent room audits</h3>
            <span class="panel-caption">Across the estate</span>
          </div>
          <p class="subtle">Review room compliance, missing items, and expiry issues directly from the phone.</p>
        </section>

        <section class="panel">
          <div id="auditList" class="stack-list"></div>
        </section>
      </div>
    `;
    document.getElementById('backButton').addEventListener('click', () => { state.currentView = 'main'; render(); });
    document.querySelectorAll('[data-nav-view]').forEach((button) => {
      button.addEventListener('click', () => {
        state.currentView = button.getAttribute('data-nav-view');
        render();
      });
    });
    renderAudits();
    return;
  }

  if (state.currentView === 'fridges') {
    root.innerHTML = `
      <div class="app-shell">
        <header class="app-header">
          <div class="app-title-block">
            <p class="eyebrow">Mobile web</p>
            <h1>Fridge monitoring</h1>
            <p class="subtle">Track Wi-Fi-connected pharmacy fridges in real time</p>
          </div>
          <button id="backButton" class="secondary-button">Back</button>
        </header>

        <div class="view-nav">
          <button class="view-pill" data-nav-view="main">Overview</button>
          <button class="view-pill" data-nav-view="audits">Audits</button>
          <button class="view-pill active" data-nav-view="fridges">Fridges</button>
          <button class="view-pill" data-nav-view="ai">AI guidance</button>
        </div>

        <section class="panel">
          <div class="panel-header">
            <h3>Register Wi-Fi fridge</h3>
            <span class="panel-caption">Add a connected fridge</span>
          </div>
          <form id="fridgeForm" class="compact-form stacked-form">
            <label for="fridgeName">Fridge name</label>
            <input id="fridgeName" name="deviceName" placeholder="Example: Pharmacy fridge A" required />
            <label for="fridgeRoom">Room</label>
            <select id="fridgeRoom" name="roomId">
              ${state.rooms.map((room) => `<option value="${room.id}" ${room.id == null ? 'selected' : ''}>${room.room_name || room.name || 'Room'}</option>`).join('')}
            </select>
            <label for="fridgeCode">Device code</label>
            <input id="fridgeCode" name="deviceCode" placeholder="FR-001" />
            <label for="fridgeEndpoint">Endpoint URL</label>
            <input id="fridgeEndpoint" name="endpointUrl" placeholder="https://fridge.example.local/api" />
            <label for="fridgeMin">Min temp (°C)</label>
            <input id="fridgeMin" name="minTemp" type="number" step="0.1" value="2" />
            <label for="fridgeMax">Max temp (°C)</label>
            <input id="fridgeMax" name="maxTemp" type="number" step="0.1" value="8" />
            <label for="fridgeLocation">Location</label>
            <input id="fridgeLocation" name="location" placeholder="Pharmacy store room" />
            <label for="fridgeNotes">Notes</label>
            <input id="fridgeNotes" name="notes" placeholder="Optional notes" />
            <button class="pill-button" type="submit">Register fridge</button>
          </form>
        </section>

        <section class="panel">
          <div class="panel-header">
            <h3>Record live temperature</h3>
            <span class="panel-caption">Submit a fresh reading</span>
          </div>
          <form id="fridgeReadingForm" class="compact-form stacked-form">
            <label for="fridgeSelect">Fridge</label>
            <select id="fridgeSelect" name="fridgeId">
              ${state.fridges.map((fridge) => `<option value="${fridge.id}">${fridge.device_name}</option>`).join('')}
            </select>
            <label for="fridgeTemp">Temperature (°C)</label>
            <input id="fridgeTemp" name="temperatureC" type="number" step="0.1" placeholder="4.2" required />
            <label for="fridgeReadingNotes">Notes</label>
            <input id="fridgeReadingNotes" name="notes" placeholder="Door opened / maintenance" />
            <button class="pill-button" type="submit">Save reading</button>
          </form>
        </section>

        <section class="panel">
          <div class="panel-header">
            <h3>Connected fridges</h3>
            <span class="panel-caption">Latest reported temperatures</span>
          </div>
          <div id="fridgeList" class="stack-list"></div>
        </section>
      </div>
    `;
    document.getElementById('backButton').addEventListener('click', () => { state.currentView = 'main'; render(); });
    document.querySelectorAll('[data-nav-view]').forEach((button) => {
      button.addEventListener('click', () => {
        state.currentView = button.getAttribute('data-nav-view');
        render();
      });
    });
    document.getElementById('fridgeForm').addEventListener('submit', handleCreateFridge);
    document.getElementById('fridgeReadingForm').addEventListener('submit', handleFridgeReading);
    renderFridges();
    return;
  }

  if (state.currentView === 'ai') {
    root.innerHTML = `
      <div class="app-shell">
        <header class="app-header">
          <div class="app-title-block">
            <p class="eyebrow">Mobile web</p>
            <h1>AI guidance</h1>
            <p class="subtle">Forecasts, risk alerts, and next actions</p>
          </div>
          <button id="backButton" class="secondary-button">Back</button>
        </header>

        <div class="view-nav">
          <button class="view-pill" data-nav-view="main">Overview</button>
          <button class="view-pill" data-nav-view="audits">Audits</button>
          <button class="view-pill" data-nav-view="fridges">Fridges</button>
          <button class="view-pill active" data-nav-view="ai">AI guidance</button>
        </div>

        <section class="panel">
          <div class="panel-header">
            <h3>Forecasts</h3>
            <span class="panel-caption">Usage outlook</span>
          </div>
          <div id="aiForecastList" class="stack-list"></div>
        </section>

        <section class="panel">
          <div class="panel-header">
            <h3>Expiry risk</h3>
            <span class="panel-caption">Transfer or reduce ordering</span>
          </div>
          <div id="aiRiskList" class="stack-list"></div>
        </section>
      </div>
    `;
    document.getElementById('backButton').addEventListener('click', () => { state.currentView = 'main'; render(); });
    document.querySelectorAll('[data-nav-view]').forEach((button) => {
      button.addEventListener('click', () => {
        state.currentView = button.getAttribute('data-nav-view');
        render();
      });
    });
    renderAiGuidance();
    return;
  }

  const item = selectedItem();
  root.innerHTML = `
    <div class="app-shell">
      <header class="app-header">
        <div class="app-title-block">
          <p class="eyebrow">Mobile web</p>
          <h1>Taboryx AI</h1>
          <p class="subtle">Pharmacy inventory at a glance</p>
        </div>
        <button id="refreshButton" class="pill-button">Refresh</button>
      </header>

      <div class="view-nav">
        <button class="view-pill active" data-nav-view="main">Overview</button>
        <button class="view-pill" data-nav-view="audits">Audits</button>
        <button class="view-pill" data-nav-view="fridges">Fridges</button>
        <button class="view-pill" data-nav-view="ai">AI guidance</button>
      </div>

      <section class="hero-card">
        <div class="hero-copy">
          <p class="eyebrow">Live overview</p>
          <h2>Monitor stock, expiry, and usage from your phone.</h2>
          <p class="subtle">Signed in securely to the same backend as the desktop system.</p>
        </div>
        <div class="hero-badge">iPhone ready</div>
      </section>

      <section class="quick-actions">
        <article class="quick-action-card">
          <strong>Low stock</strong>
          <div class="meta">Watch shortage risk before it hits the ward</div>
        </article>
        <article class="quick-action-card">
          <strong>Expiring soon</strong>
          <div class="meta">Review items close to expiry and transfer early</div>
        </article>
      </section>

      <section class="panel">
        <div class="panel-header">
          <h3>Search inventory</h3>
          <span class="panel-caption">Find stock fast</span>
        </div>
        <form id="searchForm" class="compact-form">
          <input id="searchInput" name="search" value="${state.searchQuery}" placeholder="Search by name or category" />
          <button class="pill-button" type="submit">Search</button>
        </form>
        ${state.feedback ? `<div class="${state.feedbackKind === 'error' ? 'error-text' : 'subtle'}">${state.feedback}</div>` : ''}
      </section>

      <section class="panel">
        <div class="panel-header">
          <h3>Scan lookup</h3>
          <span class="panel-caption">Barcode or QR code</span>
        </div>
        <form id="scanForm" class="compact-form">
          <input id="scanInput" name="scanCode" value="${state.scanCode}" placeholder="Enter barcode or QR code" />
          <button class="pill-button" type="submit">Lookup</button>
        </form>
      </section>

      ${item ? `
        <section class="panel">
          <div class="panel-header">
            <h3>Quick stock movement</h3>
            <span class="panel-caption">${item.item_name}</span>
          </div>
          <form id="movementForm" class="compact-form stacked-form">
            <label for="movementType">Action</label>
            <select id="movementType" name="movementType">
              <option value="ISSUED">Issued</option>
              <option value="RECEIVED">Received</option>
              <option value="ADJUSTED">Adjusted</option>
              <option value="RETURNED">Returned</option>
            </select>
            <label for="movementQuantity">Quantity</label>
            <input id="movementQuantity" name="quantity" type="number" min="1" value="1" required />
            <label for="movementRoom">Room</label>
            <input id="movementRoom" name="room" value="${item.clinical_room || ''}" placeholder="Optional room" />
            <label for="movementReason">Reason</label>
            <input id="movementReason" name="reason" placeholder="Reason for this movement" />
            <button class="pill-button" type="submit">Record movement</button>
          </form>
        </section>
      ` : ''}

      <section class="stats-grid" id="statsGrid"></section>

      <section class="panel">
        <div class="panel-header">
          <h3>Items needing attention</h3>
          <span class="panel-caption">Tap an item to open details</span>
        </div>
        <div id="inventoryList" class="stack-list"></div>
      </section>

      <section class="panel">
        <div class="panel-header">
          <h3>Recent stock movements</h3>
          <span class="panel-caption">Latest actions</span>
        </div>
        <div id="movementList" class="stack-list"></div>
      </section>

      <section class="panel">
        <div class="panel-header">
          <h3>Forecasts & expiry risk</h3>
          <span class="panel-caption">AI guidance</span>
        </div>
        <div id="insightList" class="stack-list"></div>
      </section>

      <section class="panel install-panel">
        <h3>Add to your Home Screen</h3>
        <p>On iPhone, tap Share and choose “Add to Home Screen” for the fastest access.</p>
        <p class="subtle">After install, the app opens in full-screen with a more native feel.</p>
      </section>
    </div>
  `;
  document.getElementById('refreshButton').addEventListener('click', loadData);
  document.getElementById('searchForm').addEventListener('submit', handleSearch);
  document.getElementById('scanForm').addEventListener('submit', handleScan);
  document.querySelectorAll('[data-nav-view]').forEach((button) => {
    button.addEventListener('click', () => {
      state.currentView = button.getAttribute('data-nav-view');
      render();
    });
  });
  if (item) {
    document.getElementById('movementForm').addEventListener('submit', handleMovement);
  }
  renderStats();
  renderInventory();
  renderMovements();
  renderInsights();
}

function renderStats() {
  const grid = document.getElementById('statsGrid');
  if (!state.dashboard) return;
  grid.innerHTML = buildStats(state.dashboard)
    .map((card) => `
      <article class="stat-card">
        <p class="eyebrow">${card.label}</p>
        <div class="value">${card.value}</div>
      </article>
    `).join('');
}

function renderAudits() {
  const container = document.getElementById('auditList');
  if (!container) return;
  if (!state.audits.length) {
    container.innerHTML = '<div class="empty-state">No room audits have been recorded yet.</div>';
    return;
  }

  container.innerHTML = state.audits.slice(0, 8).map((audit) => {
    const roomName = getRoomName(audit.room_id);
    const status = (audit.status || 'Pending').toUpperCase();
    const stats = [
      audit.total_items_checked != null ? `${audit.total_items_checked} checked` : null,
      audit.missing_items_count != null ? `${audit.missing_items_count} missing` : null,
      audit.expired_items_count != null ? `${audit.expired_items_count} expired` : null,
    ].filter(Boolean).join(' • ');

    return `
      <article class="list-item audit-card">
        <div class="row-between">
          <strong>${roomName}</strong>
          <span class="subtle-pill">${status}</span>
        </div>
        <div class="meta">${audit.audit_date || 'Unknown date'}${audit.audit_time ? ` • ${audit.audit_time}` : ''}</div>
        <div class="meta">${stats || 'No detail recorded'}</div>
        <div class="meta">${audit.notes || 'Audit completed from the mobile companion view.'}</div>
      </article>
    `;
  }).join('');
}

function renderFridges() {
  const container = document.getElementById('fridgeList');
  if (!container) return;
  if (!state.fridges.length) {
    container.innerHTML = '<div class="empty-state">No Wi-Fi fridges are registered yet.</div>';
    return;
  }

  container.innerHTML = state.fridges.map((fridge) => {
    const temp = fridge.latest_temperature_c != null ? `${fridge.latest_temperature_c}°C` : 'No reading yet';
    const status = fridge.latest_status || 'normal';
    const suffix = fridge.latest_recorded_at ? ` • ${fridge.latest_recorded_at}` : '';
    return `
      <article class="list-item audit-card">
        <div class="row-between">
          <strong>${fridge.device_name}</strong>
          <span class="subtle-pill">${status}</span>
        </div>
        <div class="meta">${temp}${suffix}</div>
        <div class="meta">${fridge.location || fridge.room_name || 'Pharmacy'} • ${fridge.min_temperature ?? '—'}°C to ${fridge.max_temperature ?? '—'}°C</div>
        <div class="meta">${fridge.endpoint_url || 'Manual entry / Wi-Fi endpoint'}</div>
      </article>
    `;
  }).join('');
}

function renderAiGuidance() {
  const forecastContainer = document.getElementById('aiForecastList');
  const riskContainer = document.getElementById('aiRiskList');
  if (!forecastContainer || !riskContainer) return;

  const forecasts = state.insights.filter((item) => item.forecast_next_month !== undefined || item.forecast_next_quarter !== undefined || item.forecast_next_year !== undefined);
  const risks = state.insights.filter((item) => item.reason && !item.forecast_next_month && !item.forecast_next_quarter && !item.forecast_next_year);

  if (!forecasts.length) {
    forecastContainer.innerHTML = '<div class="empty-state">No forecasting data is available yet.</div>';
  } else {
    forecastContainer.innerHTML = forecasts.slice(0, 6).map((item) => `
      <article class="list-item insight-card">
        <div class="row-between">
          <strong>${item.name || item.item_name || 'Forecast'}</strong>
          <span class="subtle-pill">${item.shortage_risk || item.risk_level || 'Watch'}</span>
        </div>
        <div class="meta">Next month ${item.forecast_next_month ?? '—'} • Next quarter ${item.forecast_next_quarter ?? '—'}</div>
        <div class="meta">Next year ${item.forecast_next_year ?? '—'} • Confidence ${item.confidence || 'high'}</div>
      </article>
    `).join('');
  }

  if (!risks.length) {
    riskContainer.innerHTML = '<div class="empty-state">No expiry countermeasures are flagged right now.</div>';
  } else {
    riskContainer.innerHTML = risks.slice(0, 6).map((item) => `
      <article class="list-item insight-card">
        <div class="row-between">
          <strong>${item.name || item.item_name || 'Risk'}</strong>
          <span class="subtle-pill">${item.confidence || 'high'}</span>
        </div>
        <div class="meta">${item.reason || item.summary || 'AI recommendation available'}</div>
      </article>
    `).join('');
  }
}

function renderInventory() {
  const container = document.getElementById('inventoryList');
  if (!state.inventory.length) {
    container.innerHTML = '<div class="empty-state">No inventory items received yet.</div>';
    return;
  }

  container.innerHTML = state.inventory.slice(0, 8).map((item) => `
    <button class="list-item" data-item-id="${item.id}">
      <strong>${item.item_name || item.name || 'Unnamed item'}</strong>
      <div class="meta">Qty ${item.current_quantity ?? item.quantity ?? 0} • Min ${item.minimum_quantity ?? 0} • ${item.category || 'Inventory'}</div>
      <div class="meta">Status: ${item.stock_status || item.status || 'Active'}</div>
    </button>
  `).join('');
  container.querySelectorAll('[data-item-id]').forEach((button) => {
    button.addEventListener('click', () => {
      state.selectedItemId = button.getAttribute('data-item-id');
      state.currentView = 'main';
      state.feedback = 'Selected item ready for movement';
      state.feedbackKind = 'info';
      render();
    });
  });
}

function renderMovements() {
  const container = document.getElementById('movementList');
  if (!state.movements.length) {
    container.innerHTML = '<div class="empty-state">No movement history available yet.</div>';
    return;
  }

  container.innerHTML = state.movements.slice(0, 8).map((movement) => `
    <article class="list-item">
      <strong>${movement.movement_type || movement.type || 'Movement'}</strong>
      <div class="meta">${movement.reason || 'No reason provided'}</div>
      <div class="meta">${movement.movement_date || movement.date || 'Unknown date'}</div>
    </article>
  `).join('');
}

function renderInsights() {
  const container = document.getElementById('insightList');
  if (!container) return;
  if (!state.insights.length) {
    container.innerHTML = '<div class="empty-state">No AI insight data yet.</div>';
    return;
  }

  container.innerHTML = state.insights.slice(0, 8).map((item) => `
    <article class="list-item insight-card">
      <div class="row-between">
        <strong>${item.name || item.item_name || 'Insight'}</strong>
        <span class="subtle-pill">${item.shortage_risk || item.risk_level || 'Watch'}</span>
      </div>
      <div class="meta">${item.reason || item.summary || 'AI recommendation available'}</div>
      <div class="meta">${item.forecast_next_month !== undefined ? `Next month ${item.forecast_next_month}` : ''}${item.confidence ? ` • Confidence ${item.confidence}` : ''}</div>
    </article>
  `).join('');
}

async function fetchJson(path, options = {}) {
  const headers = { Accept: 'application/json', ...(options.headers || {}) };
  const response = await fetch(path, { ...options, headers });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed: ${response.status}`);
  }
  return response.json();
}

async function handleLogin(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const username = form.username.value.trim();
  const password = form.password.value;
  state.error = '';
  state.feedback = '';
  try {
    const result = await fetchJson('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    state.token = result.token || '';
    localStorage.setItem('Taboryx_token', state.token);
    state.currentView = 'main';
    render();
    await loadData();
  } catch (error) {
    state.error = error.message;
    render();
  }
}

async function handleSearch(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const query = form.search.value.trim();
  state.searchQuery = query;
  state.feedback = '';
  if (!query) {
    state.feedback = 'Enter a search term to find inventory';
    state.feedbackKind = 'info';
    render();
    return;
  }

  try {
    const result = await fetchJson(`/api/v1/inventory?q=${encodeURIComponent(query)}&limit=12`, {
      headers: { Authorization: `Bearer ${state.token}` },
    });
    state.inventory = result.items || [];
    state.feedback = `Showing ${state.inventory.length} matching items`;
    state.feedbackKind = 'info';
    render();
  } catch (error) {
    state.feedback = error.message;
    state.feedbackKind = 'error';
    render();
  }
}

async function handleScan(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const code = form.scanCode.value.trim();
  state.scanCode = code;
  state.feedback = '';
  if (!code) {
    state.feedback = 'Enter a barcode or QR code';
    state.feedbackKind = 'error';
    render();
    return;
  }

  try {
    const result = await fetchJson('/api/v1/scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${state.token}` },
      body: JSON.stringify({ code }),
    });
    if (result.found && result.item) {
      state.selectedItemId = result.item.id;
      state.inventory = [result.item, ...state.inventory.filter((entry) => String(entry.id) !== String(result.item.id))];
      state.feedback = result.message;
      state.feedbackKind = 'info';
      render();
      return;
    }
    state.feedback = result.message || 'Item not found';
    state.feedbackKind = 'error';
    render();
  } catch (error) {
    state.feedback = error.message;
    state.feedbackKind = 'error';
    render();
  }
}

async function handleMovement(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const item = selectedItem();
  if (!item) {
    state.feedback = 'Select an item first';
    state.feedbackKind = 'error';
    render();
    return;
  }

  const payload = {
    item_id: item.id,
    movement_type: form.movementType.value,
    quantity: form.quantity.value,
    room: form.room.value.trim(),
    reason: form.reason.value.trim(),
  };

  try {
    const result = await fetchJson('/api/v1/stock-movement', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${state.token}` },
      body: JSON.stringify(payload),
    });
    state.feedback = result.message || 'Stock movement recorded';
    state.feedbackKind = 'info';
    await loadData();
  } catch (error) {
    state.feedback = error.message;
    state.feedbackKind = 'error';
    render();
  }
}

async function handleCreateFridge(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = {
    device_name: form.deviceName.value.trim(),
    room_id: form.roomId.value || null,
    device_code: form.deviceCode.value.trim(),
    endpoint_url: form.endpointUrl.value.trim(),
    min_temperature: form.minTemp.value,
    max_temperature: form.maxTemp.value,
    location: form.location.value.trim(),
    notes: form.notes.value.trim(),
  };

  try {
    const result = await fetchJson('/api/v1/fridges', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${state.token}` },
      body: JSON.stringify(payload),
    });
    state.feedback = result.message || 'Fridge registered';
    state.feedbackKind = 'info';
    state.currentView = 'fridges';
    await loadData();
  } catch (error) {
    state.feedback = error.message;
    state.feedbackKind = 'error';
    render();
  }
}

async function handleFridgeReading(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = {
    fridge_id: form.fridgeId.value,
    temperature_c: form.temperatureC.value,
    notes: form.notes.value.trim(),
    source: 'wifi',
  };

  try {
    const result = await fetchJson('/api/v1/fridge-readings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${state.token}` },
      body: JSON.stringify(payload),
    });
    state.feedback = result.message || 'Fridge reading saved';
    state.feedbackKind = 'info';
    state.currentView = 'fridges';
    await loadData();
  } catch (error) {
    state.feedback = error.message;
    state.feedbackKind = 'error';
    render();
  }
}

async function loadData() {
  if (!state.token) {
    state.currentView = 'login';
    render();
    return;
  }

  const statusText = document.querySelector('.hero-card .subtle');
  if (statusText) statusText.textContent = 'Refreshing live inventory data...';
  const [dashboard, inventory, movements, forecasts, expiryRisk, audits, rooms, fridges] = await Promise.all([
    fetchJson('/api/v1/dashboard', { headers: { Authorization: `Bearer ${state.token}` } }),
    fetchJson('/api/v1/inventory?limit=12', { headers: { Authorization: `Bearer ${state.token}` } }),
    fetchJson('/api/v1/movements?limit=8', { headers: { Authorization: `Bearer ${state.token}` } }),
    fetchJson('/api/v1/ai/forecasts', { headers: { Authorization: `Bearer ${state.token}` } }),
    fetchJson('/api/v1/ai/expiry-risk?days=90', { headers: { Authorization: `Bearer ${state.token}` } }),
    fetchJson('/api/v1/audits', { headers: { Authorization: `Bearer ${state.token}` } }),
    fetchJson('/api/v1/rooms', { headers: { Authorization: `Bearer ${state.token}` } }),
    fetchJson('/api/v1/fridges', { headers: { Authorization: `Bearer ${state.token}` } }),
  ]);

  const forecastRows = Array.isArray(forecasts) ? forecasts : (forecasts?.forecasts || []);
  const expiryRows = Array.isArray(expiryRisk) ? expiryRisk : (expiryRisk?.items || []);

  state.dashboard = dashboard;
  state.inventory = inventory.items || [];
  state.movements = movements.movements || [];
  state.audits = (audits && audits.audits) || [];
  state.rooms = (rooms && rooms.rooms) || [];
  state.fridges = (fridges && fridges.fridges) || [];
  state.insights = [
    ...forecastRows,
    ...expiryRows.map((item) => ({
      name: item.item_name || item.name || 'Expiry risk',
      reason: `Expires ${item.expiry_date || 'soon'} • risk ${item.risk_level || 'medium'}`,
      confidence: item.confidence || 'high',
      risk_level: item.risk_level || 'medium',
    })),
  ];

  if (!state.selectedItemId && state.inventory.length) {
    state.selectedItemId = state.inventory[0].id;
  }

  render();
}

window.addEventListener('DOMContentLoaded', async () => {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  }

  if (state.token) {
    state.currentView = 'main';
  }

  try {
    if (state.currentView === 'main') {
      await loadData();
    } else {
      render();
    }
  } catch (error) {
    state.error = error.message;
    state.currentView = 'login';
    render();
  }
});
