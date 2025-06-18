import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import clsx from 'clsx';
import { Button } from '../ui/Button';
import { User } from '../../types';

interface NavbarProps {
  user?: User;
  onLogout?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ user, onLogout }) => {
  const router = useRouter();
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  const navItems = [
    { href: '/dashboard', label: 'Dashboard' },
    { href: '/jobs', label: 'Job Search' },
    { href: '/applications', label: 'Applications' },
    { href: '/documents', label: 'Documents' },
    { href: '/portals', label: 'Job Portals' },
  ];

  const isActiveRoute = (href: string) => {
    return router.pathname === href || router.pathname.startsWith(href + '/');
  };

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase();
  };

  return (
    <nav className="bg-white border-b border-gray-200 px-6 py-4 sticky top-0 z-50 backdrop-blur-md">
      <div className="flex justify-between items-center">
        {/* Logo */}
        <Link href="/dashboard" className="text-2xl font-bold text-blue-600 hover:text-blue-700 transition-colors">
          JobFlow
        </Link>

        {/* Main Navigation */}
        <div className="hidden md:flex items-center space-x-8">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                'px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200',
                isActiveRoute(item.href)
                  ? 'text-blue-600 bg-blue-50'
                  : 'text-gray-700 hover:text-blue-600 hover:bg-gray-50'
              )}
            >
              {item.label}
            </Link>
          ))}
        </div>

        {/* User Menu */}
        {user ? (
          <div className="relative">
            <button
              onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
              className="flex items-center space-x-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-lg p-2"
            >
              <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white font-medium text-sm">
                {getInitials(user.full_name)}
              </div>
              <span className="hidden md:block text-gray-700 font-medium">{user.full_name}</span>
              <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {/* Dropdown Menu */}
            {isUserMenuOpen && (
              <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50">
                <Link
                  href="/profile"
                  className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                  onClick={() => setIsUserMenuOpen(false)}
                >
                  Profile Settings
                </Link>
                <Link
                  href="/applications"
                  className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                  onClick={() => setIsUserMenuOpen(false)}
                >
                  My Applications
                </Link>
                <hr className="my-2 border-gray-100" />
                <button
                  onClick={() => {
                    onLogout?.();
                    setIsUserMenuOpen(false);
                  }}
                  className="block w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
                >
                  Sign Out
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="flex items-center space-x-4">
            <Link href="/login">
              <Button variant="secondary" size="small">
                Sign In
              </Button>
            </Link>
            <Link href="/register">
              <Button variant="primary" size="small">
                Sign Up
              </Button>
            </Link>
          </div>
        )}
      </div>

      {/* Mobile Navigation */}
      <div className="md:hidden mt-4 pt-4 border-t border-gray-200">
        <div className="grid grid-cols-2 gap-2">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                'px-3 py-2 rounded-lg text-sm font-medium text-center transition-all duration-200',
                isActiveRoute(item.href)
                  ? 'text-blue-600 bg-blue-50'
                  : 'text-gray-700 hover:text-blue-600 hover:bg-gray-50'
              )}
            >
              {item.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
};
