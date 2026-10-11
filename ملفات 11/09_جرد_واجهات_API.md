# 🔌 جرد واجهات API — AI-COS (مولّد برمجيًا من التطبيق نفسه)

**إجمالي نقاط النهاية الثابتة: 191** (بالإضافة إلى نقاط المعاملات الديناميكية ذات المعرفات)

## /accounting (5)
- `GET` /api/v1/accounting/forensics/benford
- `GET` /api/v1/accounting/journal-entries
- `POST` /api/v1/accounting/sync-from-orders
- `GET` /api/v1/accounting/trial-balance
- `GET` /api/v1/accounting/working-capital

## /agents (36)
- `POST` /api/v1/agents/analytics/summary
- `POST` /api/v1/agents/automation/callback
- `GET` /api/v1/agents/automation/metrics
- `POST` /api/v1/agents/automation/trigger
- `GET` /api/v1/agents/customer-profiles
- `POST` /api/v1/agents/customer-success/insights
- `POST` /api/v1/agents/documentation/compliance-audit
- `POST` /api/v1/agents/documentation/log-decision
- `POST` /api/v1/agents/finance/clv
- `GET` /api/v1/agents/financial-vision
- `POST` /api/v1/agents/inventory/alert
- `POST` /api/v1/agents/inventory/create-reorder-po
- `GET` /api/v1/agents/market-intelligence/actions
- `GET` /api/v1/agents/market-intelligence/insights
- `POST` /api/v1/agents/market-intelligence/scan
- `POST` /api/v1/agents/marketing/generate-campaign
- `POST` /api/v1/agents/marketing/validate-coupon
- `GET` /api/v1/agents/models/active
- `POST` /api/v1/agents/models/benchmark
- `POST` /api/v1/agents/models/finetune
- `GET` /api/v1/agents/models/list
- `POST` /api/v1/agents/models/pull
- `POST` /api/v1/agents/models/switch
- `POST` /api/v1/agents/orchestrator/route
- `POST` /api/v1/agents/pricing/calculate-discount
- `POST` /api/v1/agents/sales/cross-sell
- `POST` /api/v1/agents/simulator/curve
- `POST` /api/v1/agents/simulator/deploy
- `GET` /api/v1/agents/simulator/drugs
- `POST` /api/v1/agents/simulator/prefill
- `POST` /api/v1/agents/simulator/run
- `GET` /api/v1/agents/simulator/runs
- `GET` /api/v1/agents/simulator/scenarios/chronic
- `GET` /api/v1/agents/simulator/scenarios/dead-stock
- `GET` /api/v1/agents/support/complaints
- `POST` /api/v1/agents/support/handle-complaint

## /ai (7)
- `POST` /api/v1/ai/chat
- `POST` /api/v1/ai/copilot/draft
- `POST` /api/v1/ai/export-summary-pdf
- `POST` /api/v1/ai/patient-health-insights
- `GET` /api/v1/ai/security-kpis
- `POST` /api/v1/ai/tts
- `POST` /api/v1/ai/upload-prescription-chat

## /analytics (12)
- `GET` /api/v1/analytics/ab-statistical-significance
- `POST` /api/v1/analytics/ab-tests
- `GET` /api/v1/analytics/ab-tests
- `POST` /api/v1/analytics/ab-tests/mark-converted
- `POST` /api/v1/analytics/ab-tests/record-result
- `GET` /api/v1/analytics/cohort-retention
- `GET` /api/v1/analytics/drug-affinity-network
- `GET` /api/v1/analytics/revenue-forecast
- `GET` /api/v1/analytics/revenue-trend
- `GET` /api/v1/analytics/seasonal-analysis
- `GET` /api/v1/analytics/summary
- `GET` /api/v1/analytics/weekly-summary

## /auth (4)
- `POST` /api/v1/auth/complete-registration
- `POST` /api/v1/auth/invite-customer
- `POST` /api/v1/auth/invite-customer/
- `GET` /api/v1/auth/me

