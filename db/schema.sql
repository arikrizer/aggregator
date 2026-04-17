-- טבלת פריטים
CREATE TABLE IF NOT EXISTS articles (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  run_date DATE NOT NULL,
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  source_type TEXT,
  source_emoji TEXT,
  summary_hebrew TEXT,
  sts_angle_hebrew TEXT,
  model_level INTEGER,
  model_concept TEXT,
  hr_relevant BOOLEAN DEFAULT false,
  resonance TEXT,
  tags TEXT[],
  published_date TEXT,
  agent TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- מניעת כפילויות: אותו URL באותו יום
CREATE UNIQUE INDEX IF NOT EXISTS articles_url_date
  ON articles (url, run_date);

-- טבלת דוחות יומיים
CREATE TABLE IF NOT EXISTS digests (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  run_date DATE UNIQUE NOT NULL,
  pulse TEXT,
  top_read_title TEXT,
  top_read_url TEXT,
  top_read_reason TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- פתיחת גישה (ל-POC בלבד)
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE digests ENABLE ROW LEVEL SECURITY;

CREATE POLICY "allow all" ON articles FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "allow all" ON digests FOR ALL USING (true) WITH CHECK (true);
