import React from "react";
import { Link } from "react-router-dom";
import {
  Activity, Compass, BarChart3, Bot, Microscope, Home, Database,
} from "lucide-react";

const Item = ({ icon: Icon, label, to, active = false }: { icon: any; label: string; to: string; active?: boolean }) => (
  <Link to={to} className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${active ? "bg-black text-white" : "text-black/40 hover:bg-black/5 hover:text-black"}`}>
    <Icon size={16} /><span className="text-xs font-medium">{label}</span>
  </Link>
);

/** Page chrome for the Compound Library pages (same look as the other app pages). */
export const LibraryShell: React.FC<{ title: string; subtitle?: string; children: React.ReactNode }> = ({ title, subtitle, children }) => (
  <div className="flex min-h-screen bg-[#F8F9FA] text-[#111111] font-sans p-4 md:p-6 gap-6">
    <aside className="w-64 bg-white rounded-[40px] border border-black/5 p-8 hidden lg:flex flex-col gap-10 flex-shrink-0">
      <Link to="/" className="flex items-center gap-2 px-4">
        <div className="w-8 h-8 bg-black rounded-lg flex items-center justify-center"><div className="w-4 h-4 border-2 border-white rounded-full" /></div>
        <span className="text-lg font-bold tracking-tighter">ELYSIUM</span>
      </Link>
      <nav aria-label="Main" className="space-y-1">
        <Item icon={Home} label="Home" to="/" />
        <Item icon={Activity} label="Runs" to="/discovery" />
        <Item icon={Compass} label="Discovery" to="/dashboard" />
        <Item icon={Database} label="Library" to="/library" active />
        <Item icon={Microscope} label="Graphs" to="/graphs" />
        <Item icon={Bot} label="Agent" to="/agent" />
        <Item icon={BarChart3} label="Analysis" to="/analysis" />
      </nav>
    </aside>
    <main className="flex-1 min-w-0 space-y-6">
      <header>
        <h1 className="text-4xl font-medium tracking-tight">{title}</h1>
        {subtitle && <p className="text-sm opacity-40 mt-1">{subtitle}</p>}
      </header>
      {children}
    </main>
  </div>
);
