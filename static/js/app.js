// Trading Bot ML - Aplicación Frontend

let socket;
let currentTab = 'dashboard';

// Inicializar aplicación
document.addEventListener('DOMContentLoaded', function() {
    initializeSocket();
    setupNavigation();
    loadInitialData();
    setupEventListeners();
});

// Configurar Socket.IO
function initializeSocket() {
    socket = io();
    
    socket.on('connect', function() {
        console.log('Conectado al servidor');
        document.getElementById('connection-status').classList.add('connected');
        document.getElementById('status-text').textContent = 'Conectado';
    });
    
    socket.on('disconnect', function() {
        console.log('Desconectado del servidor');
        document.getElementById('connection-status').classList.remove('connected');
        document.getElementById('status-text').textContent = 'Desconectado';
    });
    
    socket.on('signals_update', function(data) {
        updateSignalsDisplay(data.signals);
    });
    
    socket.on('simulator_stats', function(stats) {
        updateSimulatorStats(stats);
    });
    
    socket.on('supervisor_update', function(status) {
        updateSupervisorDisplay(status);
    });
    
    socket.on('prices_update', function(data) {
        updatePricesDisplay(data.prices);
    });
}

// Configurar navegación entre pestañas
function setupNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    
    navItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Remover clase active de todos
            navItems.forEach(nav => nav.classList.remove('active'));
            
            // Añadir a este
            this.classList.add('active');
            
            // Cambar tab
            const tabId = this.getAttribute('data-tab');
            switchTab(tabId);
        });
    });
}

// Cambiar pestaña activa
function switchTab(tabId) {
    // Ocultar todas las pestañas
    document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.remove('active');
    });
    
    // Mostrar la seleccionada
    document.getElementById(tabId).classList.add('active');
    
    // Actualizar breadcrumb
    const pageNames = {
        'dashboard': 'Dashboard',
        'signals': 'Señales',
        'trades': 'Operaciones',
        'analytics': 'Analytics',
        'ml-status': 'Machine Learning',
        'supervisor': 'Supervisor LLM',
        'settings': 'Configuración'
    };
    
    document.getElementById('current-page').textContent = pageNames[tabId] || tabId;
    currentTab = tabId;
    
    // Cargar datos específicos de la pestaña
    loadTabData(tabId);
}

// Cargar datos iniciales
async function loadInitialData() {
    try {
        await loadStatus();
        await loadSettings();
    } catch (error) {
        console.error('Error cargando datos iniciales:', error);
    }
}

// Cargar estado general
async function loadStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        if (data.simulator_stats) {
            updateSimulatorStats(data.simulator_stats);
        }
        
        if (data.supervisor_status) {
            updateSupervisorDisplay(data.supervisor_status);
        }
        
        if (data.ml_stats) {
            updateMLModelsDisplay(data.ml_stats);
        }
        
        // Actualizar modo actual
        if (data.current_mode) {
            const modeNames = {
                'safe': 'Segura',
                'normal': 'Normal',
                'aggressive': 'Agresiva',
                'very_active': 'Muy Activa'
            };
            document.getElementById('current-mode').textContent = modeNames[data.current_mode] || data.current_mode;
        }
    } catch (error) {
        console.error('Error cargando estado:', error);
    }
}

// Cargar configuración
async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        const settings = await response.json();
        
        if (settings.timeframe) {
            document.getElementById('setting-timeframe').value = settings.timeframe;
            document.getElementById('timeframe-select').value = settings.timeframe;
        }
        
        if (settings.mode) {
            document.getElementById('setting-mode').value = settings.mode;
        }
        
        if (settings.auto_adjust !== undefined) {
            document.getElementById('auto-adjust-toggle').checked = settings.auto_adjust;
        }
        
        if (settings.symbols) {
            updateSymbolTags(settings.symbols);
        }
    } catch (error) {
        console.error('Error cargando configuración:', error);
    }
}

