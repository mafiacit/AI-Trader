// Charts and visualization
document.addEventListener('DOMContentLoaded', function() {
    // Initialize the market chart if the element exists
    const marketChartEl = document.getElementById('marketChart');
    if (marketChartEl) {
        initializeMarketChart(marketChartEl);
    }
    
    // Initialize trade buttons
    setupTradeButtons();
    
    // Setup timeframe selector
    setupTimeframeSelector();
    
    // Initialize currency pair selector
    setupCurrencySelector();
    
    // Initialize risk analysis functionality
    setupRiskAnalyzer();
});

// Initialize market chart with historical data
function initializeMarketChart(chartEl) {
    const currencyPair = chartEl.getAttribute('data-currency') || 'EURUSD';
    const timeframe = chartEl.getAttribute('data-timeframe') || '1d';
    
    // Fetch historical data from the API
    fetch(`/api/market_data/${currencyPair}?timeframe=${timeframe}`)
        .then(response => response.json())
        .then(data => {
            // Extract dates and prices for the chart
            const dates = data.map(item => item.date);
            const prices = data.map(item => item.close);
            
            // Create chart
            const ctx = chartEl.getContext('2d');
            const marketChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: dates,
                    datasets: [{
                        label: `${currencyPair} Price`,
                        data: prices,
                        borderColor: '#7CB9E8',
                        borderWidth: 2,
                        pointRadius: 0,
                        pointHoverRadius: 5,
                        pointHoverBackgroundColor: '#7CB9E8',
                        pointHoverBorderColor: '#fff',
                        fill: false,
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                        },
                        legend: {
                            position: 'top',
                            labels: {
                                color: '#eee'
                            }
                        }
                    },
                    scales: {
                        x: {
                            ticks: {
                                color: '#ccc',
                                maxRotation: 45,
                                minRotation: 45
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.05)'
                            }
                        },
                        y: {
                            ticks: {
                                color: '#ccc'
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.05)'
                            }
                        }
                    }
                }
            });
        })
        .catch(error => {
            console.error('Error fetching market data:', error);
            chartEl.innerHTML = '<div class="alert alert-danger">Failed to load chart data</div>';
        });
}

// Setup trade buttons
function setupTradeButtons() {
    // Buy button
    const buyButton = document.getElementById('buyButton');
    if (buyButton) {
        buyButton.addEventListener('click', function() {
            const currencyPair = document.getElementById('currencyPair').value;
            const amount = document.getElementById('tradeAmount').value;
            
            // Create form data
            const formData = new FormData();
            formData.append('action', 'buy');
            formData.append('currency_pair', currencyPair);
            formData.append('amount', amount);
            
            // Submit the form
            fetch('/trading', {
                method: 'POST',
                body: formData
            })
            .then(response => response.text())
            .then(html => {
                document.getElementById('tradeResults').innerHTML = html;
            })
            .catch(error => {
                console.error('Error executing trade:', error);
                document.getElementById('tradeResults').innerHTML = 
                    '<div class="alert alert-danger">Failed to execute trade</div>';
            });
        });
    }
    
    // Sell button
    const sellButton = document.getElementById('sellButton');
    if (sellButton) {
        sellButton.addEventListener('click', function() {
            const currencyPair = document.getElementById('currencyPair').value;
            const amount = document.getElementById('tradeAmount').value;
            
            // Create form data
            const formData = new FormData();
            formData.append('action', 'sell');
            formData.append('currency_pair', currencyPair);
            formData.append('amount', amount);
            
            // Submit the form
            fetch('/trading', {
                method: 'POST',
                body: formData
            })
            .then(response => response.text())
            .then(html => {
                document.getElementById('tradeResults').innerHTML = html;
            })
            .catch(error => {
                console.error('Error executing trade:', error);
                document.getElementById('tradeResults').innerHTML = 
                    '<div class="alert alert-danger">Failed to execute trade</div>';
            });
        });
    }
    
    // Auto trade button
    const autoTradeButton = document.getElementById('autoTradeButton');
    if (autoTradeButton) {
        autoTradeButton.addEventListener('click', function() {
            const currencyPair = document.getElementById('currencyPair').value;
            const amount = document.getElementById('tradeAmount').value;
            
            // Create form data
            const formData = new FormData();
            formData.append('action', 'auto');
            formData.append('currency_pair', currencyPair);
            formData.append('amount', amount);
            
            // Submit the form
            fetch('/trading', {
                method: 'POST',
                body: formData
            })
            .then(response => response.text())
            .then(html => {
                document.getElementById('tradeResults').innerHTML = html;
            })
            .catch(error => {
                console.error('Error executing trade:', error);
                document.getElementById('tradeResults').innerHTML = 
                    '<div class="alert alert-danger">Failed to execute auto trade</div>';
            });
        });
    }
}

