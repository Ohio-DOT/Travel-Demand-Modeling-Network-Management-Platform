// src/services/api.js
import axios from 'axios';
import { logout } from './auth';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/',
});

api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  res => res,
  async error => {
    const originalRequest = error.config;
    if (
      (error.response?.status === 401 || error.response?.status === 403) &&
      !originalRequest._retry &&
      localStorage.getItem('refresh_token')
    ) {
      originalRequest._retry = true;
      try {
        const res = await axios.post('http://localhost:8000/api/token/refresh/', {
          refresh: localStorage.getItem('refresh_token')
        });
        localStorage.setItem('access_token', res.data.access);
        originalRequest.headers.Authorization = `Bearer ${res.data.access}`;
        return api(originalRequest); // retry original request
      } catch (refreshErr) {
        logout();
      }
    }
    return Promise.reject(error);
  }
);

export default api;
