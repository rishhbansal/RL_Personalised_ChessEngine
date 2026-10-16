import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import "./Navbar.css";

const Navbar = () => {
  const { user, logout } = useAuth();
  const location = useLocation();

  const links = [
    { to: "/", label: "Home" },
    { to: "/play", label: "Play" },
    { to: "/analysis", label: "Analysis" },
 
  ];

  return (
    <nav className="app-nav">
      <span className="app-nav-brand">♟ ChessMentor</span>

      <div className="app-nav-links">
        {links.map((l) => (
          <Link
            key={l.to}
            to={l.to}
            className={`app-nav-link ${location.pathname === l.to ? "active" : ""}`}
          >
            {l.label}
          </Link>
        ))}
      </div>

      <div className="app-nav-user">
        {user ? (
          <>
            <span className="app-nav-email">{user.email}</span>
            <button className="app-nav-logout" onClick={logout}>
              Logout
            </button>
          </>
        ) : (
          <Link to="/login" className="app-nav-link">
            Login
          </Link>
        )}
      </div>
    </nav>
  );
};

export default Navbar;