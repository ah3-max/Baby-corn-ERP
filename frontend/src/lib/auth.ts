/**
 * 認證狀態管理工具
 */
import Cookies from 'js-cookie';

export const setTokens = (accessToken: string, refreshToken: string) => {
  Cookies.set('access_token', accessToken, { expires: 1 });       // 1 天
  Cookies.set('refresh_token', refreshToken, { expires: 7 });     // 7 天
};

export const clearTokens = () => {
  Cookies.remove('access_token');
  Cookies.remove('refresh_token');
};

export const getAccessToken = () => Cookies.get('access_token');
export const getRefreshToken = () => Cookies.get('refresh_token');
export const isLoggedIn = () => !!Cookies.get('access_token');
