// main.js
// =========================================================================
//
// All logic waits for the full `window.load` event so the flex layout is
// finished and containers have real dimensions before we create charts.
//
// =========================================================================
window.addEventListener('load', () => {

    /* ---------- DOM refs ---------- */
    const chartContainer  = document.getElementById('chart');
    const rsiContainer    = document.getElementById('rsiChart');
    const noDataMessage   = document.getElementById('noDataMessage');
    const loadingOverlay  = document.getElementById('loadingOverlay');

    /* ---------- Globals ---------- */
    let isDarkMode = false;
    let typingTimer;
    const typingDelay = 800;              // ms
    let autoUpdateId;

    /* ---------- Chart creation ---------- */
    const grid = { vertLines:{color:'#e1e1e1'}, horzLines:{color:'#e1e1e1'} };

    const chart = LightweightCharts.createChart(chartContainer,{
        width:  chartContainer.clientWidth,
        height: chartContainer.clientHeight,
        layout:{background:{type:'solid',color:'white'},textColor:'black'},
        grid, crosshair:{mode:LightweightCharts.CrosshairMode.Normal},
        timeScale:{timeVisible:true,secondsVisible:false,timeZone:'America/New_York'},
        priceScale:{position:'right',autoScale:true}
    });

    const rsiChart = LightweightCharts.createChart(rsiContainer,{
        width:  chartContainer.clientWidth,
        height: rsiContainer.clientHeight,
        layout:{background:{type:'solid',color:'white'},textColor:'black'},
        grid, timeScale:{timeVisible:true,secondsVisible:false,timeZone:'America/New_York'},
        priceScale:{position:'right',autoScale:true}
    });

    /* ---------- Series ---------- */
    const candleSeries  = chart.addCandlestickSeries();
    const emaLine       = chart.addLineSeries({color:'blue',   lineWidth:2});
    const sma50Line     = chart.addLineSeries({color:'#6b7280',lineWidth:1,visible:false});
    const sma200Line    = chart.addLineSeries({color:'#111827',lineWidth:1,visible:false});
    const bbUpperLine   = chart.addLineSeries({color:'green',  lineWidth:1,visible:false});
    const bbLowerLine   = chart.addLineSeries({color:'red',    lineWidth:1,visible:false});
    const macdLine      = chart.addLineSeries({color:'purple', lineWidth:2,visible:false});
    const stochRsiLine  = chart.addLineSeries({color:'orange', lineWidth:2,visible:false});
    const vwapLine      = chart.addLineSeries({color:'#10b981',lineWidth:1,visible:false});
    const volumeSeries  = chart.addHistogramSeries({
        color:'#26a69a',priceFormat:{type:'volume'},priceLineVisible:false,
        scaleMargins:{top:0.8,bottom:0}
    });
    const rsiLine       = rsiChart.addLineSeries({color:'red', lineWidth:2});

    /* ---------- Helpers ---------- */
    const showLoading = () => loadingOverlay.classList.add('show');
    const hideLoading = () => loadingOverlay.classList.remove('show');
    const isTadawul   = t  => /^\d+$/.test(t);          // numeric = Tadawul code

    /* ---------- Fetch + render ---------- */
    async function fetchData(){
        const ticker     = (document.getElementById('ticker').value.trim().toUpperCase() || '^TASI');
        const timeframe  = document.getElementById('timeframe').value;
        const emaPeriod  = document.getElementById('emaPeriod').value;
        const rsiPeriod  = document.getElementById('rsiPeriod').value;

        // indicator toggles
        const EMA     = document.getElementById('toggleEMA').checked;
        const SMA50   = document.getElementById('toggleSMA50').checked;
        const SMA200  = document.getElementById('toggleSMA200').checked;
        const RSI     = document.getElementById('toggleRSI').checked;
        const MACD    = document.getElementById('toggleMACD').checked;
        const STOCH   = document.getElementById('toggleStochRSI').checked;
        const VOL     = document.getElementById('toggleVolume').checked;
        const BBANDS  = document.getElementById('toggleBBands').checked;
        const VWAP    = document.getElementById('toggleVWAP').checked;

        showLoading();

        const backendTicker = isTadawul(ticker) ? `${ticker}.SR` : ticker;
        const url = `/api/data/${backendTicker}/${timeframe}/${emaPeriod}/${rsiPeriod}` +
                    `?ema=${EMA}&sma50=${SMA50}&sma200=${SMA200}&rsi=${RSI}` +
                    `&macd=${MACD}&stochrsi=${STOCH}&volume=${VOL}` +
                    `&bbands=${BBANDS}&vwap=${VWAP}`;

        try{
            const resp = await fetch(url);
            const data = await resp.json();
            hideLoading();

            if (data.candlestick.length === 0){
                // clear everything & show message
                [candleSeries,emaLine,sma50Line,sma200Line,bbUpperLine,bbLowerLine,
                 macdLine,stochRsiLine,vwapLine,volumeSeries,rsiLine].forEach(s => s.setData([]));
                noDataMessage.classList.remove('hidden');
                return;
            }

            noDataMessage.classList.add('hidden');

            candleSeries.setData(data.candlestick);
            emaLine   .setData(EMA    ? data.ema     : []);
            sma50Line .setData(SMA50  ? data.sma50   : []); sma50Line .applyOptions({visible:SMA50});
            sma200Line.setData(SMA200 ? data.sma200  : []); sma200Line.applyOptions({visible:SMA200});
            bbUpperLine.setData(BBANDS ? data.bbands.map(d=>({time:d.time,value:d.upper})) : []);
            bbLowerLine.setData(BBANDS ? data.bbands.map(d=>({time:d.time,value:d.lower})) : []);
            bbUpperLine.applyOptions({visible:BBANDS}); bbLowerLine.applyOptions({visible:BBANDS});
            macdLine     .setData(MACD  ? data.macd     : []); macdLine    .applyOptions({visible:MACD});
            stochRsiLine .setData(STOCH ? data.stochrsi : []); stochRsiLine.applyOptions({visible:STOCH});
            vwapLine     .setData(VWAP  ? data.vwap     : []); vwapLine    .applyOptions({visible:VWAP});
            volumeSeries .setData(VOL   ? data.volume   : []);
            rsiLine      .setData(RSI   ? data.rsi      : []);

            document.getElementById('lastUpdated').textContent =
                `Last Updated: ${new Date().toLocaleTimeString()} | Symbol: ${ticker}`;

        }catch(err){
            hideLoading();
            console.error('fetchData error:',err);
        }
    }

    /* ---------- Event wiring ---------- */

    // manual search
    document.getElementById('searchButton').addEventListener('click', fetchData);

    // auto-search after typing
    document.getElementById('ticker').addEventListener('input', () => {
        clearTimeout(typingTimer);
        typingTimer = setTimeout(fetchData, typingDelay);
    });

    // auto-update
    document.getElementById('autoUpdate').addEventListener('change', e => {
        if (e.target.checked){
            const ms = document.getElementById('updateFrequency').value * 1000;
            autoUpdateId = setInterval(fetchData, ms);
        }else clearInterval(autoUpdateId);
    });

    // resize
    window.addEventListener('resize', () => {
        chart.resize(chartContainer.clientWidth, chartContainer.clientHeight);
        rsiChart.resize(rsiContainer.clientWidth , rsiContainer.clientHeight);
    });

    // theme toggle
    document.getElementById('themeToggle').addEventListener('click', toggleTheme);

    function toggleTheme(){
        const body = document.body.classList;
        const toolbar = document.getElementById('toolbar');
        const drawingBar = document.getElementById('drawingToolsBar');
        const mainContainer = document.getElementById('mainContainer');
        const watchlist = document.getElementById('watchlist');

        if (!isDarkMode){
            body.replace('bg-white','bg-gray-800'); body.replace('text-black','text-white');
            document.querySelectorAll('input,select,button')
                .forEach(el => {el.classList.remove('bg-white','text-black');
                                el.classList.add('bg-gray-700','text-white','border-gray-600');});
            toolbar.classList.replace('bg-gray-100','bg-gray-700');
            drawingBar.classList.replace('bg-gray-50','bg-gray-700');
            mainContainer.classList.replace('bg-white','bg-gray-800');
            watchlist.classList.replace('bg-gray-50','bg-gray-800');

            chart.applyOptions({layout:{background:{type:'solid',color:'#333'},textColor:'white'},
                                grid:{vertLines:{color:'#444'},horzLines:{color:'#444'}}});
            rsiChart.applyOptions({layout:{background:{type:'solid',color:'#333'},textColor:'white'},
                                   grid:{vertLines:{color:'#444'},horzLines:{color:'#444'}}});
            this.textContent='Light';
            isDarkMode = true;
        }else{
            body.replace('bg-gray-800','bg-white'); body.replace('text-white','text-black');
            document.querySelectorAll('input,select,button')
                .forEach(el => {el.classList.remove('bg-gray-700','text-white','border-gray-600');
                                el.classList.add('bg-white','text-black');});
            toolbar.classList.replace('bg-gray-700','bg-gray-100');
            drawingBar.classList.replace('bg-gray-700','bg-gray-50');
            mainContainer.classList.replace('bg-gray-800','bg-white');
            watchlist.classList.replace('bg-gray-800','bg-gray-50');

            chart.applyOptions({layout:{background:{type:'solid',color:'white'},textColor:'black'},grid});
            rsiChart.applyOptions({layout:{background:{type:'solid',color:'white'},textColor:'black'},grid});
            this.textContent='Dark';
            isDarkMode = false;
        }
    }

    /* ---------- Autocomplete ---------- */
    setupAutocomplete();

    function setupAutocomplete(){
        const tickerInput = document.getElementById('ticker');
        const list = document.getElementById('autocompleteList');

        tickerInput.addEventListener('input', () => {
            const q = tickerInput.value.trim();
            if (q.length < 1){ list.classList.add('hidden'); return; }

            fetch(`/api/search_symbols/${q}`)
                .then(r => r.json())
                .then(results => {
                    list.innerHTML = '';
                    if (results.length === 0){ list.classList.add('hidden'); return; }

                    results.forEach(r => {
                        const div = document.createElement('div');
                        div.className = 'autocomplete-item p-2 cursor-pointer text-sm';
                        div.textContent = `${r.symbol} - ${r.name}`;
                        div.addEventListener('click', () => {
                            tickerInput.value = r.symbol;
                            list.classList.add('hidden');
                            fetchData();
                        });
                        list.appendChild(div);
                    });
                    list.classList.remove('hidden');
                })
                .catch(err => console.error('autocomplete error',err));
        });

        document.addEventListener('click', e => {
            if (!list.contains(e.target) && e.target !== tickerInput){
                list.classList.add('hidden');
            }
        });
    }

    /* ---------- Watch-list ---------- */
    loadTadawulWatchlist();

    function loadTadawulWatchlist(){
        const wrap = document.getElementById('watchlistContent');
        if (!wrap) return;

        fetch('/api/tadawul_watchlist')
            .then(r => r.json())
            .then(data => {
                wrap.innerHTML = '';
                for (const sector in data){
                    const sectorDiv = document.createElement('div');
                    sectorDiv.innerHTML = `<h3 class="font-bold text-blue-700 text-xs uppercase mb-2">${sector}</h3>`;
                    data[sector].forEach(s => {
                        const item = document.createElement('div');
                        item.className = 'watchlist-item p-2 border-b text-sm';
                        item.textContent = `${s.code} - ${s.name}`;
                        item.addEventListener('click', () => {
                            document.getElementById('ticker').value = s.code;
                            fetchData();
                        });
                        sectorDiv.appendChild(item);
                    });
                    wrap.appendChild(sectorDiv);
                }
            })
            .catch(err => console.error('watchlist error',err));
    }

    /* ---------- Drawing-tools placeholders (optional) ---------- */
    function enableDrawingTool(t){console.log(`${t} on`);}
    function disableDrawingTool(t){console.log(`${t} off`);}
    ['TrendLine','Fib','Text','Brush'].forEach(tool=>{
        const id = `toggle${tool}`;
        document.getElementById(id).addEventListener('change',e=>{
            e.target.checked ? enableDrawingTool(tool) : disableDrawingTool(tool);
        });
    });

    /* ---------- First load ---------- */
    document.getElementById('ticker').value = '^TASI.SR';
    fetchData();
});
