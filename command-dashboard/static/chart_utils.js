/* ===================================================================
   chart_utils.js — 共用圖表繪製（Dashboard + 情境設計器）
   從 commander_dashboard.html drawSparkline 抽出
   =================================================================== */

/**
 * drawSparkline(canvasId, datasets, opts, N, expanded, times)
 *
 * @param {string}  canvasId   - canvas 元素 ID
 * @param {Array}   datasets   - [{data, color, w, fill, fillColor, dash, unit, label,
 *                                 extraData, extraUnit}]
 * @param {Object}  opts       - {yMin, yMax, yUnit, noEndLabel, hover,
 *                                thresholds, stackedArea, gridSteps,
 *                                rightAxis:{max, unit, label}}
 * @param {number}  N          - 資料點數
 * @param {boolean} expanded   - 是否展開模式
 * @param {Array}   times      - X 軸時間標籤
 */

// 全域共用 tooltip div
let _chartTooltip = null;
function _getTooltip() {
  if (!_chartTooltip) {
    _chartTooltip = document.createElement('div');
    _chartTooltip.style.cssText =
      'position:fixed;pointer-events:none;z-index:9999;display:none;' +
      'background:rgba(13,17,23,.96);border:1px solid rgba(48,54,61,.8);border-radius:6px;' +
      'padding:7px 11px;font:11px IBM Plex Mono,monospace;color:#e6edf3;' +
      'box-shadow:0 4px 16px rgba(0,0,0,.6);white-space:nowrap;line-height:1.8;';
    document.body.appendChild(_chartTooltip);
  }
  return _chartTooltip;
}

// 各 canvas 的 hover listener 參照（避免重複掛載）
const _hoverState = {};