// Cargar datos de pestaña específica
function loadTabData(tabId) {
    switch(tabId) {
        case 'signals':
            refreshSignals();
            break;
        case 'trades':
            loadPositions();
            loadTradesHistory();
            break;
        case 'analytics':
            loadAnalytics();
            break;
        case 'ml-status':
            loadMLStatus();
            break;
        case 'supervisor':
            loadSupervisorData();
            break;
    }
}

// Actualizar estadísticas del simulador
function updateSimulatorStats(stats) {
    if (!stats) return;
    
    // Balance y equity
    document.getElementById('balance').textContent = formatCurrency(stats.current_balance || 10000);
    document.getElementById('equity').textContent = formatCurrency(stats.current_equity || 10000);
    
    // Win rate
    const winRate = stats.win_rate || 0;
    document.getElementById('win-rate').textContent = `${winRate.toFixed(1)}%`;
    
    // Trades
    document.getElementById('total-trades').textContent = stats.total_trades || 0;
    
    // Profit factor
    const pf = stats.profit_factor || 0;
    document.getElementById('profit-factor').textContent = `PF: ${pf.toFixed(2)}`;
    
    // Cambios porcentuales
    const pnlPct = stats.total_pnl_pct || 0;
    const balanceChange = document.getElementById('balance-change');
    balanceChange.textContent = `${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(2)}%`;
    balanceChange.className = `stat-change ${pnlPct >= 0 ? 'positive' : 'negative'}`;
    
    // Actualizar analytics
    document.getElementById('pf-value').textContent = pf.toFixed(2);
    document.getElementById('sharpe-value').textContent = (stats.sharpe_ratio || 0).toFixed(2);
    document.getElementById('max-dd-value').textContent = `${(stats.max_drawdown || 0).toFixed(2)}%`;
    document.getElementById('expectancy-value').textContent = formatCurrency(stats.expectancy || 0);
}

// Actualizar display de señales
function updateSignalsDisplay(signals) {
    const container = document.getElementById('signals-list');
    
    if (!signals || signals.length === 0) {
        container.innerHTML = '<div class="loading">No hay señales activas</div>';
        return;
    }
    
    container.innerHTML = signals.map(signal => `
        <div class="signal-card">
            <div class="signal-symbol">${signal.symbol}</div>
            <div class="signal-type ${signal.signal}">${signal.signal}</div>
            <div class="signal-confidence">Confianza: ${(signal.confidence * 100).toFixed(1)}%</div>
            <div class="signal-probability">Prob: ${(signal.probability * 100).toFixed(1)}%</div>
            <div class="signal-time">${new Date(signal.timestamp).toLocaleTimeString()}</div>
        </div>
    `).join('');
}

// Refrescar señales manualmente
async function refreshSignals() {
    try {
        const response = await fetch('/api/signals');
        const signals = await response.json();
        updateSignalsDisplay(signals);
    } catch (error) {
        console.error('Error refrescando señales:', error);
    }
}

