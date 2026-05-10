CREATE TABLE IF NOT EXISTS public.feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    email TEXT,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    liked TEXT,
    disliked TEXT,
    improvement TEXT,
    contact_ok BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE public.feedback ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "feedback_service_role_all" ON public.feedback;

CREATE POLICY "feedback_service_role_all"
ON public.feedback
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

REVOKE ALL ON public.feedback FROM anon;
REVOKE ALL ON public.feedback FROM authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.feedback TO service_role;
