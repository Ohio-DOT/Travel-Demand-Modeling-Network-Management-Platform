import { useEffect } from 'react';
import { jwtDecode } from 'jwt-decode';

export default function AuthVerify({ logout, checkInterval = 5*1000*60 }) {
  useEffect(() => {
    const interval = setInterval(() => {
      const token = localStorage.getItem('access_token');
      if (token) {
        try {
          const decoded = jwtDecode(token);
          const currentTime = Date.now() / 1000;
          if (decoded.exp && decoded.exp < currentTime) {
            console.warn('Token expired. Logging out.');
            logout();
          }
        } catch (error) {
          console.error('Failed to decode token.', error);
          logout();
        }
      }
    }, checkInterval);

    return () => clearInterval(interval);
  }, [logout, checkInterval]);

  return null;
}
