import { NavLink } from "react-router-dom";

function Navbar() {
  const linkClass = ({ isActive }) =>
    `px-4 py-2 rounded-lg text-sm font-medium ${
      isActive
        ? "bg-cyan-100 text-cyan-700"
        : "text-slate-600 hover:bg-slate-100"
    }`;

  return (
    <nav className="bg-white border-b border-slate-200 px-8 py-4 flex justify-between items-center">
      <div className="flex items-center gap-3">
        <div className="bg-cyan-500 w-10 h-10 rounded-full flex items-center justify-center text-white font-bold">
          AI
        </div>

        <div>
          <h1 className="text-xl font-bold text-slate-800">
            AI CodeLens
          </h1>
          <p className="text-sm text-slate-500">
            Intelligent Software Testing System
          </p>
        </div>
      </div>

      <div className="flex gap-2">
        <NavLink to="/" className={linkClass}>
          Dashboard
        </NavLink>

        <NavLink to="/analysis" className={linkClass}>
          New Analysis
        </NavLink>

        <NavLink to="/history" className={linkClass}>
          Recent Results
        </NavLink>
      </div>
    </nav>
  );
}

export default Navbar;