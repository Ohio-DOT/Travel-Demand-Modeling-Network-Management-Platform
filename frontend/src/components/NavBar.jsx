// src/components/NavBar.jsx
import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { logout } from '../services/auth';

export default function NavBar() {
  const navigate = useNavigate();
  const loggedIn = !!localStorage.getItem('access_token');

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="mmx-auto max-w-7xl px-2 sm:px-6 lg:px-8" >
      <Link to="/">Home</Link>
      {loggedIn ? (
        <button onClick={handleLogout}>Logout</button>
      ) : (
        <>
          {/* <Link to="/login">Login</Link>
          <Link to="/signup">Sign Up</Link> */}
        </>
      )}
    </nav>
  );
}