function drawSparkline(canvasId, datasets, opts, N, expanded, times) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const par = canvas.parentElement;
  const W = par.clientWidth, H = par.clientHeight;
  if (!W || !H) return;
  canvas.width = W * devicePixelRatio;
  canvas.height = H * devicePixelRatio;
  const ctx = canvas.getContext('2d');
  ctx.scale(devicePixelRatio, devicePixelRatio);

  const fs = expanded ? {axis:11, threshold:10, value:13, dot:3.5} : {axis:7, threshold:7, value:9, dot:2};
  const hasRightAxis = expanded && opts.rightAxis;
  // hasRightAxis 時右側需容納兩個 zone：末端標籤（~36px）+ 右軸數字（~30px）
  const pad = expanded ? {t:8, r: hasRightAxis ? 72 : 44, b:24, l:40} : {t:2, r:4, b:2, l:4};
  const cW = W-pad.l-pad.r, cH = H-pad.t-pad.b;
  const yMin = opts.yMin||0, yMax = opts.yMax||100, yR = yMax-yMin||1;
  function px(i){ return pad.l + (i/Math.max(N-1,1)) * cW; }
  function py(v){ return pad.t + cH - ((v-yMin)/yR)*cH; }

  // 展開：左側 Y 軸 grid
  if (expanded) {
    const steps = opts.gridSteps || _autoGridSteps(yMin, yMax);
    ctx.strokeStyle='rgba(110,118,129,.2)'; ctx.lineWidth=0.5;
    ctx.fillStyle='#8b949e'; ctx.font=fs.axis+'px IBM Plex Mono,monospace'; ctx.textAlign='right';
    steps.forEach(v => {
      if (v < yMin || v > yMax) return;
      const y = py(v);
      ctx.beginPath(); ctx.moveTo(pad.l,y); ctx.lineTo(pad.l+cW,y); ctx.stroke();
      ctx.fillText(v + (opts.yUnit||''), pad.l-4, y+4);
    });
  }

  // 右側 Y 軸（zone 2：raX = cW+40 起，zone 1：cW+4~36 留給末端標籤）
  if (hasRightAxis) {
    const ra = opts.rightAxis;
    const raMax = ra.max || 100;
    const raSteps = _autoGridSteps(0, raMax);
    const raX = pad.l + cW + 40;
    ctx.fillStyle='#8b949e'; ctx.font=fs.axis+'px IBM Plex Mono,monospace'; ctx.textAlign='left';
    raSteps.forEach(v => {
      const leftV = (v / raMax) * (yMax - yMin) + yMin;
      const y = py(leftV);
      ctx.fillText(v + (ra.unit||''), raX, y + 4);
    });
    if (ra.label) {
      ctx.fillStyle='#6e7681'; ctx.font=(fs.axis-1)+'px IBM Plex Mono,monospace';
      ctx.fillText(ra.label, raX, pad.t - 1);
    }
  }

  // 門檻線
  (opts.thresholds||[]).forEach(th => {
    ctx.strokeStyle=th.color; ctx.lineWidth=expanded?1:0.5; ctx.setLineDash([4,3]);
    const y = py(th.value);
    ctx.beginPath(); ctx.moveTo(pad.l,y); ctx.lineTo(pad.l+cW,y); ctx.stroke();
    ctx.setLineDash([]);
    if (expanded) {
      ctx.fillStyle=th.color; ctx.font=fs.threshold+'px IBM Plex Mono,monospace'; ctx.textAlign='left';
      ctx.fillText(th.label||th.value, pad.l+cW+3, y+4);
    }
  });

  // 堆疊面積
  if (opts.stackedArea) {
    const cumul = Array(N).fill(0);
    opts.stackedArea.forEach(layer => {
      const top = layer.data.map((v,i) => cumul[i] + (v||0));
      ctx.beginPath();
      for (let i=0; i<N; i++) { i===0 ? ctx.moveTo(px(i), py(top[i])) : ctx.lineTo(px(i), py(top[i])); }
      for (let i=N-1; i>=0; i--) { ctx.lineTo(px(i), py(cumul[i])); }
      ctx.closePath();
      ctx.fillStyle = layer.fillColor; ctx.fill();
      top.forEach((v,i) => cumul[i] = v);
    });
  }

  // 線條 + 資料點
  datasets.forEach(ds => {
    if (ds.fill) {
      ctx.beginPath();
      ds.data.forEach((v,i) => { i===0 ? ctx.moveTo(px(i),py(v)) : ctx.lineTo(px(i),py(v)); });
      ctx.lineTo(px(N-1),py(yMin)); ctx.lineTo(px(0),py(yMin)); ctx.closePath();
      ctx.fillStyle = ds.fillColor||'rgba(100,150,255,.1)'; ctx.fill();
    }
    ctx.strokeStyle=ds.color; ctx.lineWidth=expanded?(ds.w||1.5)*1.5:(ds.w||1.5); ctx.lineJoin='round';
    ctx.setLineDash(ds.dash||[]);
    ctx.beginPath();
    ds.data.forEach((v,i) => { i===0 ? ctx.moveTo(px(i),py(v)) : ctx.lineTo(px(i),py(v)); });
    ctx.stroke(); ctx.setLineDash([]);

    if (expanded) {
      // 資料點
      ds.data.forEach((v,i) => {
        ctx.fillStyle=ds.color; ctx.beginPath(); ctx.arc(px(i),py(v),fs.dot,0,Math.PI*2); ctx.fill();
      });
      // 末端數值標籤（opts.noEndLabel 時省略）
      if (!opts.noEndLabel) {
        const lv = ds.data[N-1];
        if (lv != null) {
          ctx.fillStyle=ds.color; ctx.font='bold '+fs.value+'px IBM Plex Mono,monospace'; ctx.textAlign='left';
          ctx.fillText(lv+(ds.unit||''), px(N-1)+6, py(lv)+4);
        }
      }
    }
  });

  // 展開：X 軸時間標籤
  if (expanded && times && times.length >= N) {
    ctx.fillStyle='#8b949e'; ctx.font=fs.axis+'px IBM Plex Mono,monospace'; ctx.textAlign='center';
    const step = N <= 15 ? 1 : N <= 30 ? 2 : 3;
    for (let i=0; i<N; i++) {
      if (i % step === 0 || i === N-1) ctx.fillText(times[i], px(i), H-3);
    }
  }

  // ── Hover 互動 ────────────────────────────────────────────────
  // 清除舊 listener（避免重複掛載）
  if (_hoverState[canvasId]) {
    const {mm, ml} = _hoverState[canvasId];
    canvas.removeEventListener('mousemove', mm);
    canvas.removeEventListener('mouseleave', ml);
    delete _hoverState[canvasId];
  }

  if (expanded && opts.hover) {
    // 靜態快照：hover 時先還原此快照再疊高亮點
    const snapshot = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const dpr = devicePixelRatio;

    function restoreSnapshot() {
      ctx.save();
      ctx.setTransform(1,0,0,1,0,0); // putImageData 不受 transform 影響，需先重置
      ctx.putImageData(snapshot, 0, 0);
      ctx.restore(); // 恢復 scale(dpr, dpr)
    }

    const SNAP_R = 22; // 邏輯像素，游標距點在此半徑內才觸發
    const mm = (e) => {
      const rect = canvas.getBoundingClientRect();
      // 換算到 canvas 邏輯座標
      const logicX = (e.clientX - rect.left) * (W / rect.width);
      const logicY = (e.clientY - rect.top)  * (H / rect.height);

      // 找 2D 距離最近的資料點，距離超過 SNAP_R 則不顯示
      let nearest = -1, minD2 = SNAP_R * SNAP_R;
      for (let i = 0; i < N; i++) {
        const dx = px(i) - logicX;
        for (const ds of datasets) {
          const v = ds.data[i];
          if (v == null) continue;
          const dy = py(v) - logicY;
          const d2 = dx*dx + dy*dy;
          if (d2 < minD2) { minD2 = d2; nearest = i; }
        }
      }
      if (nearest === -1) {
        restoreSnapshot();
        _getTooltip().style.display = 'none';
        return;
      }
      // 還原靜態畫面，再疊高亮點
      restoreSnapshot();
      datasets.forEach(ds => {
        const v = ds.data[nearest];
        if (v == null) return;
        ctx.fillStyle = ds.color;
        ctx.strokeStyle = 'rgba(230,236,240,.85)';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(px(nearest), py(v), fs.dot * 2.2, 0, Math.PI*2);
        ctx.fill();
        ctx.stroke();
      });
      // 建 tooltip
      let html = '';
      if (times && times[nearest]) {
        html += `<div style="color:#8b949e;border-bottom:1px solid rgba(48,54,61,.6);` +
                `margin-bottom:5px;padding-bottom:3px">${times[nearest]}</div>`;
      }
      datasets.forEach(ds => {
        const v = ds.data[nearest];
        if (v == null) return;
        const pct = v + (ds.unit||'');
        const abs = ds.extraData ? ` / ${ds.extraData[nearest]}${ds.extraUnit||''}` : '';
        const lbl = ds.label ? ds.label + '&ensp;' : '';
        html += `<div><span style="color:${ds.color}">●</span>&ensp;${lbl}<b>${pct}${abs}</b></div>`;
      });
      // hoverExtra：只在 tooltip 顯示，不繪製線條（stackedArea 分解、補充數值等）
      (opts.hoverExtra||[]).forEach(he => {
        const v = he.data[nearest];
        if (v == null) return;
        const lbl = he.label ? he.label + '&ensp;' : '';
        html += `<div style="color:${he.color||'#8b949e'}"><span>●</span>&ensp;${lbl}<b>${v}${he.unit||''}</b></div>`;
      });
      const tip = _getTooltip();
      tip.innerHTML = html;
      tip.style.display = 'block';
      // 位置：貼游標右上，防右溢
      const tipW = tip.offsetWidth || 140;
      const tx = Math.min(e.clientX + 14, window.innerWidth - tipW - 8);
      tip.style.left = tx + 'px';
      tip.style.top  = (e.clientY - 10) + 'px';
    };

    const ml = () => {
      restoreSnapshot();
      _getTooltip().style.display = 'none';
    };

    canvas.addEventListener('mousemove', mm);
    canvas.addEventListener('mouseleave', ml);
    _hoverState[canvasId] = {mm, ml};
  }
}

/** IPI 計算（high*3 + medium） */
function ipiCalc(h, m) { return h * 3 + m; }

function _autoGridSteps(yMin, yMax) {
  const range = yMax - yMin;
  const step = range <= 10 ? 2 : range <= 50 ? 10 : 25;
  const steps = [];
  for (let v = yMin; v <= yMax; v += step) steps.push(v);
  return steps;
}
