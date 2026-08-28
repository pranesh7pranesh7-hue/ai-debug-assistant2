/**
 * BugSense AI — Authentication Manager
 */
import { apiRequest } from './api.js';
import { showToast } from './utils.js';

export function getAuthToken() {
  return localStorage.getItem('bugsense_token');
}

export function getCurrentUser() {
  const user = localStorage.getItem('bugsense_user');
  return user ? JSON.parse(user) : null;
}

export function requireAuth() {
  const token = getAuthToken();
  if (!token) {
    window.location.href = 'login.html';
  }
}

export function logout() {
  localStorage.removeItem('bugsense_token');
  localStorage.removeItem('bugsense_user');
  showToast('Logged out successfully', 'info');
  setTimeout(() => {
    window.location.href = 'login.html';
  }, 300);
}

export async function login(email, password) {
  const data = await apiRequest('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });

  if (data && data.access_token) {
    localStorage.setItem('bugsense_token', data.access_token);
    localStorage.setItem('bugsense_user', JSON.stringify({ id: data.user_id, email: data.email }));
    showToast('Login successful!', 'success');
    setTimeout(() => {
      window.location.href = 'index.html';
    }, 400);
    return data;
  }
}

export async function register(email, password) {
  const data = await apiRequest('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });

  if (data && data.access_token) {
    localStorage.setItem('bugsense_token', data.access_token);
    localStorage.setItem('bugsense_user', JSON.stringify({ id: data.user_id, email: data.email }));
    showToast('Account registered successfully!', 'success');
    setTimeout(() => {
      window.location.href = 'index.html';
    }, 400);
    return data;
  }
}
