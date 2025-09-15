// src/services/auth.js
import api from './api';

export const login = async (username, password) => {
  const res = await api.post('token/', { username, password });
  localStorage.setItem('access_token', res.data.access);
  localStorage.setItem('refresh_token', res.data.refresh);
  return res.data;
};

export const signup = async (username, password) => {
  return await api.post('signup/', { username, password });
};

export const logout = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  window.location.href = '/login';
};
