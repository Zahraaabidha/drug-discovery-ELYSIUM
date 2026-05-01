import React, { useState, useEffect } from "react";
import { NavLink, useLocation, Link } from "react-router-dom";

const navLinks = [
  { label: "Discovery", to: "/discovery" },
  { label: "Runs", to: "/runs" },
  { label: "Graphs", to: "/graphs" },
  { label: "Agent", to: "/agent" },
  { label: "Analysis", to: "/analysis" },
];

interface Props { children: React.ReactNode; }

const AppLayout: React.FC<Props> = ({ children }) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const location = useLocation();
  const isHome = location.pathname === "/";

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => { setMenuOpen(false); }, [location.pathname]);

  return (
    <div className="min-h-screen bg-white text-neutral-900">
      {/* ── NAV ── */}
      <header className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled || !isHome ? "bg-white/95 backdrop-blur-md border-b border-neutral-100" : "bg-transparent"
      }`}>
        <div className="max-w-7xl mx-auto px-6 md:px-10 h-16 flex items-center justify-between">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-7 h-7 rounded-lg bg-violet-600 flex items-center justify-center">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2l3.5 7 7.5 1-5.5 5 1.5 7.5L12 19l-7 3.5L6.5 15 1 10l7.5-1z"/>
              </svg>
            </div>
            <span className="font-bold text-base tracking-tight text-neutral-900">ELYSIUM</span>
          </Link>

          {/* Desktop links */}
          <nav className="hidden md:flex items-center gap-8">
            {navLinks.map(l => (
              <NavLink key={l.to} to={l.to}
                className={({ isActive }) =>
                  `text-sm font-medium transition-colors ${isActive ? "text-violet-600" : "text-neutral-500 hover:text-neutral-900"}`
                }>
                {l.label}
              </NavLink>
            ))}
          </nav>

          {/* Right side */}
          <div className="flex items-center gap-4">
            <Link to="/discovery"
              className="hidden md:inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-700 transition-colors">
              Start Discovery
            </Link>
            {/* Hamburger */}
            <button onClick={() => setMenuOpen(!menuOpen)}
              className="flex flex-col gap-[5px] p-1 group md:hidden">
              <span className={`block w-5 h-[1.5px] bg-neutral-900 transition-all duration-200 ${menuOpen ? "rotate-45 translate-y-[6.5px]" : ""}`}/>
              <span className={`block w-5 h-[1.5px] bg-neutral-900 transition-all duration-200 ${menuOpen ? "opacity-0" : ""}`}/>
              <span className={`block w-5 h-[1.5px] bg-neutral-900 transition-all duration-200 ${menuOpen ? "-rotate-45 -translate-y-[6.5px]" : ""}`}/>
            </button>
            {/* Desktop hamburger for "Menu" label like MYDNA */}
            <button onClick={() => setMenuOpen(!menuOpen)}
              className="hidden md:flex items-center gap-2 text-sm text-neutral-500 hover:text-neutral-900 transition-colors">
              <div className="flex flex-col gap-[4px]">
                <span className={`block w-4 h-[1.5px] bg-current transition-all duration-200 ${menuOpen ? "rotate-45 translate-y-[5.5px]" : ""}`}/>
                <span className={`block w-4 h-[1.5px] bg-current transition-all duration-200 ${menuOpen ? "opacity-0" : ""}`}/>
                <span className={`block w-4 h-[1.5px] bg-current transition-all duration-200 ${menuOpen ? "-rotate-45 -translate-y-[5.5px]" : ""}`}/>
              </div>
              Menu
            </button>
          </div>
        </div>

        {/* Full-screen menu overlay */}
        {menuOpen && (
          <div className="fixed inset-0 top-16 bg-white z-40 flex flex-col">
            <nav className="flex-1 flex flex-col justify-center max-w-7xl mx-auto px-10 w-full gap-2">
              {[{ label: "Home", to: "/" }, ...navLinks].map((l, i) => (
                <NavLink key={l.to} to={l.to}
                  className={({ isActive }) =>
                    `text-5xl md:text-7xl font-bold tracking-tight py-3 border-b border-neutral-100 transition-colors ${
                      isActive ? "text-violet-600" : "text-neutral-900 hover:text-violet-600"
                    }`
                  }
                  style={{ animationDelay: `${i * 60}ms` }}>
                  {l.label}
                </NavLink>
              ))}
            </nav>
            <div className="max-w-7xl mx-auto px-10 w-full pb-10">
              <p className="text-sm text-neutral-400">ELYSIUM Labs · Research use only · © {new Date().getFullYear()}</p>
            </div>
          </div>
        )}
      </header>

      <main>{children}</main>

      {/* Footer */}
      {!isHome && (
        <footer className="border-t border-neutral-100 mt-20">
          <div className="max-w-7xl mx-auto px-10 py-8 flex items-center justify-between text-sm text-neutral-400">
            <p>© {new Date().getFullYear()} ELYSIUM Labs · Research use only</p>
            <p>Built with FastAPI · RDKit · DeepPurpose · React</p>
          </div>
        </footer>
      )}
    </div>
  );
};

export default AppLayout;