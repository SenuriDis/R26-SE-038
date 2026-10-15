import { NavLink } from "react-router-dom";
import { LayoutDashboard, FileSearch, Clock3, Sparkles } from "lucide-react";

function Navbar() {
  const linkClass = ({ isActive }) =>
    `flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition ${
      isActive
        ? "bg-cyan-100 text-cyan-700"
        : "text-slate-600 hover:bg-slate-100"
    }`;

  return (
    <nav className="bg-white border-b border-slate-200 px-8 py-4 flex justify-between items-center sticky top-0 z-50">
      <div className="flex items-center gap-3">
        <div className="bg-cyan-500 w-11 h-11 rounded-2xl flex items-center justify-center text-white shadow-sm">
          <Sparkles size={22} />
        </div>

        <div>
          <h1 className="text-xl font-bold text-slate-800">AI CodeLens</h1>
          <p className="text-sm text-slate-500">
            Intelligent Software Testing System
          </p>
        </div>
      </div>

      <div className="flex gap-2">
        <NavLink to="/" className={linkClass}>
          <LayoutDashboard size={17} />
          Dashboard
        </NavLink>

        <NavLink to="/analysis" className={linkClass}>
          <FileSearch size={17} />
          New Analysis
        </NavLink>

        <NavLink to="/history" className={linkClass}>
          <Clock3 size={17} />
          Recent Results
        </NavLink>
      </div>
    </nav>
  );
}

export default Navbar;