import React from "react";

/**
 * Loading spinner component with animation.
 */
export function LoadingSpinner() {
  return (
    <div className="flex justify-center items-center py-16">
      <div className="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
      <span className="ml-4 text-lg text-gray-600 font-medium">
        Loading rates...
      </span>
    </div>
  );
}

/**
 * Error message component with icon.
 */
export function ErrorMessage({ message }: { message: string }) {
  return (
    <div className="mb-4 p-4 bg-red-50 border-l-4 border-red-500 rounded-lg shadow-sm">
      <div className="flex items-start">
        <span className="text-2xl mr-3">⚠️</span>
        <div className="flex-1">
          <h3 className="font-bold text-red-800 text-lg">Error</h3>
          <p className="text-red-700 text-sm mt-1">{message}</p>
          <p className="text-red-600 text-xs mt-2">
            Please try refreshing or check if the API is running at
            localhost:8000
          </p>
        </div>
      </div>
    </div>
  );
}

/**
 * Success message component with animation.
 */
export function SuccessMessage({ message }: { message: string }) {
  return (
    <div className="mb-4 p-4 bg-green-50 border-l-4 border-green-500 rounded-lg shadow-sm">
      <div className="flex items-center">
        <span className="text-2xl mr-3">✓</span>
        <div>
          <p className="text-green-700 font-medium">{message}</p>
        </div>
      </div>
    </div>
  );
}

/**
 * Badge component for categorization.
 */
export function Badge({
  children,
  variant = "default",
}: {
  children: React.ReactNode;
  variant?: "default" | "success" | "warning" | "error";
}) {
  const variants = {
    default: "bg-gray-100 text-gray-800",
    success: "bg-green-100 text-green-800",
    warning: "bg-yellow-100 text-yellow-800",
    error: "bg-red-100 text-red-800",
  };
  return (
    <span
      className={`inline-block px-2 py-1 text-xs rounded font-medium ${variants[variant]}`}
    >
      {children}
    </span>
  );
}

/**
 * Skeleton loading placeholder.
 */
export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 animate-pulse rounded ${className}`}
    ></div>
  );
}

/**
 * Empty state component.
 */
export function EmptyState({
  title,
  description,
}: {
  title: string;
  description?: string;
}) {
  return (
    <div className="text-center py-12">
      <span className="text-6xl mb-4 block">📭</span>
      <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
      {description && (
        <p className="text-gray-600 text-sm mt-1">{description}</p>
      )}
    </div>
  );
}

/**
 * Tooltip component.
 */
export function Tooltip({
  content,
  children,
}: {
  content: string;
  children: React.ReactNode;
}) {
  const [showTooltip, setShowTooltip] = React.useState(false);
  return (
    <div className="relative inline-block">
      <div
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        {children}
      </div>
      {showTooltip && (
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-1 bg-gray-800 text-white text-xs rounded whitespace-nowrap pointer-events-none z-10">
          {content}
        </div>
      )}
    </div>
  );
}
