-- Create analysis_results table
CREATE TABLE IF NOT EXISTS public.analysis_results (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    attendance_id INTEGER NOT NULL,
    communication INTEGER NOT NULL,
    emotional_intelligence INTEGER NOT NULL,
    leadership INTEGER NOT NULL,
    problem_solving INTEGER NOT NULL,
    teamwork INTEGER NOT NULL,
    work_ethic INTEGER NOT NULL,
    persuasion INTEGER NOT NULL,
    adaptability INTEGER NOT NULL,
    feedback_handling INTEGER NOT NULL,
    stress_management INTEGER NOT NULL,
    summary TEXT NOT NULL,
    pros TEXT NOT NULL,
    cons TEXT NOT NULL,
    next_questions TEXT[] NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add index for faster queries
CREATE INDEX IF NOT EXISTS idx_analysis_results_attendance_id ON public.analysis_results(attendance_id);

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to update updated_at timestamp
CREATE TRIGGER update_analysis_results_updated_at
    BEFORE UPDATE ON public.analysis_results
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add comment to table
COMMENT ON TABLE public.analysis_results IS 'Stores AI analysis results for candidate interviews';