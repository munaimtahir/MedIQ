/**
 * Global toast notification helper
 * Provides consistent toast notifications across the application
 */

import { toast } from "@/components/ui/use-toast";

/**
 * Show a success toast notification
 */
export function success(title: string, description?: string) {
  toast({
    title,
    description,
    variant: "default",
  });
}

/**
 * Show an error toast notification
 */
export function error(title: string, description?: string) {
  toast({
    title,
    description,
    variant: "destructive",
  });
}

/**
 * Show an info toast notification
 */
export function info(title: string, description?: string) {
  toast({
    title,
    description,
    variant: "default",
  });
}

/**
 * Notification helper object
 */
export const notify = {
  success,
  error,
  info,
};

