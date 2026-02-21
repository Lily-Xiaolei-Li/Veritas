/**
 * Button Component
 *
 * Reusable button with variants and sizes.
 */

import React from "react";
import { cn } from "@/lib/utils/cn";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
}

export function Button({
  className,
  variant = "primary",
  size = "md",
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        // Base styles
        "inline-flex items-center justify-center rounded-md font-medium transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2",
        "disabled:pointer-events-none disabled:opacity-50",

        // Variants
        {
          "bg-blue-600 text-white hover:bg-blue-700 focus-visible:ring-blue-500":
            variant === "primary",
          "bg-gray-600 text-white hover:bg-gray-700 focus-visible:ring-gray-500":
            variant === "secondary",
          "border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-800 focus-visible:ring-gray-500":
            variant === "outline",
          "text-gray-700 dark:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800 focus-visible:ring-gray-500":
            variant === "ghost",
          "bg-red-600 text-white hover:bg-red-700 focus-visible:ring-red-500":
            variant === "danger",
        },

        // Sizes
        {
          "h-8 px-3 text-sm": size === "sm",
          "h-10 px-4 text-base": size === "md",
          "h-12 px-6 text-lg": size === "lg",
        },

        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