// Cargar posiciones abiertas
async function loadPositions() {
    try {
        const response = await fetch('/api/positions');
        const positions = await response.json();
        
        const tbody = document.getElementById('open-positions-body');
        
        if (!positions || positions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="no-data">No hay posiciones abiertas</td></tr>';
            return;
        }
        
        tbody.innerHTML = positions.map(pos => `
            <tr>
                <td>${pos.symbol}</td>
                <td>${pos.direction}</td>
                <td>${formatPrice(pos.entry_price)}</td>
                <td>${formatPrice(pos.close_price || pos.entry_price)}</td>
                <td>${formatPrice(pos.stop_loss)}</td>
                <td>${formatPrice(pos.take_profit)}</td>
                <td class="${pos.pnl >= 0 ? 'positive' : 'negative'}">${formatCurrency(pos.pnl)}</td>
                <td class="${pos.pnl_pct >= 0 ? 'positive' : 'negative'}">${pos.pnl_pct.toFixed(2)}%</td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error cargando posiciones:', error);
    }
}

// Cargar historial de trades
async function loadTradesHistory() {
    try {
        const response = await fetch('/api/trades?limit=20');
        const trades = await response.json();
        
        const tbody = document.getElementById('trades-history-body');
        
        if (!trades || trades.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="no-data">No hay operaciones cerradas</td></tr>';
            return;
        }
        
        tbody.innerHTML = trades.map(trade => `
            <tr>
                <td>${trade.symbol}</td>
                <td>${trade.direction}</td>
                <td>${formatPrice(trade.entry_price)}</td>
                <td>${formatPrice(trade.close_price)}</td>
                <td>${trade.close_reason}</td>
                <td class="${trade.pnl >= 0 ? 'positive' : 'negative'}">${formatCurrency(trade.pnl)}</td>
                <td class="${trade.pnl_pct >= 0 ? 'positive' : 'negative'}">${trade.pnl_pct.toFixed(2)}%</td>
                <td>${new Date(trade.open_time).toLocaleString()}</td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error cargando historial:', error);
    }
}

// Cargar analytics
async function loadAnalytics() {
    // Ya se actualiza con updateSimulatorStats
    // Aquí podríamos añadir gráficos adicionales
}

// Cargar estado de ML
async function loadMLStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        if (data.ml_stats) {
            updateMLModelsDisplay(data.ml_stats);
        }
    } catch (error) {
        console.error('Error cargando ML status:', error);
    }
}

// Actualizar display de modelos ML
function updateMLModelsDisplay(mlStats) {
    const container = document.getElementById('ml-models-container');
    
    if (!mlStats) {
        container.innerHTML = '<div class="loading">Cargando...</div>';
        return;
    }
    
    container.innerHTML = Object.entries(mlStats).map(([tf, stats]) => `
        <div class="ml-model-card">
            <h4>Timeframe: ${tf.toUpperCase()}</h4>
            <div class="ml-stat">
                <span>Entrenado:</span>
                <span>${stats.is_fitted ? '✅ Sí' : '❌ No'}</span>
            </div>
            <div class="ml-stat">
                <span>Win Rate:</span>
                <span>${(stats.win_rate * 100).toFixed(1)}%</span>
            </div>
            <div class="ml-stat">
                <span>Predicciones:</span>
                <span>${stats.total_predictions}</span>
            </div>
            <div class="ml-stat">
                <span>Accuracy:</span>
                <span>${(stats.overall_accuracy * 100).toFixed(1)}%</span>
            </div>
            <div class="ml-stat">
                <span>Features:</span>
                <span>${stats.feature_count}</span>
            </div>
            ${stats.last_retrain ? `
            <div class="ml-stat">
                <span>Último Train:</span>
                <span>${new Date(stats.last_retrain).toLocaleString()}</span>
            </div>
            ` : ''}
        </div>
    `).join('');
}

// Reentrenar todos los modelos
async function retrainAll() {
    try {
        const response = await fetch('/api/ml/retrain', {
            method: 'POST'
        });
        const result = await response.json();
        
        alert('Reentrenamiento completado:\n' + JSON.stringify(result, null, 2));
        loadMLStatus();
    } catch (error) {
        console.error('Error en reentrenamiento:', error);
        alert('Error en reentrenamiento: ' + error.message);
    }
}

// Cargar datos del supervisor
async function loadSupervisorData() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        if (data.supervisor_status) {
            updateSupervisorDisplay(data.supervisor_status);
        }
    } catch (error) {
        console.error('Error cargando supervisor:', error);
    }
}

