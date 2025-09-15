// src/components/Auth/SignupForm.jsx
import React, { useState } from 'react';
import { signup } from '../../services/auth';

export default function SignupForm() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');

  const handleSubmit = async e => {
    e.preventDefault();
    try {
      await signup(username, password);
      setMessage('Signup successful! You may now log in.');
    } catch (err) {
      setMessage('Signup failed.');
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <h2>Sign Up</h2>
      <input value={username} onChange={e => setUsername(e.target.value)} placeholder="Username" />
      <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Password" />
      <button type="submit">Sign Up</button>
      <p>{message}</p>
    </form>
  );
}
