export const API_ENDPOINTS = {
  AUTH: '/auth',
  USERS: '/users',
  JOBS: '/jobs',
  APPLICATIONS: '/applications',
  DOCUMENTS: '/documents',
  PORTALS: '/portals',
} as const;

export const JOB_TYPES = {
  FULL_TIME: 'full_time',
  PART_TIME: 'part_time',
  CONTRACT: 'contract',
  REMOTE: 'remote',
} as const;

export const EXPERIENCE_LEVELS = {
  ENTRY: 'entry',
  MID: 'mid',
  SENIOR: 'senior',
  EXECUTIVE: 'executive',
} as const;

export const APPLICATION_STATUSES = {
  PENDING: 'pending',
  APPLIED: 'applied',
  INTERVIEW: 'interview',
  OFFER: 'offer',
  REJECTED: 'rejected',
  WITHDRAWN: 'withdrawn',
} as const;

export const DOCUMENT_TYPES = {
  RESUME: 'resume',
  COVER_LETTER: 'cover_letter',
} as const;
