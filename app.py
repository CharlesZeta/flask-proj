from flask import Flask, render_template_string, jsonify, request
import random
from datetime import datetime

app = Flask(__name__)

# 模拟数据库
orders = []
positions = [
    {
        "id": "MT4_8821",
        "symbol": "XAUUSD",
        "side": "BUY",
        "lots": 1.00,
        "open_price": 2333.05,
        "current_price": 2345.50,
        "sl": 0.00,
        "tp": 0.00,
        "margin": 1166.52,
        "open_time": "14:22:10"
    }
]

# 嵌入的 HTML 模板
HTML_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <!-- 1. Viewport 适配与移动端优先 -->
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover" />
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
  <meta name="format-detection" content="telephone=no" />
  <meta name="theme-color" content="#ffffff" />
  
  <title>量化交易终端 - 移动版</title>
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
      --shadow: 0 0.5rem 1.5rem rgba(0,0,0,0.06);
      --radius: 1rem;
      --safe-bottom: env(safe-area-inset-bottom);
    }

    /* 2. CSS Reset (移动端优化) */
    * { 
      box-sizing: border-box; 
      -webkit-tap-highlight-color: transparent; 
      outline: none;
    }
    
    html {
      font-size: 16px; /* 基准字号 */
      -webkit-text-size-adjust: 100%; /* 禁止字体自动缩放 */
    }

    body {
      margin: 0; 
      font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Helvetica Neue", sans-serif;
      color: var(--text); 
      background: var(--bg); 
      line-height: 1.5;
      overflow-x: hidden; /* 防止横向滚动 */
      width: 100%;
      overscroll-behavior-y: none; /* 禁用下拉刷新效果，模拟原生App */
    }

    /* 消除点击延迟 */
    button, a, input, [role="button"] {
      touch-action: manipulation;
    }

    /* 容器布局 */
    .app { 
      width: 100%;
      max-width: 62.5rem; /* 1000px */
      margin: 0 auto; 
      min-height: 100vh; 
      padding: 1.25rem; /* 20px */
      padding-bottom: calc(1.25rem + var(--safe-bottom));
    }

    /* 顶部 */
    .topbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.25rem; }
    .title { font-size: 1.375rem; font-weight: 800; }
    .btn { 
      border: 1px solid var(--line); 
      background: #fff; 
      border-radius: 0.5rem; 
      padding: 0.5rem 1rem; 
      font-weight: 600; 
      min-height: 2.75rem; /* 44px 最小触控区域 */
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 0.9375rem;
    }
    /* 移除 hover-only，改为 active */
    .btn:active { background: var(--chip); }

    /* 顶部分类 Tabs */
    .tabs-wrapper { 
      overflow-x: auto; 
      white-space: nowrap; 
      margin-bottom: 1.25rem; 
      -webkit-overflow-scrolling: touch; 
      padding-bottom: 0.3125rem; 
      scrollbar-width: none; /* Firefox */
    }
    .tabs-wrapper::-webkit-scrollbar { display: none; } /* Chrome/Safari */
    
    .tabs { display: inline-flex; gap: 0.5rem; }
    .tab { 
      padding: 0.5rem 1rem; 
      border-radius: 0.5rem; 
      background: transparent; 
      color: var(--muted); 
      font-weight: 700; 
      border: none; 
      font-size: 0.9375rem; /* 15px */
      min-height: 2.75rem; /* 44px */
      transition: 0.2s;
    }
    .tab.active { background: var(--card); color: var(--text); box-shadow: 0 2px 8px rgba(0,0,0,0.05); }

    /* 行情头 */
    .symRow { 
      display: flex; align-items: center; justify-content: space-between; 
      margin-bottom: 1.25rem; background: var(--card); padding: 1.25rem; 
      border-radius: var(--radius); box-shadow: var(--shadow); 
      border: 1px solid var(--line); 
    }
    .symLeft { display: flex; flex-direction: column; gap: 0.25rem; }
    .symName { display: flex; align-items: center; gap: 0.625rem; font-size: 1.625rem; font-weight: 800; }
    .symBadge { 
      font-size: 0.875rem; padding: 0.25rem 0.5rem; 
      border-radius: 0.375rem; background: var(--text); color: #fff; 
      font-weight: 700; min-height: 2rem; display: inline-flex; align-items: center;
    }
    .symRight { display: flex; align-items: center; }
    .iconBtn.huge-chart { 
      width: 5rem; height: 5rem; border-radius: 1rem; 
      border: 2px solid var(--line); background: #fff; 
      display: grid; place-items: center; font-size: 2.25rem; 
      box-shadow: 0 4px 12px rgba(0,0,0,0.05); transition: 0.2s; 
    }
    .iconBtn.huge-chart:active { transform: scale(0.95); }

    /* 核心布局 */
    .main-grid { display: flex; gap: 1.25rem; align-items: stretch; }
    .col-left { flex: 1.2; display: flex; flex-direction: column; gap: 1.25rem; }
    .col-right { flex: 1; display: flex; flex-direction: column; gap: 1.25rem; }
    .card { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); padding: 1.5rem; }

    /* 数据统计 */
    .obTopStats { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; margin-bottom: 1.5rem; }
    .obStatItem { display: flex; flex-direction: column; gap: 0.25rem; }
    .obStatLabel { font-size: 0.875rem; /* >= 14px */ font-weight: 600; color: var(--muted); }
    .obStatVal { font-weight: 800; font-size: 1rem; color: var(--text); }
    
    .midPrice { text-align: center; margin: 1.25rem 0 0.3125rem; font-size: 2.25rem; font-weight: 800; letter-spacing: -1px; }
    .midSub { display: flex; justify-content: center; align-items: center; gap: 0.5rem; color: var(--muted); font-weight: 600; font-size: 0.875rem; margin-bottom: 1.5rem; }
    
    .signal-dot { width: 0.625rem; height: 0.625rem; border-radius: 50%; display: inline-block; transition: background 0.3s; }
    .signal-dot.green { background: var(--green); box-shadow: 0 0 6px var(--green); }
    .signal-dot.yellow { background: var(--yellow); box-shadow: 0 0 6px var(--yellow); }
    .signal-dot.red { background: var(--red); box-shadow: 0 0 6px var(--red); }

    /* 止损计算器 */
    .sl-calculator { background: #fafbfc; border: 1px solid var(--line); border-radius: 0.75rem; padding: 1rem; margin-top: auto; }
    .sl-title { font-size: 0.875rem; font-weight: 800; margin-bottom: 0.75rem; color: var(--text); display: flex; justify-content: space-between; align-items: flex-end;}
    .sl-row { display: flex; justify-content: space-between; margin: 0.5rem 0; font-size: 0.875rem; font-variant-numeric: tabular-nums; }
    .sl-row .k { color: var(--muted); font-weight: 600; }
    .sl-row .v { font-weight: 800; font-size: 0.875rem; color: var(--text); }

    /* 表单区 */
    .form-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem; }
    .chips { display: flex; gap: 0.5rem; }
    .chip { 
      padding: 0.5rem 0.75rem; border-radius: 0.5rem; background: var(--chip); 
      font-weight: 700; font-size: 0.875rem; border: 1px solid transparent; 
      min-height: 2rem; display: inline-flex; align-items: center;
    }
    .chip.primary { background: var(--text); color: #fff; }
    
    .form-row { 
      display: flex; justify-content: space-between; align-items: center; 
      background: var(--chip); border-radius: 0.625rem; padding: 0.875rem 1rem; 
      margin-bottom: 0.75rem; border: 1px solid transparent; transition: 0.2s; 
      min-height: 3.5rem; /* 56px touch target */
    }
    .form-row:focus-within { background: #fff; border-color: var(--text); }
    .form-row label { color: var(--muted); font-weight: 600; font-size: 0.875rem; white-space: nowrap; }
    .form-row input { 
      border: none; background: transparent; text-align: right; width: 100%; margin-left: 1rem; 
      font-size: 1rem; /* >= 16px to prevent zoom */
      font-weight: 800; color: var(--text); outline: none; font-family: inherit; 
    }
    .form-row .value-text { font-size: 1rem; font-weight: 800; color: var(--text); }

    /* 滑块 */
    .range-wrap { margin: 1.25rem 0 1.5rem; padding: 0; }
    .range-header { display: flex; justify-content: space-between; margin-bottom: 0.75rem; font-size: 0.875rem; font-weight: 700; color: var(--muted); align-items: center;}
    input[type=range] { -webkit-appearance: none; width: 100%; background: transparent; padding: 0.625rem 0; margin: 0; min-height: 2.75rem; } /* 44px */
    input[type=range]:focus { outline: none; }
    input[type=range]::-webkit-slider-runnable-track { width: 100%; height: 0.375rem; background: linear-gradient(to right, var(--text) 0%, var(--text) var(--track-fill, 10%), var(--line) var(--track-fill, 10%), var(--line) 100%); border-radius: 3px; }
    input[type=range]::-webkit-slider-thumb { height: 1.5rem; width: 1.5rem; border-radius: 50%; background: #fff; border: 4px solid var(--text); -webkit-appearance: none; margin-top: -0.5625rem; box-shadow: 0 2px 6px rgba(0,0,0,0.15); }

    /* 按钮组 */
    .cta-group { display: flex; gap: 0.75rem; margin-top: 0.625rem;}
    .cta { 
      border: none; flex: 1; padding: 1rem; border-radius: 0.75rem; 
      color: #fff; font-size: 1rem; font-weight: 800; 
      transition: transform 0.1s; 
      min-height: 3.5rem; /* 56px */
      display: flex; align-items: center; justify-content: center;
    }
    .cta:active { transform: scale(0.98); }
    .cta.buy { background: var(--green); }
    .cta.sell { background: var(--red); }

    /* 底部列表 */
    .bottom-section { margin-top: 2rem; }
    .segTabs { display: flex; gap: 1.5rem; border-bottom: 1px solid var(--line); margin-bottom: 1.25rem; }
    .seg { 
      padding: 0.75rem 0.25rem; color: var(--muted); font-weight: 700; font-size: 1rem; 
      position: relative; min-height: 2.75rem; display: flex; align-items: center;
    }
    .seg.active { color: var(--text); }
    .seg.active::after { content: ""; position: absolute; left: 0; right: 0; bottom: -1px; height: 3px; border-radius: 3px 3px 0 0; background: var(--text); }
    
    .listCard { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); display: none; }
    .listCard.active { display: block; }
    .posItem { padding: 1.25rem; }
    .posTop { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem; }
    .posTitle { display: flex; gap: 0.5rem; align-items: center; font-weight: 800; font-size: 1.125rem; }
    .sideTag { padding: 0.125rem 0.5rem; border-radius: 0.375rem; font-size: 0.875rem; font-weight: 800; border: 1px solid; background: #fff; }
    .sideTag.buy { color: var(--green); border-color: rgba(37,185,122,.3); }
    .posGrid { display: grid; grid-template-columns: repeat(auto-fit, minmax(7.5rem, 1fr)); gap: 1rem; margin-bottom: 1rem; }
    .mini { color: var(--muted); font-size: 0.875rem; /* >= 14px */ font-weight: 600; margin-bottom: 0.25rem; }
    .big { font-weight: 800; font-size: 1rem; }
    .posActions { display: flex; gap: 0.75rem; }
    .ghost { 
      flex: 1; border: 1px solid var(--line); background: transparent; 
      border-radius: 0.5rem; padding: 0.625rem; font-weight: 700; 
      min-height: 2.75rem; display: flex; align-items: center; justify-content: center;
      transition: 0.2s; 
    }
    .ghost:active { background: var(--chip); }

    /* 弹窗/动作面板 (Action Sheet) */
    .modalMask { 
      position: fixed; inset: 0; background: rgba(0,0,0,.5); 
      display: none; align-items: center; justify-content: center; 
      padding: 1.25rem; z-index: 100; backdrop-filter: blur(2px); 
    }
    .modal { 
      width: min(27.5rem, 100%); background: #fff; border-radius: 1.25rem; 
      overflow: hidden; box-shadow: 0 1.25rem 2.5rem rgba(0,0,0,0.1); 
      animation: pop 0.2s ease-out; display: flex; flex-direction: column; max-height: 90vh; 
    }
    @keyframes pop { from { transform: scale(0.95); opacity: 0; } to { transform: scale(1); opacity: 1; } }
    
    .modalHeader { 
      padding: 1.25rem; display: flex; justify-content: space-between; align-items: center; 
      border-bottom: 1px solid var(--line); font-weight: 800; font-size: 1.125rem; flex-shrink: 0; 
      min-height: 3.5rem;
    }
    .modalBody { padding: 1.25rem; overflow-y: auto; flex-grow: 1; }
    .select-item { 
      padding: 1rem; border-bottom: 1px solid var(--line); font-weight: 700; 
      display: flex; justify-content: space-between; align-items: center; min-height: 3.5rem;
    }
    .select-item:last-child { border-bottom: none; }
    .select-item:active { background: var(--chip); }
    .select-item.active { color: var(--text); }

    /* 3. 移动端媒体查询 (320-428px) */
    @media (max-width: 768px) {
      .app { padding: 1rem; padding-bottom: calc(1rem + var(--safe-bottom)); }
      
      /* 单列流式布局 */
      .main-grid { flex-direction: column; gap: 1rem; }
      .col-left, .col-right { gap: 1rem; }
      
      /* 底部动作面板模式 */
      .modalMask { align-items: flex-end; padding: 0; }
      .modal { 
        width: 100%; max-width: 100%; 
        border-radius: 1.5rem 1.5rem 0 0; 
        margin: 0; animation: slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1); 
        padding-bottom: var(--safe-bottom);
      }
      @keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
      
      /* 字体与间距微调 */
      .title { font-size: 1.25rem; }
      .midPrice { font-size: 2rem; }
      .posGrid { grid-template-columns: repeat(2, 1fr); }
      
      /* 1px 边框优化 */
      .form-row, .btn, .tab, .cta, .ghost, .symRow, .card, .sl-calculator {
        border-width: 0.0625rem; /* fallback */
      }
      @media (-webkit-min-device-pixel-ratio: 2) {
        .form-row, .btn, .tab, .cta, .ghost, .symRow, .card, .sl-calculator { border-width: 0.5px; }
      }
    }

    /* 问卷样式 */
    .quiz-item { margin-bottom: 1.5rem; }
    .quiz-q { font-size: 0.9375rem; font-weight: 800; margin-bottom: 0.75rem; color: var(--text); }
    .quiz-opts { display: flex; gap: 0.75rem; flex-direction: column; }
    .quiz-opt { 
      flex: 1; padding: 0.75rem; border: 1px solid var(--line); border-radius: 0.625rem; 
      text-align: center; font-weight: 700; transition: 0.2s; background: var(--chip); 
      min-height: 3rem; display: flex; align-items: center; justify-content: center;
    }
    .quiz-opt.selected { background: var(--text); color: #fff; border-color: var(--text); }

    /* 日历样式 */
    .cal-header { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; text-align: center; font-weight: 800; color: var(--muted); font-size: 0.875rem; margin-bottom: 0.5rem; }
    .cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; }
    .cal-day { 
      border: 1px solid var(--line); border-radius: 0.5rem; padding: 0.25rem; text-align: center; 
      min-height: 3.5rem; display: flex; flex-direction: column; justify-content: space-between; 
    }
    .cal-day.empty { border: none; background: transparent; }
    .cal-date { font-weight: 800; font-size: 0.875rem; color: var(--text); }
    .cal-pnl { font-size: 0.75rem; font-weight: 800; margin-top: 0.25rem; }

    /* 错误弹窗 */
    .error-popup { position: fixed; inset: 0; background: rgba(0,0,0,0.6); display: none; align-items: center; justify-content: center; z-index: 1000; backdrop-filter: blur(4px); }
    .error-popup.show { display: flex; }
    .error-popup-content { background: #fff; border-radius: 1.25rem; padding: 1.5rem; width: min(22.5rem, 85%); text-align: center; box-shadow: 0 1.25rem 3.75rem rgba(0,0,0,0.3); }
    .error-popup-icon { width: 4rem; height: 4rem; background: linear-gradient(135deg, #fee2e2, #fecaca); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 1.25rem; font-size: 2rem; }
    .error-popup-title { font-size: 1.25rem; font-weight: 800; color: #1f2937; margin-bottom: 1rem; }
    .error-popup-list { text-align: left; background: #f9fafb; border-radius: 0.75rem; padding: 1rem; margin-bottom: 1.25rem; max-height: 12.5rem; overflow-y: auto; }
    .error-popup-item { display: flex; align-items: center; padding: 0.5rem 0; color: #dc2626; font-size: 0.875rem; font-weight: 600; border-bottom: 1px solid #e5e7eb; }
    .error-popup-item:last-child { border-bottom: none; }
    .error-popup-btn { 
      background: linear-gradient(135deg, #1f2937, #374151); color: #fff; border: none; 
      padding: 0.875rem 2rem; border-radius: 0.75rem; font-size: 1rem; font-weight: 700; 
      width: 100%; min-height: 3rem;
    }

    /* 4. 图片视频资源优化 (CSS层) */
    img, video { max-width: 100%; height: auto; display: block; object-fit: cover; }
    
    /* 锁仓按钮 */
    .lock-btn { 
      background: linear-gradient(135deg, #f6465d, #ff7b8c); color: #fff; border: none; 
      padding: 1rem; border-radius: 0.75rem; font-size: 1rem; font-weight: 800; 
      width: 100%; box-shadow: 0 0.25rem 0.75rem rgba(246,70,93,0.3); margin-top: 0.625rem; 
      min-height: 3.5rem;
    }
  </style>
</head>
<body>

  <div class="error-popup" id="errorPopup" onclick="closeErrorPopup(event)">
    <div class="error-popup-content">
      <div class="error-popup-icon">⚠️</div>
      <div class="error-popup-title">表单数据错误</div>
      <div class="error-popup-list" id="errorPopupList"></div>
      <button class="error-popup-btn" onclick="$('errorPopup').classList.remove('show')">我知道了</button>
    </div>
  </div>

  <!-- 模拟 API -->
  <script>
    const API = {
      // 1. 发送下单指令
      submitOrder: async function(symbol, side, type, marginPct, leverage, calculatedLots, params) {
        console.log("【API】执行下单:", {symbol, side, type, marginPct, leverage, calculatedLots, ...params});
        
        try {
          const response = await fetch('/api/v1/order', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              symbol,
              side,
              type,
              marginPct,
              leverage,
              lots: calculatedLots,
              ...params
            })
          });
          const data = await response.json();
          return data;
        } catch (error) {
          console.error("下单失败:", error);
          alert("网络请求失败，请检查连接");
          return { success: false };
        }
      },
      
      // 2. 修改持仓订单 (分批止盈止损)
      modifyPosition: async function(positionId, tpPrice, tpLots, slPrice, slLots) {
        console.log("【API】修改持仓:", {positionId, tpPrice, tpLots, slPrice, slLots});
        
        try {
          const response = await fetch('/api/v1/position/modify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ positionId, tpPrice, tpLots, slPrice, slLots })
          });
          return await response.json();
        } catch (error) {
          console.error("修改持仓失败:", error);
          return { success: false };
        }
      },
      
      // 3. 锁仓接口
      lockPosition: async function(positionId) {
        console.log("【API】一键锁仓:", {positionId});
        
        try {
          const response = await fetch('/api/v1/position/lock', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ positionId })
          });
          return await response.json();
        } catch (error) {
          console.error("锁仓失败:", error);
          return { success: false };
        }
      },
      
      // 4. 获取历史日历盈亏数据
      getCalendarPnL: async function(year, month) {
        console.log("【API】获取日历数据:", year, month);
        
        try {
          const response = await fetch(`/api/v1/calendar?year=${year}&month=${month}`);
          return await response.json();
        } catch (error) {
          console.error("获取日历失败:", error);
          return {};
        }
      }
    };
  </script>

  <div class="app">
    <div class="topbar">
      <div class="title">MT4 量化终端</div>
      <button class="btn" onclick="alert('系统设置功能开发中...')">设置</button>
    </div>

    <div class="tabs-wrapper">
      <div class="tabs">
        <button class="tab" data-category="forex" onclick="switchMainTab(this); showCategoryPairs('forex')">外汇</button>
        <button class="tab" data-category="index" onclick="switchMainTab(this); showCategoryPairs('index')">指数</button>
        <button class="tab" data-category="commodity" onclick="switchMainTab(this); showCategoryPairs('commodity')">大宗商品</button>
        <button class="tab active" data-category="metal" onclick="switchMainTab(this); showCategoryPairs('metal')">贵金属</button>
        <button class="tab" data-category="stock" onclick="switchMainTab(this); showCategoryPairs('stock')">股票</button>
      </div>
    </div>

    <div class="symRow">
      <div class="symLeft">
        <div class="symName">
          <span id="symName">XAUUSD</span>
          <span class="symBadge" onclick="$('pairMask').style.display='flex'">切换品种 ▼</span>
        </div>
      </div>
      <div class="symRight">
        <button class="iconBtn huge-chart" title="交易日历看板" onclick="openCalendar()">📈</button>
      </div>
    </div>

    <div class="main-grid">
      <div class="col-left">
        <div class="card">
          <div class="obTopStats">
            <div class="obStatItem"><div class="obStatLabel">账户净值 (USD)</div><div class="obStatVal">10,125.50</div></div>
            <div class="obStatItem"><div class="obStatLabel">可用余额 (USD)</div><div class="obStatVal" id="availMarginStr">9,540.20</div></div>
            <div class="obStatItem"><div class="obStatLabel">日内浮动盈亏</div><div class="obStatVal" style="color:var(--green)">+125.50</div></div>
            <div class="obStatItem"><div class="obStatLabel">日内盈亏率</div><div class="obStatVal" style="color:var(--green)">+1.24%</div></div>
          </div>
          
          <div class="midPrice" id="midPriceText">2345.50</div>
          <div class="midSub">
            当前实时买入价 (Bid) <span class="signal-dot green" id="latencySignal" title="获取延迟"></span>
          </div>
        </div>

        <div class="sl-calculator">
          <div class="sl-title">
            <span>基于当前仓位预估止损额度</span>
            <span style="color:var(--muted); font-size:0.75rem; font-weight:600">公式: 预付款×杠杆×比例</span>
          </div>
          <div style="height:1px; background:var(--line); margin:0.75rem 0;"></div>
          <div class="sl-row"><span class="k">2% 止损亏损</span><span class="v" id="sl_2">0.00 USD</span></div>
          <div class="sl-row"><span class="k">3% 止损亏损</span><span class="v" id="sl_3">0.00 USD</span></div>
          <div class="sl-row"><span class="k">5% 止损亏损</span><span class="v" id="sl_5">0.00 USD</span></div>
          <div class="sl-row"><span class="k">8% 止损亏损</span><span class="v" id="sl_8">0.00 USD</span></div>
          <div class="sl-row"><span class="k">10% 止损亏损</span><span class="v" id="sl_10">0.00 USD</span></div>
          
          <div style="height:1px; background:var(--line); margin:0.75rem 0;"></div>
          <div class="sl-row"><span class="k">占用保证金</span><span class="v" id="calcMargin">0.00 USD</span></div>
          <div class="sl-row"><span class="k">当前设置下每点波动≈</span><span class="v" id="calcPpVal">0.00 USD</span></div>
          <div class="sl-row"><span class="k">预估强平价格</span><span class="v" id="calcLiq">0.00</span></div>
        </div>
      </div>

      <div class="col-right">
        <div class="card" style="height: 100%; display: flex; flex-direction: column;">
          <div class="form-header">
            <div class="chips">
              <div class="chip primary">全仓模式</div>
              <div class="chip" id="btnLev" onclick="$('levMask').style.display='flex'">杠杆 20x ▼</div>
            </div>
            <div style="color: var(--muted); font-size: 0.8125rem; font-weight: 600;">可用: <span style="color:var(--text);font-weight:800">9540.20</span></div>
          </div>

          <div class="form-row" onclick="$('orderTypeMask').style.display='flex'">
            <label>交易类型</label>
            <div class="value-text"><span id="orderTypeText">限价止盈止损</span> ▼</div>
          </div>
          
          <div id="dynamicFormArea"></div>

          <div class="range-wrap" style="margin-top: auto;">
            <div class="range-header">
              <span>仓位占比 (基于可用余额)</span>
              <span style="color: var(--text); font-size: 1rem;">
                <span id="pctText">10</span>% 
                <span style="font-size: 0.75rem; color: var(--muted); margin-left: 0.25rem;">(<span id="lotsText">0.00</span> 手)</span>
              </span>
            </div>
            <input type="range" id="marginSlider" min="0" max="100" step="1" value="10">
          </div>

          <div class="cta-group">
            <button class="cta buy" onclick="initiateOrder('BUY')">买入 / 做多</button>
            <button class="cta sell" onclick="initiateOrder('SELL')">卖出 / 做空</button>
          </div>
        </div>
      </div>
    </div>

    <div class="bottom-section">
      <div class="segTabs">
        <div class="seg active" onclick="switchBottomTab('positions')">持有仓位 (1)</div>
        <div class="seg" onclick="switchBottomTab('orders')">当前委托 (0)</div>
      </div>
      
      <div class="listCard active" id="list-positions">
        <div class="posItem">
          <div class="posTop">
            <div>
              <div class="posTitle"><span class="sideTag buy">Buy</span> XAUUSD <span class="symBadge" style="background:var(--chip); color:var(--text)">1:20</span></div>
              <div class="mini" style="margin-top: 0.5rem;">浮动盈亏 (USD)</div>
              <div style="font-size: 1.5rem; font-weight: 800; color: var(--green);">+125.50</div>
            </div>
            <div style="text-align:right">
              <div class="mini">订单号</div>
              <div class="big" style="font-family: monospace;">#MT4_8821</div>
              <div class="mini" style="margin-top:0.375rem">开仓时间 <span style="color:var(--text); font-weight:800">14:22:10</span></div>
            </div>
          </div>
          <div class="posGrid">
            <div><div class="mini">剩余手数</div><div class="big" id="posLotsVal">1.00</div></div>
            <div><div class="mini">开仓价</div><div class="big">2333.05</div></div>
            <div><div class="mini">当前价</div><div class="big">2345.50</div></div>
            <div><div class="mini">止损 (S/L)</div><div class="big" id="posSlVal">0.00</div></div>
            <div><div class="mini">止盈 (T/P)</div><div class="big" id="posTpVal">0.00</div></div>
            <div><div class="mini">占用预付款</div><div class="big">1166.52</div></div>
          </div>
          <div class="posActions">
            <button class="ghost" onclick="openModifyOrderPanel()">修改订单</button>
            <button class="ghost" style="color: var(--red); border-color: rgba(246,70,93,0.3);" onclick="alert('执行平仓接口')">一键平仓</button>
          </div>
        </div>
      </div>
      
      <div class="listCard" id="list-orders">
        <div style="padding: 2.5rem; text-align: center; color: var(--muted); font-weight: 600; font-size: 0.875rem;">暂无当前委托挂单</div>
      </div>
    </div>
  </div>

  <!-- 弹窗部分 -->
  <div class="modalMask" id="quizMask" onclick="closeModal(event, 'quizMask')">
    <div class="modal">
      <div class="modalHeader"><span>执行前风控检查</span><button class="btn" style="border:none; padding:0.25rem 0.5rem;" onclick="$('quizMask').style.display='none'">✕</button></div>
      <div class="modalBody">
        <div class="quiz-item">
          <div class="quiz-q">1. 该笔交易是否顺应大级别趋势？</div>
          <div class="quiz-opts">
            <div class="quiz-opt" onclick="selectQuiz(this, 1, 'A')">A. 是的，顺势</div>
            <div class="quiz-opt" onclick="selectQuiz(this, 1, 'B')">B. 否，逆势博弈</div>
          </div>
        </div>
        <div class="quiz-item">
          <div class="quiz-q">2. 盈亏比是否达到你的交易系统标准？</div>
          <div class="quiz-opts">
            <div class="quiz-opt" onclick="selectQuiz(this, 2, 'A')">A. 已达标</div>
            <div class="quiz-opt" onclick="selectQuiz(this, 2, 'B')">B. 未达标</div>
          </div>
        </div>
        <div class="quiz-item">
          <div class="quiz-q">3. 当前是否属于情绪化报复性交易？</div>
          <div class="quiz-opts">
            <div class="quiz-opt" onclick="selectQuiz(this, 3, 'A')">A. 情绪稳定，非报复</div>
            <div class="quiz-opt" onclick="selectQuiz(this, 3, 'B')">B. 是的，急于回本</div>
          </div>
        </div>
        <button class="cta" style="background:var(--text); color:#fff; width:100%" onclick="confirmOrderAfterQuiz()">确认并发送订单</button>
      </div>
    </div>
  </div>

  <div class="modalMask" id="modifyMask" onclick="closeModal(event, 'modifyMask')">
    <div class="modal">
      <div class="modalHeader"><span>高级订单管理</span><button class="btn" style="border:none; padding:0.25rem 0.5rem;" onclick="$('modifyMask').style.display='none'">✕</button></div>
      <div class="modalBody">
        <div style="margin-bottom: 1.25rem; padding: 1rem; border: 1px solid var(--line); border-radius: 0.75rem;">
          <div class="form-row" style="margin-bottom: 0.75rem;">
            <label style="color:var(--green)">止盈触发价 (T/P)</label>
            <input type="number" id="modTpPrice" placeholder="输入价格">
          </div>
          <div class="range-wrap" style="margin: 0;">
            <div class="range-header"><span>止盈平仓数量</span><span style="color:var(--text);font-weight:800" id="tpLotsText">1.00 手</span></div>
            <input type="range" id="tpLotsSlider" min="0.01" max="1.00" step="0.01" value="1.00">
          </div>
        </div>

        <div style="margin-bottom: 1.25rem; padding: 1rem; border: 1px solid var(--line); border-radius: 0.75rem;">
          <div class="form-row" style="margin-bottom: 0.75rem;">
            <label style="color:var(--red)">止损触发价 (S/L)</label>
            <input type="number" id="modSlPrice" placeholder="输入价格">
          </div>
          <div class="range-wrap" style="margin: 0;">
            <div class="range-header"><span>止损平仓数量</span><span style="color:var(--text);font-weight:800" id="slLotsText">1.00 手</span></div>
            <input type="range" id="slLotsSlider" min="0.01" max="1.00" step="0.01" value="1.00">
          </div>
        </div>

        <button class="cta" style="background:var(--text); color:#fff; width:100%" onclick="submitModifyOrder()">保存修改</button>
        <button class="lock-btn" onclick="executeLockPosition()">🔒 一键对冲锁仓</button>
      </div>
    </div>
  </div>

  <div class="modalMask" id="calendarMask" onclick="closeModal(event, 'calendarMask')">
    <div class="modal" style="height: 80vh;">
      <div class="modalHeader">
        <span>当月交易日历</span>
        <button class="btn" style="border:none; padding:0.25rem 0.5rem;" onclick="$('calendarMask').style.display='none'">✕</button>
      </div>
      <div class="modalBody">
        <div style="text-align:center; font-weight:800; font-size:1.125rem; margin-bottom:1rem;">2024 年 5 月</div>
        <div class="cal-header">
          <div>日</div><div>一</div><div>二</div><div>三</div><div>四</div><div>五</div><div>六</div>
        </div>
        <div class="cal-grid" id="calGrid"></div>
      </div>
    </div>
  </div>

  <div class="modalMask" id="levMask" onclick="closeModal(event, 'levMask')">
    <div class="modal">
      <div class="modalHeader"><span>调整杠杆倍数</span><button class="btn" style="border:none; padding:0.25rem 0.5rem;" onclick="$('levMask').style.display='none'">✕</button></div>
      <div class="modalBody">
        <div style="display:flex; justify-content:space-between; margin-bottom:1rem;">
          <span style="color:var(--muted); font-weight:700;">当前选择杠杆</span>
          <span style="font-size:1.125rem; font-weight:800;"><span id="levTextModal">20</span>x</span>
        </div>
        <div class="range-wrap" style="margin-top:0;">
          <input type="range" id="levSlider" min="1" max="100" step="1" value="20">
        </div>
        <div style="color:#d97706; font-size:0.75rem; font-weight:700; margin-bottom:1.25rem;">* 提示：调整杠杆会重算占用资金及止损额度估值。</div>
        <button class="cta" style="background:var(--text); color:#fff; width:100%" onclick="$('levMask').style.display='none'">确认修改</button>
      </div>
    </div>
  </div>

  <div class="modalMask" id="orderTypeMask" onclick="closeModal(event, 'orderTypeMask')">
    <div class="modal">
      <div class="modalHeader"><span>选择交易类型</span><button class="btn" style="border:none; padding:0.25rem 0.5rem;" onclick="$('orderTypeMask').style.display='none'">✕</button></div>
      <div class="modalBody" style="padding: 0;">
        <div class="select-item" onclick="setOrderType('market', '市价')">市价</div>
        <div class="select-item" onclick="setOrderType('market_tpsl', '市价止盈止损')">市价止盈止损</div>
        <div class="select-item" onclick="setOrderType('limit', '限价单')">限价单</div>
        <div class="select-item active" onclick="setOrderType('limit_tpsl', '限价止盈止损')">限价止盈止损</div>
      </div>
    </div>
  </div>

  <div class="modalMask" id="pairMask" onclick="closeModal(event, 'pairMask')">
    <div class="modal">
      <div class="modalHeader"><span id="pairModalTitle">切换交易品种</span><button class="btn" style="border:none; padding:0.25rem 0.5rem;" onclick="$('pairMask').style.display='none'">✕</button></div>
      <div class="modalBody" id="pairListContainer">
        <!-- JS 动态生成 -->
      </div>
    </div>
  </div>

  <script>
    const $ = id => document.getElementById(id);

    // 6. 消除 300ms 点击延迟 (虽然 Viewport 已解决，但保留 touch-action 以防万一)
    // 此外使用 passive event listeners 优化滚动性能
    document.addEventListener('touchstart', function(){}, {passive: true});

    const quantState = {
      equity: 10125.50,         
      availMargin: 9540.20,
      price: 2345.50,           
      contractSize: 100,        
      pointSize: 0.01,          
      marginPct: 10,
      leverage: 20,             
      lots: 0,
      orderType: 'limit_tpsl',
      pendingSide: '' 
    };

    let quizAnswers = {};

    function updateCalculations() {
      const { marginPct, leverage, price, contractSize, pointSize, equity, availMargin } = quantState;
      const usedMargin = availMargin * (marginPct / 100);
      const notional = usedMargin * leverage;
      let calculatedLots = notional / (contractSize * price);
      calculatedLots = Math.floor(calculatedLots * 100) / 100; 
      
      quantState.lots = calculatedLots;

      $('pctText').innerText = marginPct;
      $('lotsText').innerText = calculatedLots.toFixed(2);

      [2, 3, 5, 8, 10].forEach(pct => {
        $(`sl_${pct}`).innerText = (notional * (pct / 100)).toLocaleString('en-US', {minimumFractionDigits:2}) + " USD";
      });

      const perPointMoney = calculatedLots * contractSize * pointSize;
      const liqPrice = calculatedLots > 0 ? Math.max(0, price - (equity / (calculatedLots * contractSize))) : 0;

      $('calcMargin').innerText = usedMargin.toLocaleString('en-US', {minimumFractionDigits:2}) + " USD";
      $('calcPpVal').innerText = perPointMoney.toFixed(2) + " USD";
      $('calcLiq').innerText = calculatedLots > 0 ? liqPrice.toLocaleString('en-US', {minimumFractionDigits:2}) : "0.00";
    }

    function setOrderType(typeCode, typeName) {
      quantState.orderType = typeCode;
      $('orderTypeText').innerText = typeName;
      $('orderTypeMask').style.display = 'none';
      
      document.querySelectorAll('#orderTypeMask .select-item').forEach(el => {
        el.classList.remove('active');
        if(el.innerText === typeName) el.classList.add('active');
      });

      const area = $('dynamicFormArea');
      const renderInput = (lbl, placeholder) => `
        <div class="form-row" style="cursor:text">
          <label>${lbl}</label><input type="number" placeholder="${placeholder}">
        </div>`;
      
      let html = '';
      if(typeCode === 'market') { html += renderInput('点差', '0.00'); } 
      else if(typeCode === 'market_tpsl') { html += renderInput('止盈价', '0.00'); html += renderInput('止损价', '0.00'); html += renderInput('点差', '0.00'); } 
      else if(typeCode === 'limit') { html += renderInput('触发价', '0.00'); }
      else if(typeCode === 'limit_tpsl') { html += renderInput('止盈价', '0.00'); html += renderInput('止损价', '0.00'); html += renderInput('触发价', '0.00'); }
      
      html += renderInput('有效时间 (分钟)', '输入过期分钟数');
      area.innerHTML = html;
    }

    function validateFormInputs() {
      const area = $('dynamicFormArea');
      const inputs = area.querySelectorAll('input');
      const labels = area.querySelectorAll('label');
      const errors = [];

      inputs.forEach((input, index) => {
        const label = labels[index] ? labels[index].innerText : '字段' + (index + 1);
        const value = input.value;
        if (value === '' || value === null || value === undefined) {
          errors.push(`${label} 不能为空`);
        } else if (!isNaN(value) && parseFloat(value) === 0) {
          errors.push(`${label} 不能为0`);
        }
      });
      return errors;
    }

    function initiateOrder(side) {
      const validationErrors = validateFormInputs();
      if (validationErrors.length > 0) {
        const errorList = $('errorPopupList');
        errorList.innerHTML = validationErrors.map(err => `<div class="error-popup-item">${err}</div>`).join('');
        $('errorPopup').classList.add('show');
        return;
      }

      quantState.pendingSide = side;
      quizAnswers = {};
      document.querySelectorAll('.quiz-opt').forEach(el => el.classList.remove('selected'));
      $('quizMask').style.display = 'flex';
    }

    function selectQuiz(el, qIndex, answer) {
      const parent = el.parentElement;
      parent.querySelectorAll('.quiz-opt').forEach(opt => opt.classList.remove('selected'));
      el.classList.add('selected');
      quizAnswers[qIndex] = answer;
    }

    function confirmOrderAfterQuiz() {
      if(Object.keys(quizAnswers).length < 3) return alert('请先完成所有风控自检题！');
      $('quizMask').style.display = 'none';
      const formData = getFormInputs();
      
      API.submitOrder(
        $('symName').innerText, 
        quantState.pendingSide, 
        quantState.orderType, 
        quantState.marginPct, 
        quantState.leverage, 
        quantState.lots,
        { quiz: quizAnswers, ...formData }
      ).then(() => {
        addToPendingOrders(
          $('symName').innerText,
          quantState.pendingSide,
          quantState.orderType,
          quantState.lots,
          formData
        );
        alert(`指令发送成功！\n类型：${quantState.orderType}\n方向：${quantState.pendingSide}\n计算出对应手数：${quantState.lots.toFixed(2)}手`);
      });
    }

    function getFormInputs() {
      const area = $('dynamicFormArea');
      const inputs = area.querySelectorAll('input');
      const data = {};
      const labels = area.querySelectorAll('label');
      inputs.forEach((input, index) => {
        const label = labels[index] ? labels[index].innerText : 'field' + index;
        data[label] = input.value;
      });
      return data;
    }

    function addToPendingOrders(symbol, side, type, lots, formData) {
      const ordersList = $('list-orders');
      if (ordersList.querySelector('.posItem') && ordersList.querySelector('.posItem').innerText.includes('暂无')) {
        ordersList.innerHTML = '';
      }
      const orderId = 'ORD_' + Date.now().toString().slice(-6);
      const now = new Date();
      const timeStr = now.toTimeString().slice(0, 8);
      const sideClass = side === 'BUY' ? 'buy' : 'sell';
      const sideText = side === 'BUY' ? 'Buy' : 'Sell';
      let formInfo = '';
      for (const [key, value] of Object.entries(formData)) {
        if (value) formInfo += `<div><div class="mini">${key}</div><div class="big">${value}</div></div>`;
      }
      const orderHTML = `
        <div class="posItem">
          <div class="posTop">
            <div>
              <div class="posTitle"><span class="sideTag ${sideClass}">${sideText}</span> ${symbol}</div>
              <div class="mini" style="margin-top: 0.5rem;">交易类型</div>
              <div style="font-size: 0.875rem; font-weight: 800;">${type}</div>
            </div>
            <div style="text-align:right">
              <div class="mini">订单号</div>
              <div class="big" style="font-family: monospace;">#${orderId}</div>
              <div class="mini" style="margin-top:0.375rem">下单时间 <span style="color:var(--text); font-weight:800">${timeStr}</span></div>
            </div>
          </div>
          <div class="posGrid">
            <div><div class="mini">交易手数</div><div class="big">${lots.toFixed(2)}</div></div>
            <div><div class="mini">仓位占比</div><div class="big">${quantState.marginPct}%</div></div>
            <div><div class="mini">杠杆</div><div class="big">1:${quantState.leverage}</div></div>
            ${formInfo}
          </div>
          <div class="posActions">
            <button class="ghost" onclick="alert('撤单接口: ${orderId}')">撤单</button>
          </div>
        </div>
      `;
      ordersList.insertAdjacentHTML('beforeend', orderHTML);
      updateOrdersCount();
    }

    function updateOrdersCount() {
      const ordersList = $('list-orders');
      const orderItems = ordersList.querySelectorAll('.posItem');
      const count = orderItems.length;
      document.querySelectorAll('.segTabs .seg')[1].innerHTML = `当前委托 (${count})`;
    }

    function openModifyOrderPanel() {
      const currentLots = parseFloat($('posLotsVal').innerText);
      const tpSlider = $('tpLotsSlider');
      const slSlider = $('slLotsSlider');
      tpSlider.max = currentLots; tpSlider.value = currentLots;
      slSlider.max = currentLots; slSlider.value = currentLots;
      $('tpLotsText').innerText = currentLots.toFixed(2) + " 手";
      $('slLotsText').innerText = currentLots.toFixed(2) + " 手";
      tpSlider.oninput = function() { $('tpLotsText').innerText = parseFloat(this.value).toFixed(2) + " 手"; }
      slSlider.oninput = function() { $('slLotsText').innerText = parseFloat(this.value).toFixed(2) + " 手"; }
      $('modifyMask').style.display = 'flex';
    }

    function submitModifyOrder() {
      const tpP = $('modTpPrice').value; const tpL = $('tpLotsSlider').value;
      const slP = $('modSlPrice').value; const slL = $('slLotsSlider').value;
      API.modifyPosition('MT4_8821', tpP, tpL, slP, slL).then(() => {
        alert(`修改成功！\n止盈: ${tpL}手 @${tpP||'未设'}\n止损: ${slL}手 @${slP||'未设'}`);
        $('modifyMask').style.display = 'none';
      });
    }

    function executeLockPosition() {
      const tpPrice = $('modTpPrice').value;
      const slPrice = $('modSlPrice').value;
      if (!tpPrice || tpPrice.trim() === '' || !slPrice || slPrice.trim() === '') {
        alert('❌ 无法执行锁仓！\n\n原因：止盈价格和止损价格都必须填写才能进行锁仓操作。\n\n请先在下方设置止盈价和止损价。');
        return;
      }
      if (confirm('警告：一键锁仓将开立相同手数的反向订单对冲，是否继续？')) {
        API.lockPosition('MT4_8821').then(() => {
          alert('锁仓指令已执行。');
          $('modifyMask').style.display = 'none';
        });
      }
    }

    function openCalendar() {
      $('calendarMask').style.display = 'flex';
      renderCalendar();
    }

    async function renderCalendar() {
      const grid = $('calGrid');
      grid.innerHTML = '';
      for(let i=0; i<3; i++) grid.innerHTML += `<div class="cal-day empty"></div>`;
      const data = await API.getCalendarPnL(2024, 5);
      for(let i=1; i<=31; i++) {
        let pnlStr = '';
        if(data[i]) {
          const val = parseFloat(data[i]);
          const color = val > 0 ? 'var(--green)' : 'var(--red)';
          const sign = val > 0 ? '+' : '';
          pnlStr = `<div class="cal-pnl" style="color:${color}">${sign}${val}</div>`;
        }
        grid.innerHTML += `
          <div class="cal-day">
            <div class="cal-date">${i}</div>
            ${pnlStr}
          </div>
        `;
      }
    }

    let lastDataTick = Date.now();
    setInterval(() => {
      if (Math.random() > 0.4) lastDataTick = Date.now();
      const diff = Date.now() - lastDataTick;
      const dot = $('latencySignal');
      if (diff < 3000) { dot.className = 'signal-dot green'; dot.title = '延迟极低 (<3s)'; } 
      else if (diff < 5000) { dot.className = 'signal-dot yellow'; dot.title = '网络波动 (3-5s)'; } 
      else { dot.className = 'signal-dot red'; dot.title = '连接缓慢 (>5s)'; }
    }, 1000);

    window.onload = () => {
      setOrderType('limit_tpsl', '限价止盈止损');
      const marginSlider = $('marginSlider');
      marginSlider.style.setProperty('--track-fill', marginSlider.value + '%');
      marginSlider.oninput = function() {
        quantState.marginPct = parseInt(this.value);
        this.style.setProperty('--track-fill', this.value + '%');
        updateCalculations();
      };
      const levSlider = $('levSlider');
      levSlider.style.setProperty('--track-fill', (levSlider.value / levSlider.max * 100) + '%');
      levSlider.oninput = function() {
        quantState.leverage = parseInt(this.value);
        this.style.setProperty('--track-fill', (this.value / this.max * 100) + '%');
        $('levTextModal').innerText = quantState.leverage;
        $('btnLev').innerText = `杠杆 ${quantState.leverage}x ▼`;
        updateCalculations();
      };
      updateCalculations();
    };

    function switchMainTab(el) { document.querySelectorAll('.tabs .tab').forEach(t => t.classList.remove('active')); el.classList.add('active'); }
    function switchBottomTab(target) {
      document.querySelectorAll('.segTabs .seg').forEach(el => el.classList.remove('active'));
      event.target.classList.add('active');
      $('list-positions').classList.toggle('active', target === 'positions');
      $('list-orders').classList.toggle('active', target === 'orders');
    }
    function closeModal(e, id) { if(e.target.id === id) $(id).style.display = 'none'; }
    function closeErrorPopup(e) { if(e.target.id === 'errorPopup') $('errorPopup').classList.remove('show'); }
    
    const categoryPairs = {
      'forex': [
        { name: 'EURUSD', price: 1.0850 }, { name: 'GBPUSD', price: 1.2640 }, { name: 'USDJPY', price: 149.50 },
        { name: 'AUDUSD', price: 0.6520 }, { name: 'USDCAD', price: 1.3580 }, { name: 'USDCHF', price: 0.8840 },
        { name: 'NZDUSD', price: 0.6080 }, { name: 'EURGBP', price: 0.8580 }
      ],
      'index': [
        { name: 'US30', price: 38500 }, { name: 'US500', price: 5120 }, { name: 'NAS100', price: 17800 },
        { name: 'GER40', price: 18650 }, { name: 'UK100', price: 8020 }, { name: 'JPN225', price: 39800 },
        { name: 'HK50', price: 17800 }, { name: 'AUS200', price: 7850 }
      ],
      'commodity': [
        { name: 'XTIUSD', price: 78.50 }, { name: 'XBRUSD', price: 82.30 }, { name: 'XNGUSD', price: 2.85 },
        { name: 'XCUUSD', price: 3.85 }, { name: 'XPTUSD', price: 980.50 }, { name: 'XPDUSD', price: 1020.30 },
        { name: 'CL-OIL', price: 78.50 }, { name: 'NG-GAS', price: 2.85 }
      ],
      'metal': [
        { name: 'XAUUSD', price: 2345.50 }, { name: 'XAGUSD', price: 28.50 }, { name: 'XAUAUD', price: 3580.20 }, { name: 'XAGAUD', price: 43.80 }
      ],
      'stock': [
        { name: 'AAPL', price: 185.50 }, { name: 'GOOGL', price: 142.30 }, { name: 'MSFT', price: 415.20 },
        { name: 'AMZN', price: 178.50 }, { name: 'TSLA', price: 245.80 }, { name: 'NVDA', price: 875.30 },
        { name: 'META', price: 485.20 }, { name: 'BABA', price: 82.50 }
      ]
    };
    const categoryNames = { 'forex': '外汇', 'index': '指数', 'commodity': '大宗商品', 'metal': '贵金属', 'stock': '股票' };

    function showCategoryPairs(category) {
      const container = $('pairListContainer');
      const title = $('pairModalTitle');
      const pairs = categoryPairs[category] || [];
      title.innerText = '选择' + (categoryNames[category] || '交易品种');
      let html = '';
      pairs.forEach(pair => {
        html += `<div class="select-item" onclick="setSymbol('${pair.name}', ${pair.price})">${pair.name}</div>`;
      });
      container.innerHTML = html;
      $('pairMask').style.display = 'flex';
    }

    function setSymbol(name, price) {
      $('symName').innerText = name; quantState.price = price;
      $('midPriceText').innerText = price.toFixed(name === 'XAUUSD' ? 2 : 4);
      $('pairMask').style.display = 'none';
      updateCalculations();
    }
  </script>
</body>
</html>"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/v1/order', methods=['POST'])
def submit_order():
    data = request.json
    print(f"【API】收到下单请求: {data}")
    
    # 模拟创建订单
    new_order = {
        "id": f"ORD_{int(datetime.now().timestamp())}",
        "symbol": data.get('symbol'),
        "side": data.get('side'),
        "type": data.get('type'),
        "lots": data.get('lots'),
        "status": "PENDING",
        "created_at": datetime.now().strftime("%H:%M:%S")
    }
    orders.append(new_order)
    
    return jsonify({
        "success": True, 
        "message": "订单已提交",
        "order": new_order
    })

@app.route('/api/v1/position/modify', methods=['POST'])
def modify_position():
    data = request.json
    position_id = data.get('positionId')
    print(f"【API】修改持仓: {data}")
    
    # 模拟查找并修改持仓
    for pos in positions:
        if pos['id'] == position_id:
            pos['tp'] = data.get('tpPrice')
            pos['sl'] = data.get('slPrice')
            return jsonify({"success": True, "message": "持仓已修改", "position": pos})
            
    return jsonify({"success": False, "message": "持仓不存在"}), 404

@app.route('/api/v1/position/lock', methods=['POST'])
def lock_position():
    data = request.json
    position_id = data.get('positionId')
    print(f"【API】执行锁仓: {position_id}")
    
    # 模拟锁仓逻辑（创建反向订单）
    return jsonify({"success": True, "message": "锁仓指令已执行"})

@app.route('/api/v1/calendar', methods=['GET'])
def get_calendar_pnl():
    year = request.args.get('year')
    month = request.args.get('month')
    print(f"【API】获取日历数据: {year}-{month}")
    
    # 模拟生成随机盈亏数据
    data = {}
    for i in range(1, 32):
        if random.random() > 0.3:
            data[i] = round(random.uniform(-80, 200), 2)
            
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