// Actualizar display del supervisor
function updateSupervisorDisplay(status) {
    if (!status) return;
    
    // Régimen de mercado
    const regimeEl = document.getElementById('market-regime');
    if (status.market_regime) {
        regimeEl.textContent = status.market_regime;
        
        // Color según régimen
        const colors = {
            'BULLISH': '#10b981',
            'BEARISH': '#ef4444',
            'NEUTRAL': '#94a3b8',
            'VOLATILE': '#f59e0b',
            'TRENDING_UP': '#10b981',
            'TRENDING_DOWN': '#ef4444'
        };
        regimeEl.style.background = colors[status.market_regime] || '#3b82f6';
    }
    
    // Análisis
    if (status.last_analysis) {
        const analysis = status.last_analysis;
        document.getElementById('analysis-content').innerHTML = `
            <p><strong>Volatilidad:</strong> ${analysis.volatility_level}</p>
            <p><strong>Momentum:</strong> ${analysis.momentum.toFixed(2)}%</p>
            <p><strong>Volumen:</strong> ${analysis.volume_analysis}</p>
            <p><strong>Riesgo:</strong> ${analysis.risk_level}</p>
            <p><strong>Confianza:</strong> ${(analysis.confidence * 100).toFixed(1)}%</p>
        `;
    }
    
    // Recomendaciones
    if (status.recent_recommendations && status.recent_recommendations.length > 0) {
        document.getElementById('recommendations-list').innerHTML = 
            status.recent_recommendations.map(rec => `<li>${rec}</li>`).join('');
    }
    
    // Performance score
    if (status.performance_metrics) {
        const metrics = status.performance_metrics;
        const scoreCircle = document.getElementById('performance-score');
        const scoreValue = scoreCircle.querySelector('.score-value');
        
        scoreValue.textContent = metrics.overall_score || 0;
        
        // Actualizar gradiente del círculo
        const percentage = metrics.overall_score || 0;
        scoreCircle.style.background = `conic-gradient(#10b981 ${percentage * 3.6}deg, #1e293b ${percentage * 3.6}deg)`;
        
        // Detalles
        const detailsEl = document.getElementById('evaluation-details');
        if (metrics.strengths || metrics.weaknesses) {
            let html = '<div style="margin-top: 1rem;">';
            
            if (metrics.strengths && metrics.strengths.length > 0) {
                html += '<div style="color: #10b981; margin-bottom: 0.5rem;"><strong>Fortalezas:</strong></div>';
                html += metrics.strengths.map(s => `<div style="padding-left: 1rem;">→ ${s}</div>`).join('');
            }
            
            if (metrics.weaknesses && metrics.weaknesses.length > 0) {
                html += '<div style="color: #ef4444; margin-top: 0.5rem; margin-bottom: 0.5rem;"><strong>Debilidades:</strong></div>';
                html += metrics.weaknesses.map(w => `<div style="padding-left: 1rem;">→ ${w}</div>`).join('');
            }
            
            html += '</div>';
            detailsEl.innerHTML = html;
        }
    }
}

// Actualizar precios
function updatePricesDisplay(prices) {
    // Podríamos actualizar displays de precio en tiempo real aquí
    console.log('Precios actualizados:', prices);
}

// Actualizar tags de símbolos
function updateSymbolTags(symbols) {
    const container = document.getElementById('symbol-tags');
    container.innerHTML = symbols.map(sym => 
        `<span class="tag">${sym}</span>`
    ).join('');
}

// Configurar event listeners
function setupEventListeners() {
    // Selector de timeframe
    document.getElementById('timeframe-select').addEventListener('change', function() {
        // Podríamos cambiar el timeframe activo aquí
        console.log('Timeframe cambiado a:', this.value);
    });
    
    // Formulario de settings
    document.getElementById('settings-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const settings = {
            timeframe: document.getElementById('setting-timeframe').value,
            mode: document.getElementById('setting-mode').value,
            auto_adjust: document.getElementById('auto-adjust-toggle').checked
        };
        
        try {
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settings)
            });
            
            const result = await response.json();
            
            if (result.success) {
                alert('Configuración guardada correctamente');
                document.getElementById('current-mode').textContent = 
                    settings.mode.charAt(0).toUpperCase() + settings.mode.slice(1);
            }
        } catch (error) {
            console.error('Error guardando configuración:', error);
            alert('Error guardando configuración');
        }
    });
}

// Utilidades
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(value);
}

function formatPrice(value) {
    if (!value) return '-';
    return value.toFixed(value < 1 ? 6 : 2);
}
