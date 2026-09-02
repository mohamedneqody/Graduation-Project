
mig_file = 'alembic/versions/79b5a57ca6d6_add_prescription_ocr_tables.py'
with open(mig_file, 'r') as f:
    content = f.read()

upgrade_code = '''def upgrade() -> None:
    # prescriptions table
    op.create_table('prescriptions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('file_id', sa.String(length=255), nullable=False),
        sa.Column('uploaded_by', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='uploaded', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # prescription_analyses table
    op.create_table('prescription_analyses',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('prescription_id', sa.UUID(), nullable=False),
        sa.Column('provider', sa.String(length=100), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('model_version', sa.String(length=100), nullable=True),
        sa.Column('prompt_version', sa.String(length=100), nullable=True),
        sa.Column('schema_version', sa.String(length=100), nullable=True),
        sa.Column('request_id', sa.String(length=255), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('token_usage', sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('raw_response', sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='pending', nullable=False),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['prescription_id'], ['prescriptions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_prescription_analyses_prescription_id'), 'prescription_analyses', ['prescription_id'], unique=False)
    
    # prescription_items table
    op.create_table('prescription_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('analysis_id', sa.UUID(), nullable=False),
        sa.Column('raw_name', sa.String(length=255), nullable=True),
        sa.Column('normalized_name', sa.String(length=255), nullable=True),
        sa.Column('strength', sa.String(length=100), nullable=True),
        sa.Column('dosage_form', sa.String(length=100), nullable=True),
        sa.Column('quantity', sa.String(length=100), nullable=True),
        sa.Column('duration', sa.String(length=100), nullable=True),
        sa.Column('instructions', sa.String(length=500), nullable=True),
        sa.Column('ocr_confidence', sa.Float(), nullable=True),
        sa.Column('is_illegible', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('match_status', sa.String(length=50), nullable=False),
        sa.Column('matched_drug_id', sa.UUID(), nullable=True),
        sa.Column('match_confidence', sa.Float(), nullable=True),
        sa.Column('candidate_margin', sa.Float(), nullable=True),
        sa.Column('candidates', sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('pharmacist_decision', sa.String(length=50), server_default='pending', nullable=False),
        sa.Column('pharmacist_selected_drug_id', sa.UUID(), nullable=True),
        sa.Column('reviewed_by', sa.UUID(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['analysis_id'], ['prescription_analyses.id'], ),
        sa.ForeignKeyConstraint(['matched_drug_id'], ['drugs.drug_id'], ),
        sa.ForeignKeyConstraint(['pharmacist_selected_drug_id'], ['drugs.drug_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_prescription_items_analysis_id'), 'prescription_items', ['analysis_id'], unique=False)'''

downgrade_code = '''def downgrade() -> None:
    op.drop_index(op.f('ix_prescription_items_analysis_id'), table_name='prescription_items')
    op.drop_table('prescription_items')
    op.drop_index(op.f('ix_prescription_analyses_prescription_id'), table_name='prescription_analyses')
    op.drop_table('prescription_analyses')
    op.drop_table('prescriptions')'''

content = content.replace('def upgrade() -> None:\n    pass', upgrade_code)
content = content.replace('def downgrade() -> None:\n    pass', downgrade_code)

with open(mig_file, 'w') as f:
    f.write(content)

