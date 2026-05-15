const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

module.exports = {
  name: process.env.CANDIDATE_NAME || 'Sanagapalli Sri Ram Praneeth',
  email: process.env.CANDIDATE_EMAIL || 'praneethssr.2002@gmail.com',
  phone: process.env.CANDIDATE_PHONE || '9999999999',
  linkedin: process.env.CANDIDATE_LINKEDIN || 'https://www.linkedin.com/in/sriampraneeth143/',
  resumePath: path.join(__dirname, '..', process.env.RESUME_PDF_PATH || 'data/resume.pdf'),
  headless: process.env.HEADLESS === 'true',
  authDir: path.join(__dirname, 'auth'),

  dailyTarget: parseInt(process.env.DAILY_APPLY_TARGET || '100'),
  maxExpYears: parseInt(process.env.MAX_EXPERIENCE_YEARS || '3'),

  notifyEmail: process.env.NOTIFY_EMAIL || process.env.CANDIDATE_EMAIL || '',
  smtpUser: process.env.SMTP_USER || process.env.CANDIDATE_EMAIL || '',
  smtpPass: process.env.SMTP_PASS || '',
  ntfyTopic: process.env.NTFY_TOPIC || '',

  roles: [
    'DevOps Engineer',
    'AWS Cloud Engineer',
    'Kubernetes Engineer',
    'Site Reliability Engineer',
    'Infrastructure Engineer',
    'Platform Engineer',
  ],
  locations: ['Hyderabad', 'Bangalore', 'Remote', 'Pune', 'Chennai'],
};