// Setup timeframe selector
function setupTimeframeSelector() {
    const timeframeSelector = document.getElementById('timeframeSelector');
    if (timeframeSelector) {
        timeframeSelector.addEventListener('change', function() {
            const currencyPair = document.getElementById('currencyPair').value;
            const timeframe = this.value;
            
            // Redirect to analysis page with selected timeframe
            window.location.href = `/analyze/${currencyPair}?timeframe=${timeframe}`;
        });
    }
}

// Setup currency pair selector
function setupCurrencySelector() {
    const currencySelector = document.getElementById('currencyPair');
    if (currencySelector) {
        currencySelector.addEventListener('change', function() {
            const analysisButton = document.getElementById('analyzeButton');
            if (analysisButton) {
                analysisButton.click();
            }
        });
    }
}

// Update indicator displays
function updateIndicatorDisplay(indicators) {
    const indicatorElements = document.querySelectorAll('[data-indicator]');
    
    indicatorElements.forEach(el => {
        const indicator = el.getAttribute('data-indicator');
        if (indicators && indicators[indicator] !== undefined) {
            el.textContent = indicators[indicator];
            
            // Add color coding for some indicators
            if (indicator === 'rsi') {
                if (indicators[indicator] > 70) {
                    el.classList.add('text-danger');
                } else if (indicators[indicator] < 30) {
                    el.classList.add('text-success');
                } else {
                    el.classList.add('text-warning');
                }
            }
        }
    });
}

// Format currency value
function formatCurrency(value, decimals = 5) {
    return Number(value).toFixed(decimals);
}

// Setup risk analyzer functionality
function setupRiskAnalyzer() {
    const analyzeRiskButton = document.getElementById('analyzeRiskButton');
    if (!analyzeRiskButton) return;
    
    analyzeRiskButton.addEventListener('click', function() {
        // Get form values
        const currencyPair = document.getElementById('riskCurrencyPair').value;
        const tradeType = document.getElementById('riskTradeType').value;
        const amount = parseFloat(document.getElementById('riskAmount').value);
        const leverage = parseInt(document.getElementById('riskLeverage').value);
        const stopLoss = document.getElementById('riskStopLoss').value ? parseFloat(document.getElementById('riskStopLoss').value) : null;
        const takeProfit = document.getElementById('riskTakeProfit').value ? parseFloat(document.getElementById('riskTakeProfit').value) : null;
        const includePortfolio = document.getElementById('includePortfolio').checked;
        
        // Show loading indicator
        document.getElementById('riskAnalysisResults').classList.add('d-none');
        document.getElementById('riskAnalysisError').classList.add('d-none');
        document.getElementById('riskAnalysisLoading').classList.remove('d-none');
        
        // Create request payload
        const payload = {
            trade_details: {
                trade_type: tradeType,
                amount: amount,
                leverage: leverage,
            },
            currency_pair: currencyPair,
            include_portfolio: includePortfolio
        };
        
        // Add optional fields if they exist
        if (stopLoss) payload.trade_details.stop_loss = stopLoss;
        if (takeProfit) payload.trade_details.take_profit = takeProfit;
        
        // Call the API
        fetch('/api/analyze_risk', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Hide loading indicator
            document.getElementById('riskAnalysisLoading').classList.add('d-none');
            
            if (data.status === 'success') {
                // Display risk analysis results
                displayRiskAnalysis(data.risk_analysis);
            } else {
                // Show error
                document.getElementById('riskAnalysisError').classList.remove('d-none');
                document.getElementById('riskAnalysisErrorMessage').textContent = data.message || 'Unknown error occurred';
            }
        })
        .catch(error => {
            console.error('Error analyzing trade risk:', error);
            // Hide loading indicator and show error
            document.getElementById('riskAnalysisLoading').classList.add('d-none');
            document.getElementById('riskAnalysisError').classList.remove('d-none');
            document.getElementById('riskAnalysisErrorMessage').textContent = `Error: ${error.message}`;
        });
    });
    
    // Set up automatic price updates when currency pair changes
    const riskCurrencyPair = document.getElementById('riskCurrencyPair');
    if (riskCurrencyPair) {
        riskCurrencyPair.addEventListener('change', function() {
            // In a real app, you would fetch current price for the selected currency pair
            // and update the entry price, stop loss, and take profit fields
            console.log('Currency pair changed to:', this.value);
        });
    }
}

