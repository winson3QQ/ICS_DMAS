/* ===================================================================
   chart_utils.js — 共用圖表繪製（Dashboard + 情境設計器）
   從 commander_dashboard.html drawSparkline 抽出
   =================================================================== */

/**
 * drawSparkline(canvasId, datasets, opts, N, expanded, times)
 *
 * @param {string}  canvasId   - canvas 元素 ID
 * @param {Array}   datasets   - [{data:[], color, w, fill, fillColor, dash, unit, label}]
 * @param {Object}  opts       - {yMin, yMax, thresholds:[{value,color,label}], stackedArea:[{data,fillColor}], gridSteps}
 * @param {number}  N          - 資料點數
 * @param {boolean} expanded   - 是否展開模式（顯示軸標籤、資料點）
 * @param {Array}   times      - X 軸時間標籤（展開時用）
 */
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
  const pad = expanded ? {t:8, r: hasRightAxis ? 52 : 44, b:24, l:40} : {t:2, r:4, b:2, l:4};
  const cW = W-pad.l-pad.r, cH = H-pad.t-pad.b;
  const yMin = opts.yMin||0, yMax = opts.yMax||100, yR = yMax-yMin||1;
  function px(i){ return pad.l + (i/Math.max(N-1,1)) * cW; }
  function py(v){ return pad.t + cH - ((v-yMin)/yR)*cH; }

  // 展開：Y 軸 grid
  if (expanded) {
    const steps = opts.gridSteps || _autoGridSteps(yMin, yMax);
    ctx.strokeStyle='rgba(110,118,129,.2)'; ctx.lineWidth=0.5;
    ctx.fillStyle='#8b949e'; ctx.font=fs.axis+'px IBM Plex Mono,monospace'; ctx.textAlign='right';
    steps.forEach(v => {
      if (v < yMin || v > yMax) return;
      const y = py(v);
      ctx.beginPath(); ctx.moveTo(pad.l,y); ctx.lineTo(pad.l+cW,y); ctx.stroke();
      ctx.fillText(v, pad.l-4, y+4);
    });
  }

  // 右側 Y 軸（絕對值）
  // opts.rightAxis = {label:'人', max:50} → 右軸 0~max，與左軸 yMin~yMax 對齊
  if (hasRightAxis) {
    const ra = opts.rightAxis;
    const raMax = ra.max || 100;
    const raSteps = _autoGridSteps(0, raMax);
    ctx.fillStyle='#8b949e'; ctx.font=fs.axis+'px IBM Plex Mono,monospace'; ctx.textAlign='left';
    raSteps.forEach(v => {
      // 右軸的 v 對應左軸的 (v/raMax)*(yMax-yMin)+yMin
      const leftV = (v / raMax) * (yMax - yMin) + yMin;
      const y = py(leftV);
      ctx.fillText(v + (ra.unit||''), pad.l + cW + 4, y + 4);
    });
    // 軸標籤
    if (ra.label) {
      ctx.fillStyle='#6e7681'; ctx.font=(fs.axis-1)+'px IBM Plex Mono,monospace';
      ctx.fillText(ra.label, pad.l + cW + 4, pad.t - 1);
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

  // 線條
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

    // 展開：資料點 + 末端數值
    if (expanded) {
      ds.data.forEach((v,i) => {
        ctx.fillStyle=ds.color; ctx.beginPath(); ctx.arc(px(i),py(v),fs.dot,0,Math.PI*2); ctx.fill();
      });
      const lv = ds.data[N-1];
      if (lv != null) {
        ctx.fillStyle=ds.color; ctx.font='bold '+fs.value+'px IBM Plex Mono,monospace'; ctx.textAlign='left';
        ctx.fillText(lv+(ds.unit||''), px(N-1)+6, py(lv)+4);
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
