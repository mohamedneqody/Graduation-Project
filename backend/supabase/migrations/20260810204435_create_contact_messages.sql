-- Migration: Create contact_messages table

CREATE TABLE contact_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    customer_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE contact_messages ENABLE ROW LEVEL SECURITY;

-- Create policy for tenant isolation (users can only insert their own messages, admins can read)
CREATE POLICY "Users can insert their own contact messages" 
ON contact_messages 
FOR INSERT 
WITH CHECK (
  auth.uid() = customer_id OR customer_id IS NULL
);

-- Admins/Service Role can manage all messages (tenant_id filtering is usually handled via BOLA in FastAPI)
CREATE POLICY "Service role has full access"
ON contact_messages
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