// Display risk analysis results in the UI
function displayRiskAnalysis(analysis) {
    if (!analysis) return;
    
    // Show results container
    const resultsContainer = document.getElementById('riskAnalysisResults');
    resultsContainer.classList.remove('d-none');
    
    // Update summary information
    document.getElementById('riskLevel').textContent = analysis.risk_level || 'Unknown';
    
    // Set appropriate color for risk level
    const riskLevel = document.getElementById('riskLevel');
    riskLevel.className = 'fw-bold'; // Reset classes
    switch(analysis.risk_level?.toLowerCase()) {
        case 'low':
            riskLevel.classList.add('text-success');
            break;
        case 'moderate':
            riskLevel.classList.add('text-warning');
            break;
        case 'high':
            riskLevel.classList.add('text-danger');
            break;
        case 'extreme':
            riskLevel.classList.add('text-danger', 'fw-bolder');
            break;
        default:
            riskLevel.classList.add('text-muted');
    }
    
    // Risk score and progress bar
    const riskScore = document.getElementById('riskScore');
    const riskScoreBar = document.getElementById('riskScoreBar');
    const score = parseInt(analysis.risk_score) || 0;
    
    riskScore.textContent = score;
    riskScoreBar.style.width = `${score}%`;
    
    // Set color of risk score bar
    riskScoreBar.className = 'progress-bar'; // Reset classes
    if (score < 30) {
        riskScoreBar.classList.add('bg-success');
    } else if (score < 60) {
        riskScoreBar.classList.add('bg-warning');
    } else {
        riskScoreBar.classList.add('bg-danger');
    }
    
    // Fill in other metrics
    document.getElementById('maxDrawdown').textContent = analysis.maximum_drawdown_percent ? `${analysis.maximum_drawdown_percent}%` : 'N/A';
    document.getElementById('maxLoss').textContent = analysis.maximum_loss_amount ? `$${analysis.maximum_loss_amount}` : 'N/A';
    document.getElementById('riskReward').textContent = analysis.risk_reward_ratio || 'N/A';
    document.getElementById('positionSizing').textContent = analysis.position_sizing_recommendation || 'N/A';
    document.getElementById('leverageRecommendation').textContent = analysis.leverage_recommendation || 'N/A';
    
    // Risk factors
    const riskFactorsList = document.getElementById('riskFactorsList');
    riskFactorsList.innerHTML = ''; // Clear existing items
    
    if (analysis.risk_factors && analysis.risk_factors.length > 0) {
        analysis.risk_factors.forEach(factor => {
            const item = document.createElement('li');
            item.className = 'list-group-item bg-dark border-light';
            
            // Create risk factor item with icon and formatted text
            const factorImpactClass = factor.impact === 'high' ? 'text-danger' : 
                                     (factor.impact === 'medium' ? 'text-warning' : 'text-info');
            
            item.innerHTML = `
                <div class="d-flex align-items-start">
                    <i class="fas fa-exclamation-triangle mt-1 me-2 ${factorImpactClass}"></i>
                    <div>
                        <strong>${factor.factor}</strong>
                        <div class="text-muted">${factor.description}</div>
                    </div>
                </div>
            `;
            
            riskFactorsList.appendChild(item);
        });
    } else {
        const item = document.createElement('li');
        item.className = 'list-group-item bg-dark border-light text-muted';
        item.textContent = 'No specific risk factors identified.';
        riskFactorsList.appendChild(item);
    }
    
    // Protective measures
    const protectiveMeasuresList = document.getElementById('protectiveMeasuresList');
    protectiveMeasuresList.innerHTML = ''; // Clear existing items
    
    if (analysis.protective_measures && analysis.protective_measures.length > 0) {
        analysis.protective_measures.forEach(measure => {
            const item = document.createElement('li');
            item.className = 'list-group-item bg-dark border-light';
            
            item.innerHTML = `
                <div class="d-flex align-items-start">
                    <i class="fas fa-shield-alt mt-1 me-2 text-info"></i>
                    <div>${measure}</div>
                </div>
            `;
            
            protectiveMeasuresList.appendChild(item);
        });
    } else {
        const item = document.createElement('li');
        item.className = 'list-group-item bg-dark border-light text-muted';
        item.textContent = 'No specific protective measures suggested.';
        protectiveMeasuresList.appendChild(item);
    }
    
    // Overall assessment
    document.getElementById('overallAssessment').textContent = analysis.overall_assessment || 'No overall assessment provided.';
}
