import React from 'react';
import clsx from 'clsx';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger';
  size?: 'small' | 'medium' | 'large';
  isLoading?: boolean;
  icon?: React.ReactNode;
  children: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'medium',
  isLoading = false,
  icon,
  children,
  className,
  disabled,
  ...props
}) => {
  const baseClasses = `
    inline-flex items-center justify-center gap-2 
    border-none rounded-lg font-semibold cursor-pointer 
    transition-all duration-200 ease-in-out
    focus:outline-none focus:ring-2 focus:ring-offset-2
    disabled:opacity-60 disabled:cursor-not-allowed
  `;

  const variantClasses = {
    primary: `
      bg-blue-600 text-white hover:bg-blue-700 
      focus:ring-blue-500 hover:transform hover:-translate-y-0.5
    `,
    secondary: `
      bg-gray-100 text-gray-700 hover:bg-gray-200 
      focus:ring-gray-500
    `,
    success: `
      bg-green-600 text-white hover:bg-green-700 
      focus:ring-green-500
    `,
    warning: `
      bg-orange-500 text-white hover:bg-orange-600 
      focus:ring-orange-500
    `,
    danger: `
      bg-red-600 text-white hover:bg-red-700 
      focus:ring-red-500
    `,
  };

  const sizeClasses = {
    small: 'px-3 py-2 text-sm',
    medium: 'px-5 py-3 text-base',
    large: 'px-6 py-4 text-lg',
  };

  return (
    <button
      className={clsx(
        baseClasses,
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
      ) : (
        icon
      )}
      {children}
    </button>
  );
};
