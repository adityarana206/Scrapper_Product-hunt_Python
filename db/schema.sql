CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  full_name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  mobile_number TEXT,
  linkedin_url TEXT,
  producthunt_url TEXT,
  producthunt_username TEXT,
  university_name TEXT,
  tshirt_size TEXT,
  avatar_url TEXT,
  current_streak INTEGER DEFAULT 0,
  highest_streak INTEGER DEFAULT 0,
  last_updated TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS streak_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  streak_count INTEGER NOT NULL,
  captured_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_producthunt_username ON users(producthunt_username);
CREATE INDEX IF NOT EXISTS idx_users_current_streak ON users(current_streak DESC);
CREATE INDEX IF NOT EXISTS idx_streak_history_user_id ON streak_history(user_id);
CREATE INDEX IF NOT EXISTS idx_streak_history_captured_at ON streak_history(captured_at DESC);

CREATE TABLE IF NOT EXISTS registrations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  full_name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  mobile_number TEXT,
  linkedin_url TEXT,
  producthunt_url TEXT,
  producthunt_username TEXT,
  university_name TEXT,
  tshirt_size TEXT,
  avatar_url TEXT,
  current_streak INTEGER DEFAULT 0,
  highest_streak INTEGER DEFAULT 0,
  last_updated TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_registrations_producthunt_username ON registrations(producthunt_username);
