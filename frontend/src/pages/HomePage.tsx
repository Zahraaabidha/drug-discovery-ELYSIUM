import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

// ── Animated DNA helix (CSS + SVG based) ─────────────────────────────────────
const DNAHero: React.FC = () => (
  <div className="relative w-full h-full flex items-center justify-center">
    {/* Outer slow ring */}
    <div className="absolute w-[420px] h-[420px] rounded-full border border-violet-200/40 animate-spin-slow" />
    {/* Inner reverse ring */}
    <div className="absolute w-[300px] h-[300px] rounded-full border border-violet-300/30 animate-spin-reverse" />
    {/* Core SVG helix */}
    <div className="relative w-[260px] h-[400px] animate-float">
      <svg viewBox="0 0 200 500" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full drop-shadow-xl">
        <defs>
          <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#7c3aed" stopOpacity="0.9"/>
            <stop offset="50%" stopColor="#a78bfa" stopOpacity="0.7"/>
            <stop offset="100%" stopColor="#c4b5fd" stopOpacity="0.3"/>
          </linearGradient>
          <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#6d28d9" stopOpacity="0.6"/>
            <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0.2"/>
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="blur"/>
            <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
        </defs>
        {/* Left strand */}
        <path d="M60 10 C20 50, 140 100, 100 150 C60 200, 140 250, 100 300 C60 350, 140 400, 100 450 C60 480, 100 490, 100 500"
          stroke="url(#g1)" strokeWidth="2.5" strokeLinecap="round" filter="url(#glow)" opacity="0.9"/>
        {/* Right strand */}
        <path d="M140 10 C180 50, 60 100, 100 150 C140 200, 60 250, 100 300 C140 350, 60 400, 100 450 C140 480, 100 490, 100 500"
          stroke="url(#g2)" strokeWidth="2.5" strokeLinecap="round" filter="url(#glow)" opacity="0.8"/>
        {/* Cross-links */}
        {[60, 110, 160, 210, 260, 310, 360, 410].map((y, i) => {
          const x1 = i % 2 === 0 ? 65 : 135;
          const x2 = i % 2 === 0 ? 135 : 65;
          return <line key={y} x1={x1} y1={y} x2={x2} y2={y} stroke="#a78bfa" strokeWidth="1.2" opacity="0.5"/>;
        })}
        {/* Nodes */}
        {[60, 110, 160, 210, 260, 310, 360, 410].map((y, i) => (
          <React.Fragment key={`n${y}`}>
            <circle cx={i % 2 === 0 ? 65 : 135} cy={y} r="5" fill="#7c3aed" opacity="0.8" filter="url(#glow)"/>
            <circle cx={i % 2 === 0 ? 135 : 65} cy={y} r="5" fill="#a78bfa" opacity="0.6" filter="url(#glow)"/>
          </React.Fragment>
        ))}
      </svg>
    </div>
    {/* Floating label card like MYDNA */}
    <div className="absolute bottom-16 left-4 bg-white/90 backdrop-blur-sm rounded-2xl px-4 py-3 border border-neutral-100 shadow-lg max-w-[180px]">
      <p className="text-[10px] text-neutral-400 uppercase tracking-wider mb-0.5">Molecular binding</p>
      <p className="text-sm font-semibold text-neutral-900">Good interaction with target</p>
      <span className="inline-block mt-1.5 text-[9px] bg-violet-100 text-violet-700 px-2 py-0.5 rounded-full font-medium">Learn more</span>
    </div>
  </div>
);

// ── Scroll-triggered fade ─────────────────────────────────────────────────────
const FadeUp: React.FC<{ children: React.ReactNode; delay?: number; className?: string }> = ({ children, delay = 0, className = "" }) => {
  const [v, setV] = useState(false);
  const r = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setV(true); obs.disconnect(); } }, { threshold: 0.1 });
    if (r.current) obs.observe(r.current);
    return () => obs.disconnect();
  }, []);
  return (
    <div ref={r} className={`transition-all duration-700 ${v ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"} ${className}`}
      style={{ transitionDelay: `${delay}ms` }}>
      {children}
    </div>
  );
};

// ── Animated counter ──────────────────────────────────────────────────────────
const Count: React.FC<{ to: number; suffix?: string }> = ({ to, suffix = "" }) => {
  const [val, setVal] = useState(0);
  const r = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const obs = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return;
      obs.disconnect();
      const s = performance.now();
      const tick = (n: number) => {
        const p = Math.min((n - s) / 1600, 1);
        setVal(Math.round((1 - Math.pow(1 - p, 3)) * to));
        if (p < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }, { threshold: 0.3 });
    if (r.current) obs.observe(r.current);
    return () => obs.disconnect();
  }, [to]);
  return <span ref={r}>{val}{suffix}</span>;
};

