// src/components/Auth/LoginForm.jsx
import React, { useState } from 'react';
import { login } from '../../services/auth';
import { useNavigate } from 'react-router-dom';

export default function LoginForm() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async e => {
    e.preventDefault();
    try {
      await login(username, password);
      navigate('/');
    } catch {
      setMessage('Either username or password is wrong.');
    }
  };

  return (
    <div className="flex min-h-full flex-col justify-center px-6 py-12 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-sm">
        {/* <img className="mx-auto h-16 w-auto" src="https://portal.dot.state.oh.us/Images1/ODOT-The-Zephyr.png" alt="Your Company" /> */}
        <h2 className="mt-10 text-center text-2xl/9 font-bold tracking-tight text-gray-900">Sign in to your account</h2>
      </div>

      <div className="mt-10 sm:mx-auto sm:w-full sm:max-w-sm">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="user" className="block text-sm/6 font-medium text-gray-900">Username</label>
            <div className="mt-2">
              <input value={username} id="user" onChange={e => setUsername(e.target.value)} placeholder="Username" autoComplete="username" required className="block w-full rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-emerald-600 sm:text-sm/6" />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between">
              <label htmlFor="password" className="block text-sm/6 font-medium text-gray-900">Password</label>
              <div className="text-sm">
                <a href="#" className="font-semibold text-emerald-600 hover:text-emerald-500">Forgot password?</a>
              </div>
            </div>
            <div className="mt-2">
              <input type="password" id="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Password" autoComplete="current-password" required className="block w-full rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-emerald-600 sm:text-sm/6" />
            </div>
          </div>

          <div>
            <button type="submit" className="flex w-full justify-center rounded-md bg-emerald-600 px-3 py-1.5 text-sm/6 font-semibold text-white shadow-xs hover:bg-emerald-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600">Sign in</button>
          </div>
        </form>

        {/* <p className="mt-10 text-center text-sm/6 text-gray-500">
          Not a member?
          <a href="#" className="font-semibold text-emerald-600 hover:text-emerald-500">Start a 14 day free trial</a>
        </p> */}
        <p className="text-center text-red-600">{message}</p>
      </div>
    </div>
  );
}
