import { motion, AnimatePresence, useScroll, useTransform } from "motion/react";
import { Search, Volume2, Menu as MenuIcon, ArrowDown, Plus, X } from "lucide-react";
import { useRef, useState } from "react";
import { Link } from "react-router-dom";

const MenuOverlay = ({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) => {
  const menuItems = [
    { name: "Discovery", count: "01" },
    { name: "Runs", count: "02" },
    { name: "Graphs", count: "03" },
    { name: "Agent", count: "04" },
    { name: "Analysis", count: "05" },
  ];

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-[100] bg-black/20 backdrop-blur-sm"
          />
          {/* Centered wrapper — avoids translate clipping */}
          <div className="fixed inset-0 z-[101] flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.92, y: 16 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.92, y: 16 }}
              transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
              className="w-full max-w-2xl bg-white rounded-[40px] shadow-2xl flex flex-col overflow-hidden"
              style={{ maxHeight: "min(85vh, 680px)" }}
            >
              <nav className="flex items-center justify-between px-8 py-6 border-b border-black/5 flex-shrink-0">
                <div className="text-lg font-bold tracking-tighter">ELYSIUM</div>
                <button
                  onClick={onClose}
                  className="w-10 h-10 rounded-full border border-black/10 flex items-center justify-center hover:bg-black hover:text-white transition-all cursor-pointer group"
                >
                  <X size={18} className="group-hover:rotate-90 transition-transform duration-500" />
                </button>
              </nav>

              <div className="flex-1 overflow-y-auto px-8 py-10 md:px-16">
                <div className="space-y-1">
                  {menuItems.map((item, i) => (
                    <motion.div
                      key={item.name}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.55, delay: 0.08 + i * 0.05, ease: [0.22, 1, 0.36, 1] }}
                      className="group relative flex items-baseline gap-6 py-3 border-b border-black/5 hover:border-black/20 transition-colors"
                    >
                      <span className="text-[10px] font-bold tracking-widest opacity-20 group-hover:opacity-100 transition-opacity">
                        {item.count}
                      </span>
                      <Link
                        to="/dashboard"
                        className="text-4xl md:text-5xl font-display font-medium tracking-tighter hover:translate-x-3 transition-transform duration-500 block"
                        onClick={onClose}
                      >
                        {item.name}
                      </Link>
                      <div className="ml-auto opacity-0 group-hover:opacity-100 transition-opacity">
                        <ArrowDown size={22} className="-rotate-135 text-purple-500" />
                      </div>
                    </motion.div>
                  ))}
                </div>

                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 1, delay: 0.4 }}
                  className="mt-10 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4"
                >
                  <div className="space-y-1">
                    <p className="text-[9px] font-bold tracking-widest uppercase opacity-40">Get in touch</p>
                    <p className="text-xs font-medium">hello@elysium.science</p>
                  </div>
                  <div className="flex gap-6">
                    {["Instagram", "Twitter"].map((social) => (
                      <a key={social} href="#" className="text-[9px] font-bold tracking-widest uppercase opacity-40 hover:opacity-100 transition-opacity">
                        {social}
                      </a>
                    ))}
                  </div>
                </motion.div>
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
};

const Marquee = () => {
  const items = [
    "DRUG DISCOVERY",
    "MOLECULAR AI",
    "TARGET BINDING",
    "PHYSICOCHEMICAL PROFILING",
    "KNOWLEDGE GRAPHS",
    "ELYSIUM",
  ];

  return (
    <div className="py-8 md:py-12 border-y border-black/5 overflow-hidden bg-white relative z-10">
      <motion.div
        animate={{ x: [0, -800] }}
        transition={{ duration: 35, repeat: Infinity, ease: "linear" }}
        className="flex whitespace-nowrap gap-12 items-center"
      >
        {[...Array(5)].map((_, i) => (
          <div key={i} className="flex gap-12 items-center">
            {items.map((item, index) => (
              <div key={index} className="flex items-center gap-10">
                <span className="text-2xl md:text-4xl font-display font-medium tracking-tight text-[#111111]">
                  {item}
                </span>
                <div className="flex items-center gap-5">
                  <div className="w-6 h-6 md:w-8 md:h-8 rounded-full border border-black/10 flex items-center justify-center">
                    <Plus size={12} strokeWidth={1} className="text-black/40" />
                  </div>
                  <span className="text-xl md:text-2xl font-light opacity-10">/</span>
                </div>
              </div>
            ))}
          </div>
        ))}
      </motion.div>
    </div>
  );
};


