import React, { createContext, useContext, useState, useCallback, useRef } from "react";
import axios from "axios";
import { useAuth } from "./AuthContext";
import { API_URLS } from "../utils/constants";

const NotificationContext = createContext();

export const NotificationProvider = ({ children }) => {
  const { user } = useAuth();
  const [settings, setSettings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const baseURL = API_URLS.NOTIFICATION || "http://localhost:8088/api";

  const fetchInProgress = useRef(false);
  
  const fetchSettings = useCallback(async () => {
    if (fetchInProgress.current) return;
    
    if (!user) return;
    fetchInProgress.current = true;
    setLoading(true);
    setError(null);
    try {
      const { data } = await axios.get(
        `${baseURL}/notifications/settings`,
        { withCredentials: true }
      );
      setSettings(data);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
      fetchInProgress.current = false;
    }
  }, [user, baseURL]);

  const createSetting = useCallback(async (eventType, payload) => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await axios.post(
        `${baseURL}/notifications/settings`,
        { 
          event_type: eventType, 
          email: user.email,
          email_enabled: false,
          push_enabled: false,
          user_id: String(user.id),
          ...payload
        },
        { withCredentials: true }
      );
      setSettings(prev => [...prev, data]);
      return data;
    } catch (e) {
      setError(e);
      throw e;
    } finally {
      setLoading(false);
    }
  }, [user, baseURL, setSettings]);

  const updateSetting = useCallback(async (eventType, payload) => {
    setError(null);
    try {
      const { data } = await axios.patch(
        `${baseURL}/notifications/settings`,
        payload,
        { params: { event_type: eventType }, withCredentials: true }
      );
      setSettings(prev => prev.map(s => (s.event_type === eventType ? data : s)));
    } catch (e) {
      if (e.response?.status === 404) {
        await createSetting(eventType, payload);
        return;
      }
      setError(e);
    }
  }, [baseURL, createSetting]);

  React.useEffect(() => {
    if (user && user.id && settings.length === 0) {
      fetchSettings();
    }
  }, [user, fetchSettings, settings.length]);

  return (
    <NotificationContext.Provider value={{ settings, loading, error, fetchSettings, createSetting, updateSetting }}>
      {children}
    </NotificationContext.Provider>
  );
};

export const useNotifications = () => useContext(NotificationContext); 