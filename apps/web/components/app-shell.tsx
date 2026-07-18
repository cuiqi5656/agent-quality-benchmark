"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, BarChart3, Beaker, BookOpenCheck, Boxes, FileText, GitCompareArrows, Menu, Plus, Settings2 } from "lucide-react";
import { useState } from "react";

const navigation = [
  { href: "/", label: "Overview", icon: BarChart3 },
  { href: "/runs/new", label: "New benchmark", icon: Plus },
  { href: "/runs/demo-atlas-20260718", label: "Run explorer", icon: Activity },
  { href: "/compare", label: "Compare", icon: GitCompareArrows },
  { href: "/benchmarks", label: "Benchmark packs", icon: Boxes },
  { href: "/calibration", label: "Judge calibration", icon: Beaker },
  { href: "/reports", label: "Reports", icon: FileText },
];

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const pageName = navigation.find((item) => isActive(pathname, item.href))?.label ?? "Workspace";
  return (
    <div className="app-shell">
      <nav className={`sidebar ${menuOpen ? "mobile-open" : ""}`} aria-label="Primary navigation">
        <Link className="brand" href="/" aria-label="Agent Quality Benchmark home">
          <span className="brand-mark">AQ</span>
          <span><span className="brand-title">Agent Quality</span><span className="brand-kicker">Benchmark</span></span>
        </Link>
        <div className="nav-group">
          <div className="nav-label">Evaluate</div>
          {navigation.slice(0, 4).map(({ href, label, icon: Icon }) => (
            <Link onClick={() => setMenuOpen(false)} className={`nav-item ${isActive(pathname, href) ? "active" : ""}`} href={href} key={href} aria-current={isActive(pathname, href) ? "page" : undefined}>
              <Icon aria-hidden="true" />{label}
            </Link>
          ))}
        </div>
        <div className="nav-group">
          <div className="nav-label">Design & review</div>
          {navigation.slice(4).map(({ href, label, icon: Icon }) => (
            <Link onClick={() => setMenuOpen(false)} className={`nav-item ${isActive(pathname, href) ? "active" : ""}`} href={href} key={href} aria-current={isActive(pathname, href) ? "page" : undefined}>
              <Icon aria-hidden="true" />{label}
            </Link>
          ))}
        </div>
        <div className="sidebar-foot">
          <div className="system-status"><span className="status-dot" /> Deterministic core ready</div>
        </div>
      </nav>
      {menuOpen && <button className="nav-scrim" aria-label="Close navigation" onClick={() => setMenuOpen(false)} />}
      <main className="shell-main">
        <header className="topbar">
          <div className="top-actions"><button className="icon-button mobile-menu" aria-label="Open navigation" aria-expanded={menuOpen} onClick={() => setMenuOpen(true)}><Menu /></button><div className="breadcrumb">Workspace / <strong>{pageName}</strong></div></div>
          <div className="top-actions">
            <Link className="secondary-button" href="/methodology"><BookOpenCheck /> Methodology</Link>
            <Link className="icon-button" href="/settings" aria-label="Settings"><Settings2 /></Link>
            <Link className="primary-button" href="/runs/new"><Plus /> New run</Link>
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}
