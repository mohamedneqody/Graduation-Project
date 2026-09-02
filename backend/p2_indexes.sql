-- P2-6: Missing Foreign Key Indexes
-- These indexes prevent full table scans when joining or filtering on the second column
-- of composite keys or composite unique constraints.

-- 1. Index on drug_id_b for drug_interactions
-- (drug_id_a is already indexed via the unique constraint uq_interaction_pair)
CREATE INDEX IF NOT EXISTS idx_drug_interactions_drug_id_b 
ON drug_interactions(drug_id_b);

-- 2. Index on drug_id_b for drug_affinities
-- (drug_id_a is already indexed via the unique constraint uq_affinity_pair)
CREATE INDEX IF NOT EXISTS idx_drug_affinities_drug_id_b 
ON drug_affinities(drug_id_b);

-- 3. Index on drug_id for customer_cycles
-- (customer_id is already indexed as the first column of the primary key)
CREATE INDEX IF NOT EXISTS idx_customer_cycles_drug_id 
ON customer_cycles(drug_id);
