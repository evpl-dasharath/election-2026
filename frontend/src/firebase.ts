import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getDatabase } from "firebase/database";

const firebaseConfig = {
  apiKey: "AIzaSyDeoQ4m1hgajz7yUBaawssdH9RgKWXXqiI",
  authDomain: "kl-2026.firebaseapp.com",
  databaseURL: "https://kl-2026-default-rtdb.asia-southeast1.firebasedatabase.app",
  projectId: "kl-2026",
  storageBucket: "kl-2026.firebasestorage.app",
  messagingSenderId: "729403396504",
  appId: "1:729403396504:web:bcea2d07d037d8d428dbed",
  measurementId: "G-6QX0TK7MHN"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Realtime Database and get a reference to the service
export const db = getDatabase(app);
