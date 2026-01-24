import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import Header from '../components/Header';
import { ShieldCheck, History, Info, AlertTriangle, Settings } from 'lucide-react';
import clsx from 'clsx';

const NavItem = ({ to, icon: Icon, label, active }) => (
    <Link
        to={to}
        className={clsx(
            "flex flex-col items-center gap-1 p-2 rounded-lg transition-colors min-w-[64px]",
            active ? "text-blue-400 bg-blue-500/10" : "text-slate-500 hover:text-slate-300 hover:bg-slate-800/50"
        )}
    >
        <Icon className="w-5 h-5" />
        <span className="text-[10px] font-medium uppercase tracking-wider">{label}</span>
    </Link>
);

const Layout = () => {
    const location = useLocation();

    return (
        <div className="min-h-screen bg-background text-slate-200 font-sans selection:bg-blue-500/30 flex flex-col">
            <Header />

            {/* Main content */}
            <main className="flex-grow relative">
                <Outlet />
            </main>

            {/* Persistent Footer Navigation */}
            <footer className="border-t border-white/5 bg-slate-900/50 backdrop-blur-md sticky bottom-0 z-50">
                <div className="max-w-5xl mx-auto px-4 py-4 flex justify-center gap-8">
                    <NavItem to="/" icon={ShieldCheck} label="Home" active={location.pathname === '/'} />
                    <NavItem to="/agents" icon={Info} label="Agents" active={location.pathname === '/agents'} />
                    <NavItem to="/conflicts" icon={AlertTriangle} label="Conflicts" active={location.pathname === '/conflicts'} />
                    <NavItem to="/settings" icon={Settings} label="Settings" active={location.pathname === '/settings'} />
                </div>
            </footer>
        </div>
    );
};

export default Layout;
