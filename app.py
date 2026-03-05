<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>MT4量化交易前端 - 优化版</title>
  <style>
    :root {
      --bg: #f5f7fa;
      --card: #ffffff;
      --text: #1a1e23;
      --muted: #848e9c;
      --line: #eaecef;
      --green: #0ecb81;
      --red: #f6465d;
      --yellow: #f0b90b;
      --chip: #f3f5f7;
      --shadow: 0 8px 24px rgba(0,0,0,0.04);
      --radius: 16px;
    }
    * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Helvetica Neue", sans-serif;
      color: var(--text);
      background: var(--bg);
      line-height: 1.5;
    }

    /* 容器布局 */
    .app {
      max-width: 1000px;
      margin: 0 auto;
      min-height: 100vh;
      padding: 20px 20px 40px; /* 移除了底部预留空间 */
    }

    /* 顶部 */
    .topbar {
      display: flex; align-items: center; justify-content: space-between;
      margin-bottom: 20px;
    }
    .title { font-size: 22px; font-weight: 800; letter-spacing: 0.5px; }
    .btn {
      border: 1px solid var(--line); background: #fff; border-radius: 8px;
      padding: 8px 16px; font-weight: 600; color: #222; cursor: pointer;
      transition: background 0.2s;
    }
    .btn:hover { background: var(--chip); }

    /* 顶部大类 Tab (仿截图设计) */
    .tabs { display: flex; gap: 4px; margin-bottom: 20px; }
    .tab {
      padding: 8px 16px; border-radius: 10px; background: transparent;
      color: var(--muted); font-weight: 700; border: none; cursor: pointer;
      font-size: 15px; transition: all 0.2s;
    }
    .tab.active { background: var(--chip); color: var(--text); }

    /* 行情头部 */
    .symRow {
      display: flex; align-items: center; justify-content: space-between;
      margin-bottom: 20px; background: var(--card); padding: 20px;
      border-radius: var(--radius); box-shadow: var(--shadow); border: 1px solid var(--line);
    }
    .symLeft { display: flex; flex-direction: column; gap: 4px; }
    .symName { display: flex; align-items: center; gap: 10px; font-size: 26px; font-weight: 800; }
    .symBadge {
      font-size: 12px; padding: 4px 8px; border-radius: 6px;
      background: var(--chip); color: var(--muted); font-weight: 700; cursor: pointer;
    }
    .symBadge.primary { background: var(--text); color: #fff; }
    .symPnl { font-size: 16px; font-weight: 800; margin-top: 4px; }
    .symRight { display: flex; gap: 8px; }
    .iconBtn {
      width: 40px; height: 40px; border-radius: 10px; border: 1px solid var(--line);
      background: #fff; display: grid; place-items: center; cursor: pointer; font-size: 18px;
    }

    /* 双列布局 */
    .main-grid { display: flex; gap: 20px; align-items: stretch; }
    .col-left { flex: 1.2; display: flex; flex-direction: column; gap: 20px; }
    .col-right { flex: 1; display: flex; flex-direction: column; gap: 20px; }
    .card { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); padding: 24px; }

    /* 左侧面板内容 */
    .obTopStats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 24px; }
    .obStatLabel { font-size: 12px; font-weight: 600; color: var(--muted); margin-bottom: 4px; }
    .obStatVal { font-weight: 800; font-size: 15px; color: var(--text); }
    .midPrice { text-align: center; margin: 20px 0 5px; font-size: 36px; font-weight: 800; letter-spacing: -1px; }
    .midSub { text-align: center; color: var(--muted); font-weight: 600; font-size: 13px; margin-bottom: 24px; }
    
    /* 强平与风险监控 */
    .riskTip {
      display: flex; align-items: flex-start; gap: 12px; padding: 16px;
      border-radius: 12px; border: 1px solid #fcebb6; background: #fff9e6;
      color: #7d5e00; font-weight: 700; line-height: 1.5; font-size: 14px;
    }
    .lamp {
      width: 10px; height: 10px; border-radius: 50%; background: var(--yellow);
      box-shadow: 0 0 0 4px rgba(246,195,67,.2); flex: 0 0 auto; margin-top: 5px;
    }
    .liq-monitor { background: #fafbfc; margin-top: 20px; padding: 16px; border-radius: 12px; border: 1px solid var(--line); }
    .statRowNew { display: flex; justify-content: space-between; margin: 10px 0; font-size: 13px; }
    .statRowNew .k { color: var(--muted); font-weight: 600; }
    .statRowNew .v { font-weight: 800; font-size: 14px; }

    /* 右侧：交易表单区 */
    .form-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
    .chips { display: flex; gap: 8px; }
    .chip { padding: 6px 12px; border-radius: 8px; background: var(--chip); font-weight: 700; font-size: 13px; cursor: pointer; }
    .chip.primary { background: var(--text); color: #fff; }
    .form-avail { color: var(--muted); font-weight: 600; font-size: 13px; }
    .form-avail span { font-weight: 800; color: var(--text); }

    /* 单行输入框设计 */
    .form-row {
      display: flex; justify-content: space-between; align-items: center;
      background: var(--chip); border-radius: 10px; padding: 14px 16px;
      margin-bottom: 12px; border: 1px solid transparent; transition: border 0.2s;
    }
    .form-row:focus-within { border-color: var(--text); background: #fff; }
    .form-row.clickable { cursor: pointer; }
    .form-row label { color: var(--muted); font-weight: 600; font-size: 14px; white-space: nowrap; }
    .form-row input {
      border: none; background: transparent; text-align: right; width: 100%; margin-left: 16px;
      font-size: 16px; font-weight: 800; color: var(--text); outline: none; font-family: inherit;
    }
    .form-row .value-text { font-size: 16px; font-weight: 800; color: var(--text); }

    /* 滑块组件 */
    .wheelWrap { margin: 24px 0 32px; padding: 0 8px; }
    .wheelHeader { display: flex; justify-content: space-between; margin-bottom: 16px; font-size: 14px; font-weight: 700; color: var(--muted); }
    .wheel { position: relative; height: 24px; user-select: none; touch-action: none; cursor: pointer; }
    .track { position: absolute; left: 0; right: 0; top: 10px; height: 4px; background: var(--line); border-radius: 2px; }
    .marks { position: absolute; left: 0; right: 0; top: 7px; display: flex; justify-content: space-between; }
    .mark { width: 10px; height: 10px; border-radius: 50%; background: var(--line); cursor: pointer; transition: 0.2s; }
    .mark.active { background: var(--text); }
    .thumb {
      position: absolute; top: 0; width: 24px; height: 24px; border-radius: 50%;
      background: #fff; border: 4px solid var(--text); box-shadow: 0 4px 8px rgba(0,0,0,.15);
      transform: translateX(-50%); cursor: grab; transition: left 0.1s linear;
    }
    .thumb:active { cursor: grabbing; transform: translateX(-50%) scale(1.1); }

    /* 动作按钮 */
    .cta-group { display: flex; gap: 12px; margin-top: auto; }
    .cta {
      border: none; flex: 1; padding: 16px; border-radius: 12px;
      color: #fff; font-size: 16px; font-weight: 800; cursor: pointer; transition: transform 0.1s;
    }
    .cta:active { transform: scale(0.98); }
    .cta.buy { background: var(--green); }
    .cta.sell { background: var(--red); }

    /* 底部 Tab 及列表 (持仓/委托) */
    .bottom-section { margin-top: 30px; }
    .segTabs { display: flex; gap: 24px; border-bottom: 1px solid var(--line); margin-bottom: 20px; }
    .seg { padding: 12px 4px; color: var(--muted); font-weight: 700; font-size: 16px; cursor: pointer; position: relative; }
    .seg.active { color: var(--text); }
    .seg.active::after {
      content: ""; position: absolute; left: 0; right: 0; bottom: -1px;
      height: 3px; border-radius: 3px 3px 0 0; background: var(--text);
    }
    
    .listCard { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); display: none; }
    .listCard.active { display: block; }
    .posItem { padding: 20px; border-bottom: 1px solid var(--line); }
    .posItem:last-child { border-bottom: none; }
    .posTop { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
    .posTitle { display: flex; gap: 8px; align-items: center; font-weight: 800; font-size: 18px; }
    .sideTag { padding: 2px 8px; border-radius: 6px; font-size: 13px; font-weight: 800; border: 1px solid; background: #fff; }
    .sideTag.sell { color: var(--red); border-color: rgba(239,77,92,.3); }
    .sideTag.buy { color: var(--green); border-color: rgba(37,185,122,.3); }
    .posPnl { font-size: 24px; font-weight: 800; }
    .posGrid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 16px; margin-bottom: 16px; }
    .mini { color: var(--muted); font-size: 12px; font-weight: 600; margin-bottom: 4px; }
    .big { font-weight: 800; font-size: 15px; }
    .posActions { display: flex; gap: 12px; }
    .ghost { flex: 1; border: 1px solid var(--line); background: transparent; border-radius: 8px; padding: 10px; font-weight: 700; cursor: pointer; transition: background 0.2s; }
    .ghost:hover { background: var(--chip); }

    /* 空状态 */
    .empty-state { padding: 40px; text-align: center; color: var(--muted); font-weight: 600; font-size: 14px; }

    /* 响应式调整 */
    @media (max-width: 768px) {
      .main-grid { flex-direction: column; }
      .app { padding: 16px 16px 40px; }
      .posGrid { grid-template-columns: 1fr 1fr; }
    }

    /* 弹窗通用样式 */
    .modalMask { position: fixed; inset: 0; background: rgba(0,0,0,.5); display: none; align-items: center; justify-content: center; padding: 20px; z-index: 100; backdrop-filter: blur(2px); }
    .modal { width: min(400px, 100%); background: #fff; border-radius: 20px; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.1); animation: pop 0.2s ease-out; }
    @keyframes pop { from { transform: scale(0.95); opacity: 0; } to { transform: scale(1); opacity: 1; } }
    .modalHeader { padding: 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--line); font-weight: 800; font-size: 18px; }
    .modalBody { padding: 20px; max-height: 60vh; overflow: auto; }
    
    /* 列表选择项 */
    .select-item { padding: 16px; border-bottom: 1px solid var(--line); font-weight: 700; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }
    .select-item:last-child { border-bottom: none; }
    .select-item:hover { background: var(--chip); }
    .select-item.active { color: #0052cc; }
  </style>
</head>
<body>
  <div class="app">
    <div class="topbar">
      <div class="title">MT4 Quant Terminal</div>
      <button class="btn" onclick="alert('系统设置功能开发中...')">系统设置</button>
    </div>

    <div class="tabs">
      <button class="tab active" onclick="switchMainTab(this)">外汇 (Forex)</button>
      <button class="tab" onclick="switchMainTab(this)">贵金属 (Metals)</button>
      <button class="tab" onclick="switchMainTab(this)">原油/股指</button>
    </div>

    <div class="symRow">
      <div class="symLeft">
        <div class="symName">
          <span id="symName">XAUUSD</span>
          <span class="symBadge primary" id="btnPick">切换品种 ▼</span>
        </div>
        <div class="symPnl" id="symChg" style="color: var(--green);">+12.45 (0.53%)</div>
      </div>
      <div class="symRight">
        <button class="iconBtn" title="打开图表" onclick="alert('加载高级K线图表...')">📈</button>
        <button class="iconBtn" title="品种属性" onclick="alert('查看保证金要求及隔夜利息')">ℹ️</button>
      </div>
    </div>

    <div class="main-grid">
      <div class="col-left">
        <div class="card">
          <div class="obTopStats">
            <div><div class="obStatLabel">账户余额 (Balance)</div><div class="obStatVal">10,000.00 USD</div></div>
            <div><div class="obStatLabel">净值 (Equity)</div><div class="obStatVal" id="posNow">10,125.50 USD</div></div>
            <div><div class="obStatLabel">杠杆 (Leverage)</div><div class="obStatVal" id="posLev">1:100</div></div>
          </div>

          <div class="midPrice" id="mid">2345.50</div>
          <div class="midSub">实时买入价 (Bid)</div>

          <div style="padding-top: 16px; border-top: 1px solid var(--line);">
            <div class="statRowNew"><span class="k">浮动盈亏</span><span class="v" style="color: var(--green);">+125.50 USD</span></div>
            <div class="statRowNew"><span class="k">可用预付款</span><span class="v">9,540.20 USD</span></div>
            <div class="statRowNew"><span class="k">预付款比例</span><span class="v" style="color: var(--green);">2100.5%</span></div>
          </div>
        </div>

        <div class="riskTip">
          <div class="lamp"></div>
          <div>
            账户健康状态：良好
            <small>当前波动率正常。触发强平 (Stop Out) 水平线为预付款比例低于 20%。</small>
          </div>
        </div>
      </div>

      <div class="col-right">
        <div class="card">
          <div class="form-header">
            <div class="chips">
              <div class="chip primary">自动计算</div>
              <div class="chip" onclick="$('levMask').style.display='flex'">杠杆 100x ▼</div>
            </div>
            <div class="form-avail">可用: <span>9,540.20</span> USD</div>
          </div>

          <div class="form-row clickable" onclick="$('orderTypeMask').style.display='flex'">
            <label>交易类型</label>
            <div class="value-text"><span id="orderTypeText">市价单 (Market)</span> ▼</div>
          </div>
          
          <div id="dynamicFormArea">
            </div>

          <div class="wheelWrap">
            <div class="wheelHeader">
              <span>交易手数 (Lots)</span>
              <span style="color: var(--text); font-size: 16px;" id="pctText">1.00</span>
            </div>
            <div class="wheel" id="wheel">
              <div class="track"></div>
              <div class="marks" id="marks"></div>
              <div class="thumb" id="thumb"></div>
            </div>
          </div>

          <div class="cta-group">
            <button class="cta buy" onclick="submitOrder('BUY')">买入 (Buy by Market)</button>
            <button class="cta sell" onclick="submitOrder('SELL')">卖出 (Sell by Market)</button>
          </div>
        </div>
      </div>
    </div>

    <div class="bottom-section">
      <div class="segTabs">
        <div class="seg active" onclick="switchBottomTab('positions')">持仓列表 (1)</div>
        <div class="seg" onclick="switchBottomTab('orders')">挂单/委托 (0)</div>
      </div>

      <div class="listCard active" id="list-positions">
        <div class="posItem">
          <div class="posTop">
            <div>
              <div class="posTitle"><span class="sideTag buy">Buy</span> XAUUSD <span class="symBadge">1:100</span></div>
              <div class="mini" style="margin-top: 8px;">利润 (USD)</div>
              <div class="posPnl" style="color: var(--green);">+125.50</div>
            </div>
            <div style="text-align:right">
              <div class="mini">订单号</div>
              <div class="big" style="font-family: monospace;">#88492011</div>
              <div class="mini" style="margin-top:6px">开仓时间 <span style="color:var(--text); font-weight:800">14:22:10</span></div>
            </div>
          </div>
          <div class="posGrid">
            <div><div class="mini">手数 (Volume)</div><div class="big">1.00</div></div>
            <div><div class="mini">开仓价 (Open)</div><div class="big">2333.05</div></div>
            <div><div class="mini">当前价 (Current)</div><div class="big">2345.50</div></div>
            <div><div class="mini">止损 (S/L)</div><div class="big">2320.00</div></div>
            <div><div class="mini">止盈 (T/P)</div><div class="big">2360.00</div></div>
            <div><div class="mini">隔夜利息</div><div class="big">0.00</div></div>
          </div>
          <div class="posActions">
            <button class="ghost" onclick="alert('修改止盈止损')">修改订单</button>
            <button class="ghost" style="color: var(--red); border-color: rgba(246,70,93,0.3);" onclick="alert('确定平仓吗？')">平仓 (Close)</button>
          </div>
        </div>
      </div>

      <div class="listCard" id="list-orders">
        <div class="empty-state">当前没有挂单记录</div>
      </div>
    </div>
  </div>

  <div class="modalMask" id="orderTypeMask" onclick="closeModal(event, 'orderTypeMask')">
    <div class="modal">
      <div class="modalHeader">
        <span>选择交易类型</span>
        <button class="btn" style="border:none; padding:4px 8px;" onclick="$('orderTypeMask').style.display='none'">✕</button>
      </div>
      <div class="modalBody" style="padding: 0;">
        <div class="select-item active" onclick="setOrderType('market', '市价单 (Market)')">市价单 (Market)</div>
        <div class="select-item" onclick="setOrderType('market_tpsl', '市价 + 止盈止损')">市价 + 止盈止损</div>
        <div class="select-item" onclick="setOrderType('limit', '限价挂单 (Limit)')">限价挂单 (Limit)</div>
        <div class="select-item" onclick="setOrderType('limit_tpsl', '限价 + 止盈止损')">限价 + 止盈止损</div>
      </div>
    </div>
  </div>

  <div class="modalMask" id="pairMask" onclick="closeModal(event, 'pairMask')">
    <div class="modal">
      <div class="modalHeader">
        <span>切换交易品种</span>
        <button class="btn" style="border:none; padding:4px 8px;" onclick="$('pairMask').style.display='none'">✕</button>
      </div>
      <div class="modalBody">
        <div class="select-item" onclick="setSymbol('EURUSD', 1.0850)">EURUSD (欧元/美元)</div>
        <div class="select-item" onclick="setSymbol('GBPUSD', 1.2640)">GBPUSD (英镑/美元)</div>
        <div class="select-item" onclick="setSymbol('XAUUSD', 2345.50)">XAUUSD (黄金/美元)</div>
        <div class="select-item" onclick="setSymbol('USOIL', 82.30)">USOIL (美国原油)</div>
      </div>
    </div>
  </div>

  <script>
    const $ = id => document.getElementById(id);

    // --- 状态管理 ---
    let currentOrderType = 'market'; 
    let currentLots = 1.00;

    // --- 顶部大类 Tab 切换 ---
    function switchMainTab(el) {
      document.querySelectorAll('.tabs .tab').forEach(t => t.classList.remove('active'));
      el.classList.add('active');
      // 真实业务中这里应该请求对应大类的品种列表
    }

    // --- 底部持仓/委托 Tab 切换 ---
    function switchBottomTab(target) {
      document.querySelectorAll('.segTabs .seg').forEach(el => el.classList.remove('active'));
      event.target.classList.add('active');
      
      $('list-positions').classList.remove('active');
      $('list-orders').classList.remove('active');
      $('list-' + target).classList.add('active');
    }

    // --- 模态框控制 ---
    function closeModal(e, id) {
      if(e.target.id === id) $(id).style.display = 'none';
    }

    // --- 品种切换 ---
    $('btnPick').onclick = () => $('pairMask').style.display = 'flex';
    function setSymbol(name, price) {
      $('symName').innerText = name;
      $('mid').innerText = price.toFixed(name === 'XAUUSD' || name === 'USOIL' ? 2 : 4);
      $('pairMask').style.display = 'none';
    }

    // --- 动态渲染表单逻辑 (核心) ---
    function setOrderType(typeCode, typeName) {
      currentOrderType = typeCode;
      $('orderTypeText').innerText = typeName;
      $('orderTypeMask').style.display = 'none';
      
      // 更新下拉列表的高亮状态
      document.querySelectorAll('#orderTypeMask .select-item').forEach(el => {
        el.classList.remove('active');
        if(el.innerText === typeName) el.classList.add('active');
      });

      renderDynamicFields();
    }

    function renderDynamicFields() {
      const area = $('dynamicFormArea');
      let html = '';

      // 单行输入框模板函数
      const renderInput = (label, placeholder, val = '') => `
        <div class="form-row">
          <label>${label}</label>
          <input type="number" placeholder="${placeholder}" value="${val}">
        </div>
      `;

      switch(currentOrderType) {
        case 'market':
          // 只有点差
          html += renderInput('允许滑点 (Points)', '默认值', '30');
          break;
        case 'market_tpsl':
          // 止盈、止损、点差
          html += renderInput('止损价 (S/L)', '输入止损价格');
          html += renderInput('止盈价 (T/P)', '输入止盈价格');
          html += renderInput('允许滑点 (Points)', '默认', '30');
          break;
        case 'limit':
          // 触发价、点差
          html += renderInput('挂单触发价', '输入目标建仓价格');
          html += renderInput('失效期限', 'GTC (一直有效)', 'GTC');
          break;
        case 'limit_tpsl':
          // 触发价、止损、止盈、点差
          html += renderInput('挂单触发价', '输入目标建仓价格');
          html += renderInput('止损价 (S/L)', '输入止损价格');
          html += renderInput('止盈价 (T/P)', '输入止盈价格');
          html += renderInput('失效期限', 'GTC', 'GTC');
          break;
      }
      area.innerHTML = html;
    }

    // --- 提交订单模拟 ---
    function submitOrder(side) {
      const typeStr = $('orderTypeText').innerText;
      const lots = currentLots.toFixed(2);
      const symbol = $('symName').innerText;
      alert(`【执行下单指令】\n品种: ${symbol}\n方向: ${side}\n类型: ${typeStr}\n手数: ${lots} 手\n\n(已发送至 MT4 接口)`);
    }

    // --- 手数滑块控制逻辑 ---
    function initSlider() {
      const root = $('wheel');
      const marksEl = $('marks');
      const thumb = $('thumb');
      const min = 0.01;
      const max = 5.00; // MT4一般滑块最大值，可调
      const marksData = [0.01, 1.00, 2.00, 3.00, 4.00, 5.00];

      // 生成刻度
      marksData.forEach(v => {
        const m = document.createElement('div');
        m.className = 'mark';
        m.onclick = () => setSliderValue(v);
        marksEl.appendChild(m);
      });

      function setSliderValue(val) {
        val = Math.max(min, Math.min(max, val));
        currentLots = val;
        $('pctText').innerText = val.toFixed(2);
        
        // 更新UI
        const pct = (val - min) / (max - min);
        thumb.style.left = `calc(${pct * 100}%)`;
        
        // 高亮刻度
        Array.from(marksEl.children).forEach((el, i) => {
          el.classList.toggle('active', marksData[i] <= val);
        });
      }

      // 拖拽逻辑
      let dragging = false;
      const updateFromEvent = (e) => {
        const rect = root.getBoundingClientRect();
        let clientX = e.touches ? e.touches[0].clientX : e.clientX;
        let p = (clientX - rect.left) / rect.width;
        p = Math.max(0, Math.min(1, p));
        setSliderValue(min + p * (max - min));
      };

      root.addEventListener('mousedown', (e) => { dragging = true; updateFromEvent(e); });
      root.addEventListener('touchstart', (e) => { dragging = true; updateFromEvent(e); }, {passive: false});
      window.addEventListener('mousemove', (e) => { if(dragging) updateFromEvent(e); });
      window.addEventListener('touchmove', (e) => { if(dragging) updateFromEvent(e); }, {passive: false});
      window.addEventListener('mouseup', () => dragging = false);
      window.addEventListener('touchend', () => dragging = false);

      // 初始化默认值
      setSliderValue(1.00);
    }

    // --- 页面初始化 ---
    window.onload = () => {
      renderDynamicFields();
      initSlider();
    };
  </script>
</body>
</html>
