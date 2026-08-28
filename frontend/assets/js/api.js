/**
 * BugSense AI — Central API Fetch Wrapper
 */
import { showToast } from './utils.js';

const API_BASE_URL = window.location.port === '3000' 
  ? 'http://127.0.0.1:8000/api'
  : '/api';

export async function apiRequest(endpoint, options = {}) {
  const token = localStorage.getItem('bugsense_token');
  const headers = {
    ...options.headers,
  };

  // If payload is not FormData, default to application/json
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    // Handle 401 Unauthorized
    if (response.status === 401 && !endpoint.includes('/auth/login')) {
      localStorage.removeItem('bugsense_token');
      localStorage.removeItem('bugsense_user');
      showToast('Session expired. Please log in again.', 'error');
      if (!window.location.pathname.includes('login.html')) {
        window.location.href = 'login.html';
      }
      return null;
    }

    const data = await response.json();

    if (!response.ok) {
      const errorMsg = data?.error?.message || data?.detail || 'Request failed';
      if (!options.suppressToast) {
        showToast(errorMsg, 'error');
      }
      const err = new Error(errorMsg);
      err.data = data;
      err.errorData = data?.error;
      err.status = response.status;
      throw err;
    }

    return data;
  } catch (err) {
    if (!err.message.includes('Session expired') && !options.suppressToast) {
      console.error('API Error on ' + endpoint, err);
    }
    throw err;
  }
}

