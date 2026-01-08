/**
 * Types for admin user management.
 */

export interface User {
  id: string;
  name: string;
  email: string;
  role: "STUDENT" | "ADMIN" | "REVIEWER";
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface UsersListResponse {
  items: User[];
  page: number;
  page_size: number;
  total: number;
}

export interface UserCreate {
  name: string;
  email: string;
  role: "STUDENT" | "ADMIN" | "REVIEWER";
  is_active: boolean;
}

export interface UserUpdate {
  name?: string;
  role?: "STUDENT" | "ADMIN" | "REVIEWER";
  is_active?: boolean;
}

export interface PasswordResetResponse {
  message: string;
  email_sent: boolean;
}