## /business-value (13)
- `POST` /api/v1/business-value/ab-tests
- `GET` /api/v1/business-value/ab-tests
- `GET` /api/v1/business-value/ai-feasibility-and-uat
- `GET` /api/v1/business-value/balanced-scorecard
- `GET` /api/v1/business-value/coupon-effectiveness
- `GET` /api/v1/business-value/funnel
- `GET` /api/v1/business-value/governance-scorecard
- `GET` /api/v1/business-value/impact-ticker
- `GET` /api/v1/business-value/internal/weekly-digest
- `GET` /api/v1/business-value/privacy/cloud-ocr
- `PUT` /api/v1/business-value/privacy/cloud-ocr
- `GET` /api/v1/business-value/roi
- `GET` /api/v1/business-value/value-chains

## /customers (13)
- `POST` /api/v1/customers
- `GET` /api/v1/customers
- `POST` /api/v1/customers/
- `GET` /api/v1/customers/
- `POST` /api/v1/customers/contact
- `GET` /api/v1/customers/contact/admin-inbox
- `GET` /api/v1/customers/health
- `GET` /api/v1/customers/me
- `PATCH` /api/v1/customers/me
- `GET` /api/v1/customers/me/clinical-adherence
- `GET` /api/v1/customers/me/events
- `POST` /api/v1/customers/privacy/anonymize-account
- `GET` /api/v1/customers/privacy/my-data-export

## /drugs (10)
- `POST` /api/v1/drugs
- `GET` /api/v1/drugs
- `POST` /api/v1/drugs/
- `GET` /api/v1/drugs/
- `POST` /api/v1/drugs/affinities
- `GET` /api/v1/drugs/categories
- `POST` /api/v1/drugs/check-duplicate-therapy
- `POST` /api/v1/drugs/check-interactions
- `POST` /api/v1/drugs/interactions
- `GET` /api/v1/drugs/recommendations

## /events (1)
- `POST` /api/v1/events

## /files (1)
- `POST` /api/v1/files/upload

## /governance (7)
- `GET` /api/v1/governance/audit-logs
- `POST` /api/v1/governance/evaluate
- `GET` /api/v1/governance/events-chain/verify
- `GET` /api/v1/governance/health-telemetry
- `GET` /api/v1/governance/ledger/verify
- `GET` /api/v1/governance/risk-register
- `GET` /api/v1/governance/thresholds

## /insights (5)
- `GET` /api/v1/insights/compliance-score
- `GET` /api/v1/insights/demand-forecast
- `GET` /api/v1/insights/rfm
- `GET` /api/v1/insights/time-study
- `GET` /api/v1/insights/weekly-report

## /inventory (2)
- `GET` /api/v1/inventory
- `GET` /api/v1/inventory/

## /orders (5)
- `POST` /api/v1/orders
- `GET` /api/v1/orders
- `POST` /api/v1/orders/
- `GET` /api/v1/orders/
- `GET` /api/v1/orders/all

## /predictions (3)
- `POST` /api/v1/predictions/churn
- `POST` /api/v1/predictions/combined
- `POST` /api/v1/predictions/cycle

## /prescriptions (6)
- `POST` /api/v1/prescriptions
- `POST` /api/v1/prescriptions/
- `GET` /api/v1/prescriptions/accuracy-report
- `DELETE` /api/v1/prescriptions/cleanup-retention
- `GET` /api/v1/prescriptions/corrections
- `GET` /api/v1/prescriptions/vision-metrics

## /procurement (5)
- `GET` /api/v1/procurement/purchase-orders
- `POST` /api/v1/procurement/purchase-orders/auto-generate
- `GET` /api/v1/procurement/summary
- `GET` /api/v1/procurement/suppliers
- `POST` /api/v1/procurement/suppliers

## /settings (5)
- `GET` /api/v1/settings
- `PATCH` /api/v1/settings
- `GET` /api/v1/settings/
- `PATCH` /api/v1/settings/
- `GET` /api/v1/settings/runtime-config

## /verticals (8)
- `POST` /api/v1/verticals/activate
- `GET` /api/v1/verticals/available
- `GET` /api/v1/verticals/catalog
- `GET` /api/v1/verticals/current
- `GET` /api/v1/verticals/isolation-proof
- `GET` /api/v1/verticals/preview
- `POST` /api/v1/verticals/provision
- `GET` /api/v1/verticals/tenants

## /webhooks (1)
- `POST` /api/v1/webhooks/incoming