// ── Main ──────────────────────────────────────────────────────────────────────
const HomePage: React.FC = () => {
  const [heroIn, setHeroIn] = useState(false);
  useEffect(() => { setTimeout(() => setHeroIn(true), 80); }, []);

  const advantages = [
    { num: "01", title: "Precision Scoring", desc: "DeepPurpose DTI models predict binding affinity with BindingDB pretrained weights across all targets." },
    { num: "02", title: "Physicochemical Rules", desc: "RDKit computes Lipinski, logP, TPSA, and rotatable bonds — filtering non-viable candidates automatically." },
    { num: "03", title: "Graph Reasoning", desc: "ArangoDB knowledge graph links every molecule to known drugs, targets, and pathways for multi-hop traversal." },
  ];

  const services = [
    { title: "Candidate generation from curated SMILES libraries across 12 therapeutic classes." },
    { title: "DTI binding affinity scoring via DeepPurpose pretrained models." },
    { title: "Dual similarity search: Morgan fingerprints + ChemBERTa semantic embeddings." },
    { title: "Knowledge graph construction with SQLite and ArangoDB persistence." },
    { title: "Agentic LLM interface with tool-augmented ReAct reasoning loop." },
  ];

  const stats = [
    { val: 90, sfx: ".7%", label: "Lipinski compliance" },
    { val: 83, sfx: "", label: "Candidate molecules" },
    { val: 9, sfx: "", label: "Discovery runs" },
    { val: 3, sfx: "", label: "Oncology targets" },
  ];

  return (
    <div className="bg-white text-neutral-900">

      {/* ── HERO ── */}
      <section className="relative min-h-screen pt-16 overflow-hidden">
        {/* Subtle bg texture */}
        <div className="absolute inset-0 bg-gradient-to-br from-violet-50/60 via-white to-white pointer-events-none" />

        <div className="relative max-w-7xl mx-auto px-6 md:px-10 min-h-[calc(100vh-64px)] grid md:grid-cols-2 gap-0 items-center">
          {/* Left text */}
          <div className={`py-20 transition-all duration-1000 ${heroIn ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"}`}>
            <p className="text-xs uppercase tracking-[0.3em] text-neutral-400 mb-6 font-medium">Purpose of ELYSIUM</p>
            <h1 className="text-[clamp(3rem,7vw,5.5rem)] font-black leading-[0.95] tracking-[-0.04em] text-neutral-900 mb-8">
              Intelligent<br/>drug candidate<br/>
              <span className="text-violet-600">discovery</span>
            </h1>
            <p className="text-base text-neutral-500 leading-relaxed max-w-sm mb-10">
              ELYSIUM pairs deterministic planners with chemistry-native tools to move from hypotheses to ranked candidates while preserving transparency at every step.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link to="/discovery"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-full border border-neutral-900 text-neutral-900 text-sm font-medium hover:bg-neutral-900 hover:text-white transition-all duration-200">
                Make a Discovery
              </Link>
              <Link to="/agent"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-700 transition-all duration-200">
                Ask the Agent
              </Link>
            </div>
          </div>

          {/* Right — DNA render */}
          <div className={`relative h-[600px] transition-all duration-1000 delay-300 ${heroIn ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"}`}>
            <DNAHero />
          </div>
        </div>

        {/* Scroll cue */}
        <div className="absolute bottom-8 right-10 flex items-center gap-3 text-neutral-400">
          <span className="text-xs tracking-[0.2em] uppercase">Scroll for more</span>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="animate-bounce"><path d="M12 5v14M5 12l7 7 7-7"/></svg>
        </div>
      </section>

      {/* ── TICKER ── */}
      <div className="border-y border-neutral-100 py-5 overflow-hidden bg-white">
        <div className="flex animate-ticker whitespace-nowrap">
          {Array(2).fill(null).map((_, i) => (
            <div key={i} className="flex items-center gap-0 flex-shrink-0">
              {["DRUG DISCOVERY", "PHYSICOCHEMICAL PROFILING", "KNOWLEDGE GRAPHS", "AGENTIC AI", "DTI SCORING", "MOLECULAR EMBEDDINGS", "VIRTUAL SCREENING", "CHEMBERTA"].map(t => (
                <span key={t} className="flex items-center gap-6 px-8 text-sm font-semibold tracking-[0.15em] text-neutral-300 uppercase">
                  {t}
                  <span className="w-1.5 h-1.5 rounded-full bg-violet-300 flex-shrink-0" />
                </span>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* ── MISSION + STATS ── */}
      <section className="max-w-7xl mx-auto px-6 md:px-10 py-28 grid md:grid-cols-2 gap-16 items-center">
        <FadeUp>
          <p className="text-[clamp(2rem,4vw,3.5rem)] font-black leading-[1.05] tracking-[-0.03em] text-neutral-900">
            Our mission is to<br/>
            <span className="text-neutral-400">accelerate</span> early-stage<br/>
            drug discovery.
          </p>
        </FadeUp>
        <FadeUp delay={150}>
          <div className="grid grid-cols-2 gap-8">
            {stats.map(s => (
              <div key={s.label}>
                <p className="text-5xl font-black tracking-tight text-neutral-900 leading-none">
                  <Count to={s.val} suffix={s.sfx} />
                </p>
                <p className="text-xs text-neutral-400 uppercase tracking-[0.15em] mt-2 font-medium">{s.label}</p>
              </div>
            ))}
          </div>
        </FadeUp>
      </section>

      {/* ── ADVANTAGES (01 02 03 cards) ── */}
      <section className="border-t border-neutral-100 bg-neutral-50/50">
        <div className="max-w-7xl mx-auto px-6 md:px-10 py-24">
          <FadeUp className="flex items-end justify-between mb-16">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-neutral-400 mb-3 font-medium">Your research, our tools</p>
              <h2 className="text-[clamp(2.5rem,5vw,4rem)] font-black tracking-[-0.03em] leading-none text-neutral-900">
                Our Advantages
              </h2>
            </div>
          </FadeUp>

          <div className="grid md:grid-cols-3 gap-5">
            {advantages.map((a, i) => (
              <FadeUp key={a.num} delay={i * 100}>
                <div className="group bg-white rounded-3xl p-8 border border-neutral-100 hover:border-violet-200 hover:shadow-lg hover:shadow-violet-50 transition-all duration-300 flex flex-col h-full min-h-[280px]">
                  <div className="flex items-start justify-between mb-auto">
                    <span className="text-[10px] uppercase tracking-[0.2em] text-neutral-400 border border-neutral-200 px-2.5 py-1 rounded-full font-medium">
                      Advantages
                    </span>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
                      className="text-violet-400 group-hover:text-violet-600 transition-colors">
                      <path d="M7 17L17 7M7 7h10v10"/>
                    </svg>
                  </div>
                  <div className="mt-8">
                    <h3 className="text-xl font-bold text-neutral-900 mb-2 leading-tight">{a.title}</h3>
                    <p className="text-sm text-neutral-500 leading-relaxed">{a.desc}</p>
                  </div>
                  <div className="mt-6 flex items-end justify-between">
                    <p className="text-[5rem] font-black leading-none text-neutral-100 tracking-tight select-none">{a.num}</p>
                    <button className="flex items-center gap-2 text-xs font-medium text-neutral-500 hover:text-violet-600 transition-colors border border-neutral-200 px-3 py-1.5 rounded-full hover:border-violet-300">
                      explore
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                    </button>
                  </div>
                </div>
              </FadeUp>
            ))}
          </div>
        </div>
      </section>

      {/* ── SCIENCE BEHIND (services timeline) ── */}
      <section className="max-w-7xl mx-auto px-6 md:px-10 py-28">
        <FadeUp>
          <h2 className="text-[clamp(2.5rem,6vw,5rem)] font-black tracking-[-0.03em] leading-none text-neutral-900 mb-4">
            The Science Behind<br/>Our Pipeline
          </h2>
        </FadeUp>
        <FadeUp delay={100} className="flex items-start justify-between mt-8 mb-16">
          <p className="text-lg text-neutral-500 max-w-sm leading-relaxed">
            <span className="text-neutral-900 font-semibold">Pioneering</span> computational chemistry, we leverage cutting-edge models, from molecular transformers to agentic reasoning.
          </p>
          <Link to="/discovery" className="hidden md:inline-flex items-center gap-2 px-5 py-2.5 rounded-full border border-neutral-300 text-sm font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900 transition-colors">
            Start a Run
          </Link>
        </FadeUp>

        {/* Timeline */}
        <div className="relative">
          <div className="flex gap-3 overflow-x-auto pb-4 scrollbar-hide">
            {services.map((s, i) => (
              <FadeUp key={i} delay={i * 80}
                className="flex-shrink-0 w-[200px] md:flex-1">
                <div className="flex flex-col gap-4">
                  <div className="flex items-center gap-2">
                    <div className={`w-3 h-3 rounded-full border-2 flex-shrink-0 ${i === 0 ? "bg-violet-600 border-violet-600" : "bg-white border-neutral-300"}`} />
                    {i < services.length - 1 && <div className="h-[1px] flex-1 bg-neutral-200" />}
                  </div>
                  <p className="text-xs text-neutral-500 leading-relaxed">{s.title}</p>
                </div>
              </FadeUp>
            ))}
          </div>
        </div>
      </section>

      {/* ── TEAM / CTA section ── */}
      <section className="border-t border-neutral-100">
        <div className="max-w-7xl mx-auto px-6 md:px-10 py-28 grid md:grid-cols-2 gap-12 items-center">
          <FadeUp>
            <div className="bg-neutral-50 rounded-3xl overflow-hidden aspect-[4/3] flex items-center justify-center relative border border-neutral-100">
              {/* Orbital diagram like MYDNA precision diagnostics */}
              <svg viewBox="0 0 400 320" className="w-full h-full p-8">
                <circle cx="200" cy="160" r="120" fill="none" stroke="#e5e7eb" strokeWidth="1"/>
                <circle cx="200" cy="160" r="80" fill="none" stroke="#e5e7eb" strokeWidth="1"/>
                <circle cx="200" cy="160" r="40" fill="none" stroke="#ddd6fe" strokeWidth="1.5"/>
                {[
                  { angle: -30, label: "EGFR", r: 120 },
                  { angle: 60, label: "BRAF", r: 120 },
                  { angle: 160, label: "KRAS", r: 120 },
                  { angle: 20, label: "DTI Scoring", r: 80 },
                  { angle: 120, label: "PHYSCHEM", r: 80 },
                  { angle: 220, label: "KG Edges", r: 80 },
                ].map(({ angle, label, r }) => {
                  const rad = (angle * Math.PI) / 180;
                  const x = 200 + r * Math.cos(rad);
                  const y = 160 + r * Math.sin(rad);
                  return (
                    <g key={label}>
                      <circle cx={x} cy={y} r="5" fill={r === 120 ? "#7c3aed" : "#a78bfa"} opacity="0.8"/>
                      <text x={x + (x > 200 ? 8 : -8)} y={y + 4}
                        textAnchor={x > 200 ? "start" : "end"}
                        fontSize="9" fill="#6b7280" fontFamily="Inter, sans-serif">{label}</text>
                    </g>
                  );
                })}
                <circle cx="200" cy="160" r="8" fill="#7c3aed" opacity="0.9"/>
                <text x="200" y="185" textAnchor="middle" fontSize="9" fill="#9ca3af" fontFamily="Inter, sans-serif">ELYSIUM Core</text>
              </svg>
              <div className="absolute top-4 right-4 text-[10px] text-neutral-400 uppercase tracking-wider font-medium">ELYSIUM Pipeline</div>
            </div>
          </FadeUp>

          <FadeUp delay={150}>
            <p className="text-xs uppercase tracking-[0.3em] text-neutral-400 mb-4 font-medium">Built for researchers</p>
            <h2 className="text-4xl font-black tracking-[-0.03em] leading-tight text-neutral-900 mb-6">
              Driven by rigorous<br/>science and relentless<br/>pursuit of clarity.
            </h2>
            <p className="text-neutral-500 text-sm leading-relaxed mb-8 max-w-sm">
              ELYSIUM blends deterministic planners with chemistry models so every discovery run is fully traceable. FastAPI coordinates generation, scoring, and graph persistence.
            </p>
            <Link to="/about" className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-700 transition-colors">
              Learn more
            </Link>
          </FadeUp>
        </div>
      </section>

      {/* ── DISCLAIMERS + FOOTER ── */}
      <section className="border-t border-neutral-100 bg-neutral-50">
        <div className="max-w-7xl mx-auto px-6 md:px-10 py-16">
          <FadeUp className="grid md:grid-cols-3 gap-8 mb-16">
            {[
              "ELYSIUM is a research prototype; no clinical or therapeutic claims are made.",
              "Generated scores are model-dependent and require medicinal chemistry review before experimental action.",
              "Knowledge graph data may be incomplete and serves exploratory analysis only.",
            ].map((d, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="w-1.5 h-1.5 rounded-full bg-amber-400 mt-1.5 flex-shrink-0" />
                <p className="text-xs text-neutral-400 leading-relaxed">{d}</p>
              </div>
            ))}
          </FadeUp>
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pt-8 border-t border-neutral-200">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-md bg-violet-600 flex items-center justify-center">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2l3.5 7 7.5 1-5.5 5 1.5 7.5L12 19l-7 3.5L6.5 15 1 10l7.5-1z"/></svg>
              </div>
              <span className="font-bold text-sm text-neutral-900 tracking-tight">ELYSIUM</span>
            </div>
            <p className="text-xs text-neutral-400">© {new Date().getFullYear()} ELYSIUM Labs · Research use only · Built with FastAPI · RDKit · DeepPurpose · React</p>
          </div>
        </div>
      </section>

    </div>
  );
};

export default HomePage;