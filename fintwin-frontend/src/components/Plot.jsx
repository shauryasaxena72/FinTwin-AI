import React from 'react';
import Plot from 'react-plotly.js';

export default function CashPlot({ results, showExpected = true }) {
  if (!results?.cashflow?.length) return <div className="empty-chart"><div className="empty-icon">↗</div><strong>Forecast appears here</strong><span>Upload and confirm financial data to generate a cash-flow projection.</span></div>;
  const rows = results.cashflow;
  const traces = [];
  const plans = [...new Set(rows.map(r => r.plan_name || 'Selected plan'))];
  plans.forEach((plan, i) => {
    const data = rows.filter(r => (r.plan_name || 'Selected plan') === plan);
    traces.push({ x: data.map(r => r.month), y: data.map(r => r.closing_cash), type: 'scatter', mode: 'lines+markers', name: plan, line: { width: 3, color: i ? '#9a8cff' : '#6de0a6' }, hovertemplate: '%{x}<br>Closing cash: %{y:,.2f}<extra>'+plan+'</extra>' });
  });
  if (showExpected && rows.some(r => r.expected_inflow > 0)) traces.push({ x: rows.map(r=>r.month), y: rows.map(r=>r.expected_inflow), type:'bar', name:'Expected inflow', marker:{color:'rgba(154,140,255,.24)', pattern:{shape:'/'}}, yaxis:'y2', hovertemplate:'%{x}<br>Expected inflow: %{y:,.2f}<extra></extra>' });
  const reserve = results.reserve;
  if (typeof reserve === 'number') traces.push({ x: [rows[0].month, rows[rows.length-1].month], y:[reserve,reserve], type:'scatter', mode:'lines', name:'Minimum reserve', line:{color:'#ff7777',width:2,dash:'dash'}, hovertemplate:'Minimum reserve: %{y:,.2f}<extra></extra>' });
  return <Plot data={traces} layout={{ autosize:true, paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)', font:{color:'#a8b5ae',family:'Inter,system-ui,sans-serif',size:11}, margin:{l:58,r:18,t:24,b:48}, legend:{orientation:'h',y:-.24}, xaxis:{gridcolor:'#202b25',linecolor:'#2a3830'}, yaxis:{title:'Cash balance',gridcolor:'#202b25',zerolinecolor:'#2a3830',tickformat:'~s'}, yaxis2:{overlaying:'y',side:'right',visible:false}, hovermode:'x unified', shapes: rows.map((r,i)=>r.breach?{type:'line',x0:r.month,x1:r.month,y0:0,y1:1,yref:'paper',line:{color:'#ff7777',width:1,dash:'dot'}}:null).filter(Boolean) }} config={{displayModeBar:false,responsive:true}} style={{width:'100%',height:'340px'}} />;
}
