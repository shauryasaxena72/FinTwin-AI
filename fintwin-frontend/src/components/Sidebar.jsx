import React from 'react';
import { Activity, ArrowLeftRight, Bot, ChartNoAxesCombined, ChevronDown, CircleHelp, FileUp, LayoutDashboard, Settings2, ShieldCheck, WalletCards } from 'lucide-react';
const items = [
  { label:'Intake & review', icon:FileUp, section:'WORKSPACE' },
  { label:'Overview', icon:LayoutDashboard, section:'WORKSPACE' },
  { label:'Digital Twin', icon:Activity, section:'ANALYZE' },
  { label:'Scenario Lab', icon:ChartNoAxesCombined, section:'ANALYZE' },
  { label:'Plan explorer', icon:ArrowLeftRight, section:'ANALYZE' },
  { label:'Grounded copilot', icon:Bot, section:'TOOLS' },
];
export default function Sidebar({ page, setPage, hasData }) {
 let last='';
 return <aside className="sidebar"><div className="brand"><div className="brand-mark">FT<span>·</span></div><div><strong>fintwin<span> ai</span></strong><small>FINANCIAL INTELLIGENCE</small></div></div><div className="workspace-switch"><div className="workspace-avatar">B</div><div><b>Business workspace</b><small>Local session</small></div><ChevronDown size={15}/></div><nav>{items.map(item=>{const Icon=item.icon; const heading=item.section!==last;last=item.section;return <React.Fragment key={item.label}>{heading&&<div className="nav-section">{item.section}</div>}<button className={`nav-item ${page===item.label?'active':''}`} onClick={()=>setPage(item.label)}><Icon size={17}/><span>{item.label}</span>{item.label==='Intake & review'&&<span className="nav-dot"/>}{item.label==='Plan explorer'&&!hasData&&<span className="nav-lock">—</span>}</button></React.Fragment>})}</nav><div className="sidebar-bottom"><div className="privacy-note"><ShieldCheck size={17}/><div><b>Your data, your control</b><span>Files stay in this session until sent to your configured backend.</span></div></div><button className="nav-item" onClick={()=>setPage('Settings & assumptions')}><Settings2 size={17}/>Settings & assumptions</button><button className="nav-item" onClick={()=>setPage('Help & methodology')}><CircleHelp size={17}/>Help & methodology</button><div className="user-profile"><div className="profile-avatar">K</div><div><b>Project workspace</b><small>FinTwin AI · Phase 1</small></div><WalletCards size={17}/></div></div></aside>;
}
