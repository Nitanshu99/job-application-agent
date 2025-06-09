import React from 'react';
import { clsx } from 'clsx';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: 'none' | 'small' | 'medium' | 'large';
  shadow?: 'none' | 'small' | 'medium' | 'large';
}

export const Card: React.FC<CardProps> = ({
  children,
  className,
  padding = 'medium',
  shadow = 'medium',
}) => {
  const paddingClasses = {
    none: '',
    small: 'p-4',
    medium: 'p-6',
    large: 'p-8',
  };

  const shadowClasses = {
    none: '',
    small: 'shadow-sm',
    medium: 'shadow-md',
    large: 'shadow-lg',
  };

  return (
    <div
      className={clsx(
        'bg-white rounded-xl border border-gray-200',
        paddingClasses[padding],
        shadowClasses[shadow],
        className
      )}
    >
      {children}
    </div>
  );
};

interface CardHeaderProps {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  className?: string;
}

export const CardHeader: React.FC<CardHeaderProps> = ({
  title,
  subtitle,
  action,
  className,
}) => {
  return (
    <div className={clsx('flex justify-between items-start mb-6 pb-4 border-b border-gray-200', className)}>
      <div>
        <h2 className="text-xl font-semibold text-gray-800">{title}</h2>
        {subtitle && <p className="text-gray-600 text-sm mt-1">{subtitle}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
};

interface StatCardProps {
  title: string;
  value: string | number;
  change?: {
    value: string;
    trend: 'up' | 'down' | 'neutral';
  };
  icon?: React.ReactNode;
  className?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  change,
  icon,
  className,
}) => {
  const trendColors = {
    up: 'text-green-600',
    down: 'text-red-600',
    neutral: 'text-gray-600',
  };

  return (
    <Card className={clsx('text-center hover:transform hover:-translate-y-1 transition-transform', className)}>
      {icon && <div className="flex justify-center mb-3">{icon}</div>}
      <div className="text-3xl font-bold text-blue-600 mb-2">{value}</div>
      <div className="text-gray-600 font-medium text-sm">{title}</div>
      {change && (
        <div className={clsx('text-xs font-semibold mt-2', trendColors[change.trend])}>
          {change.value}
        </div>
      )}
    </Card>
  );
};