const FeaturesSection = () => {
  const features = [
    {
      title: "Agentic Pipeline",
      description: "ELYSIUM orchestrates a multi-step agent pipeline: generate scaffolds, score with DeepPurpose, filter by physicochemical properties, and surface the best candidates automatically.",
    },
    {
      title: "Knowledge Graph",
      description: "Every run persists molecule–target–drug edges into ArangoDB, enabling cross-run similarity traversal and drug repositioning analysis.",
    },
    {
      title: "LLM-Powered Reasoning",
      description: "The ELYSIUM agent uses OpenRouter LLMs with tool-augmented access to your live molecular database for evidence-grounded answers.",
    },
  ];

  return (
    <section className="py-14 md:py-20 px-8 md:px-12 bg-white relative z-10">
      <div className="max-w-7xl mx-auto grid lg:grid-cols-2 gap-12 lg:gap-24 items-start">

        {/* Left Column - Large Abstract Visual */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1] }}
          viewport={{ once: true }}
          className="relative aspect-[3/4] w-full rounded-[60px] overflow-hidden group"
        >
          <img
            src="/images/feature-bg.jpg"
            className="w-full h-full object-cover"
            alt="Feature"
          />

          <div className="absolute inset-0 bg-black/10" />
        </motion.div>

        {/* Right Column */}
        <div className="space-y-20">
          <div className="grid md:grid-cols-2 gap-12 items-start">
            <div className="space-y-8">
              <p className="text-sm leading-relaxed opacity-60 font-medium">
                Driven by a rich history of expertise and a relentless pursuit of scientific excellence
              </p>
              <button className="px-8 py-4 bg-black text-white rounded-full text-[10px] font-bold tracking-widest uppercase hover:bg-black/80 transition-all cursor-pointer">
                Learn More
              </button>
            </div>

            <motion.div
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 1, delay: 0.2 }}
              viewport={{ once: true }}
              className="relative aspect-square rounded-[48px] overflow-hidden bg-gray-100"
            >
              <img
                src="/images/molecule.jpg"
                alt="Molecular Interaction"
                className="w-full h-full object-cover"
              />
              <div className="absolute inset-0 bg-black/5" />
              <div className="absolute bottom-6 left-6 right-6">
                <div className="bg-white/60 backdrop-blur-xl rounded-3xl p-6 space-y-4">
                  <h3 className="text-lg font-display font-medium leading-tight">
                    Good interaction <br /> with other molecules
                  </h3>
                  <button className="px-4 py-2 bg-purple-500/20 text-purple-600 rounded-full text-[9px] font-bold tracking-widest uppercase hover:bg-purple-500/30 transition-all cursor-pointer">
                    Learn more
                  </button>
                </div>
              </div>
            </motion.div>
          </div>

          <div className="space-y-12">
            {features.map((feature, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: 20 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.8, delay: i * 0.1 }}
                viewport={{ once: true }}
                className="grid md:grid-cols-[1fr_1.5fr] gap-8 items-start border-t border-black/5 pt-12 first:border-0 first:pt-0"
              >
                <div className="flex items-center gap-6 group">
                  <div className="w-10 h-10 rounded-full border border-black/10 flex items-center justify-center group-hover:bg-black group-hover:text-white transition-all duration-500">
                    <Plus size={18} strokeWidth={1.5} />
                  </div>
                  <h4 className="text-xl font-display font-medium tracking-tight">
                    {feature.title}
                  </h4>
                </div>
                <p className="text-xs md:text-sm leading-relaxed opacity-60 max-w-md">
                  {feature.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

const ScienceSection = () => {
  const [activeStep, setActiveStep] = useState(0);

  const timelineItems = [
    { label: "Target", text: "Target protein is identified and passed to the molecule generation pipeline." },
    { label: "Generation", text: "RDKit generates diverse candidate scaffolds with structural variation." },
    { label: "Scoring", text: "DeepPurpose predicts binding affinity (DTI score) for each candidate." },
    { label: "Physicochemical", text: "RDKit physicochemical filters check Lipinski rule-of-five, logP and TPSA. No toxicity or Physicochemical prediction is made." },
    { label: "Similarity", text: "Fingerprint and ChemBERTa similarity links each molecule to known drugs." },
    { label: "Output", text: "Top candidates are ranked, stored, and surfaced in the ELYSIUM dashboard." },
  ];

  const goTo = (i: number) => setActiveStep(Math.max(0, Math.min(timelineItems.length - 1, i)));

  return (
    <section className="py-14 md:py-20 px-8 md:px-12 bg-white relative z-10">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-start gap-12 mb-16">
          <div className="max-w-xl">
            <motion.h2
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
              viewport={{ once: true }}
              className="text-5xl md:text-7xl font-display font-medium leading-[1.1] tracking-tight mb-10"
            >
              The Pipeline <br /> Behind ELYSIUM
            </motion.h2>
            {/* Arrow navigation */}
            <div className="flex gap-3">
              <button
                onClick={() => goTo(activeStep - 1)}
                disabled={activeStep === 0}
                className="w-12 h-12 rounded-full border border-black/10 flex items-center justify-center hover:bg-black hover:text-white transition-all cursor-pointer disabled:opacity-20 disabled:cursor-not-allowed"
              >
                <ArrowDown size={18} className="rotate-90" />
              </button>
              <button
                onClick={() => goTo(activeStep + 1)}
                disabled={activeStep === timelineItems.length - 1}
                className="w-12 h-12 rounded-full border border-black/10 flex items-center justify-center hover:bg-black hover:text-white transition-all cursor-pointer disabled:opacity-20 disabled:cursor-not-allowed"
              >
                <ArrowDown size={18} className="-rotate-90" />
              </button>
            </div>
          </div>

          <div className="flex flex-col items-end gap-8 md:pt-8 max-w-lg">
            <div className="flex gap-3">
              <button className="w-10 h-10 rounded-full border border-black/10 flex items-center justify-center opacity-40 hover:opacity-100 transition-opacity cursor-pointer">
                <Plus size={16} strokeWidth={1} className="rotate-45" />
              </button>
              <button className="w-10 h-10 rounded-full border border-black/10 flex items-center justify-center opacity-40 hover:opacity-100 transition-opacity cursor-pointer">
                <Volume2 size={16} strokeWidth={1} />
              </button>
            </div>
            <button className="px-8 py-4 border border-black/20 rounded-full text-[10px] font-bold tracking-widest uppercase hover:bg-black hover:text-white transition-all cursor-pointer">
              Run Discovery
            </button>
            <motion.p
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              transition={{ duration: 1, delay: 0.2 }}
              viewport={{ once: true }}
              className="text-xl md:text-3xl font-display font-medium leading-tight text-right"
            >
              From target protein <span className="opacity-20">to ranked candidates,</span> every step is automated, auditable, and powered by <span className="opacity-20">open-source cheminformatics and LLM reasoning.</span>
            </motion.p>
          </div>
        </div>

        {/* Active step description */}
        <AnimatePresence mode="wait">
          <motion.div
            key={activeStep}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.3 }}
            className="mb-10 flex items-start gap-5"
          >
            <span className="text-[10px] font-bold tracking-widest uppercase opacity-30 mt-1 flex-shrink-0">
              0{activeStep + 1}
            </span>
            <div>
              <p className="text-xs font-bold tracking-widest uppercase text-purple-600 mb-1">
                {timelineItems[activeStep].label}
              </p>
              <p className="text-base md:text-lg leading-relaxed opacity-70 max-w-2xl">
                {timelineItems[activeStep].text}
              </p>
            </div>
          </motion.div>
        </AnimatePresence>

        {/* Timeline nodes */}
        <div className="relative pt-6">
          <div className="absolute top-8 left-0 right-0 h-[1px] bg-black/5" />
          <div className="grid grid-cols-3 md:grid-cols-6 gap-4 relative">
            {timelineItems.map((item, i) => (
              <button
                key={i}
                onClick={() => setActiveStep(i)}
                className="text-left space-y-5 group focus:outline-none"
              >
                <div className="relative flex justify-start">
                  <motion.div
                    animate={{ scale: activeStep === i ? 1.25 : 1 }}
                    transition={{ duration: 0.25 }}
                    className={`w-4 h-4 rounded-full z-10 transition-all duration-300 ${
                      activeStep === i
                        ? "bg-purple-500 shadow-[0_0_14px_rgba(168,85,247,0.55)] ring-8 ring-purple-500/10"
                        : i < activeStep
                        ? "bg-black/25"
                        : "bg-black/10 group-hover:bg-black/25"
                    }`}
                  />
                </div>
                <p className={`text-[10px] font-bold tracking-widest uppercase transition-all duration-200 ${
                  activeStep === i
                    ? "text-purple-600 opacity-100"
                    : "opacity-30 group-hover:opacity-60"
                }`}>
                  {item.label}
                </p>
              </button>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

const AdvantagesSection = () => {
  const advantages = [
    { id: "01", title: "Agentic Molecule Discovery" },
    { id: "02", title: "Property-Filtered Candidates" },
    { id: "03", title: "LLM-Augmented Analysis" },
  ];

  return (
    <section className="py-14 md:py-20 px-8 md:px-12 bg-white relative z-10">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-start mb-20">
          <div className="space-y-2">
            <span className="text-sm font-medium opacity-60">Built for drug discovery research</span>
          </div>
          <h2 className="text-5xl md:text-7xl font-display font-medium tracking-tight">
            Our Advantages
          </h2>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {advantages.map((adv, i) => (
            <motion.div
              key={adv.id}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: i * 0.1 }}
              viewport={{ once: true }}
              className="bg-[#F8F8F8] rounded-[48px] p-10 md:p-12 flex flex-col justify-between min-h-[480px] group hover:bg-[#F0F0F0] transition-colors duration-500"
            >
              <div className="flex justify-between items-start">
                <span className="px-5 py-2 border border-black/10 rounded-full text-[10px] font-bold tracking-widest uppercase">
                  Advantages
                </span>
                <div className="text-purple-400 group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform duration-500">
                  <ArrowDown size={40} strokeWidth={1} className="-rotate-135" />
                </div>
              </div>

              <div className="space-y-12">
                <h3 className="text-3xl md:text-4xl font-display font-medium leading-tight tracking-tight max-w-[200px]">
                  {adv.title}
                </h3>
                <div className="flex items-end justify-between">
                  <span className="text-8xl md:text-9xl font-display font-medium tracking-tighter leading-none">
                    {adv.id}
                  </span>
                  <div className="flex items-center gap-2 bg-white border border-black/5 rounded-full p-1 pr-4 group/btn cursor-pointer hover:border-black/20 transition-all">
                    <div className="w-8 h-8 rounded-full bg-black/5 flex items-center justify-center">
                      <Plus size={14} className="opacity-40" />
                    </div>
                    <span className="text-[10px] font-bold tracking-widest uppercase">explore</span>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default function LandingPage() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <div className="relative w-full bg-white text-[#111111] font-sans selection:bg-black selection:text-white">
      <MenuOverlay isOpen={isMenuOpen} onClose={() => setIsMenuOpen(false)} />

      <section className="relative h-screen w-full overflow-hidden bg-white flex flex-col">

        <nav className="relative z-20 flex items-center justify-between px-8 py-8 md:px-12 flex-shrink-0">
          <div className="flex items-center gap-12">
            <motion.div
              initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8 }}
              className="text-xl font-bold tracking-tighter"
            >
              ELYSIUM
            </motion.div>
            <motion.button
              initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, delay: 0.1 }}
              onClick={() => setIsMenuOpen(true)}
              className="flex items-center gap-3 group cursor-pointer"
            >
              <div className="flex flex-col gap-1">
                <div className="h-[1px] w-8 bg-black transition-all group-hover:w-10" />
                <div className="h-[1px] w-5 bg-black transition-all group-hover:w-8" />
              </div>
              <span className="text-xs font-medium tracking-widest uppercase opacity-60 group-hover:opacity-100 transition-opacity">
                Menu
              </span>
            </motion.button>
          </div>
          <motion.div
            initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8 }}
            className="flex items-center gap-6"
          >
            <button className="p-2 hover:bg-black/5 rounded-full transition-colors cursor-pointer">
              <Search size={20} strokeWidth={1.5} />
            </button>
            <button className="p-2 border border-black/20 rounded-full hover:bg-black/5 transition-all cursor-pointer">
              <Volume2 size={20} strokeWidth={1.5} />
            </button>
          </motion.div>
        </nav>

        <div className="relative flex flex-1 min-h-0 z-10">

          <div className="flex flex-col justify-center px-8 md:px-16 lg:px-20 w-full lg:w-1/2">
            <div className="max-w-xl">
              <motion.p
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.3 }}
                className="text-[10px] font-bold tracking-[0.25em] uppercase mb-8 opacity-50"
              >
                Purpose of ELYSIUM
              </motion.p>
              <motion.h1
                initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 1, delay: 0.4, ease: [0.22, 1, 0.36, 1] }}
                className="text-5xl md:text-6xl lg:text-7xl font-display font-medium leading-[1.05] tracking-tight mb-8"
              >
                AI-powered<br />drug discovery
              </motion.h1>
              <motion.p
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.5 }}
                className="text-sm leading-relaxed opacity-60 max-w-xs mb-12"
              >
                Generate, score and analyse candidate molecules against any target protein. Powered by agentic AI and knowledge graphs.
              </motion.p>
              <motion.div
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.6 }}
                className="flex items-center gap-4 flex-wrap"
              >
                <Link
                  to="/dashboard"
                  className="px-8 py-4 bg-black text-white rounded-full text-[10px] font-bold tracking-widest uppercase hover:bg-black/80 transition-all duration-500"
                >
                  Start Discovery
                </Link>
                <button className="px-8 py-4 border border-black/20 rounded-full text-[10px] font-bold tracking-widest uppercase hover:bg-black hover:text-white transition-all duration-500 cursor-pointer">
                  Learn More
                </button>
              </motion.div>
            </div>
          </div>

          <div className="hidden lg:block absolute right-0 top-0 w-1/2 h-full overflow-hidden">
            <motion.div
              initial={{ opacity: 0, scale: 1.05 }} animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 1.5, ease: [0.22, 1, 0.36, 1] }}
              className="w-full h-full"
            >
              <video
                autoPlay
                loop
                muted
                playsInline
                className="w-full h-full object-cover"
              >
                <source src="/videos/hero.mp4" type="video/mp4" />
              </video>

              {/* overlay for readability */}
              <div className="absolute inset-0 bg-gradient-to-r from-white via-white/40 to-transparent" />
            </motion.div>
          </div>

        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.8 }}
          className="flex-shrink-0 px-4 pb-4 md:px-8 md:pb-6 z-10"
        >
          <div className="relative overflow-hidden rounded-[32px] border border-white/50 bg-white/35 backdrop-blur-2xl shadow-[0_24px_70px_rgba(17,17,17,0.12)] px-5 py-5 md:px-8 md:py-6">
            <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-white/60 via-white/20 to-transparent" />
            <div className="relative flex items-start gap-5 md:gap-8">
              <div className="flex-shrink-0 min-w-[88px] md:min-w-[118px]">
                <span className="block text-[56px] md:text-[72px] font-display font-medium tracking-tighter leading-none">01</span>
                <span className="mt-2 block text-[10px] font-bold tracking-[0.18em] opacity-45">2024-01-01</span>
              </div>
              <div className="flex-1 grid md:grid-cols-[1fr_1.4fr] gap-2 md:gap-8 md:pt-1">
                <h2 className="text-[22px] md:text-[36px] font-display font-medium leading-[1.1] tracking-tight max-w-xl">
                  Agentic AI Drug Discovery Platform
                </h2>
                <p className="text-[13px] md:text-[15px] leading-relaxed opacity-70 max-w-3xl md:pt-1">
                  ELYSIUM generates candidate molecules, scores binding affinity, filters by physicochemical properties, and surfaces the most drug-like candidates powered by a multi-agent pipeline.
                </p>
              </div>
            </div>
          </div>
        </motion.div>

      </section>

      <Marquee />
      <FeaturesSection />
      <ScienceSection />
      <AdvantagesSection />

      <footer className="py-20 px-8 md:px-12 border-t border-black/5 text-center">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-8">
          <div className="text-xl font-bold tracking-tighter">ELYSIUM</div>
          <div className="flex gap-8 text-[10px] font-bold tracking-widest uppercase opacity-40">
            <a href="#" className="hover:opacity-100 transition-opacity">Privacy Policy</a>
            <a href="#" className="hover:opacity-100 transition-opacity">Terms of Service</a>
            <a href="#" className="hover:opacity-100 transition-opacity">Contact Us</a>
          </div>
          <div className="text-[10px] font-bold tracking-widest uppercase opacity-40">
            © 2026 ELYSIUM. All Rights Reserved.
          </div>
        </div>
      </footer>

      <div className="fixed top-0 right-0 w-1/2 h-full pointer-events-none z-0">
        <div className="absolute top-1/4 right-1/4 w-96 h-96 bg-purple-200/10 blur-[120px] rounded-full" />
        <div className="absolute bottom-1/4 right-1/3 w-64 h-64 bg-blue-200/10 blur-[100px] rounded-full" />
      </div>
    </div>
  );
}