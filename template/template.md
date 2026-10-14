# Forex Exposure Note
Foreign-currency vendor payments due | Reference date {{reference_date}}

## 1. Headline
{{COMMENTARY:headline}}

## 2. Key figures
- Payments analysed: {{n_valid}} across {{n_currencies}} currencies and {{n_vendors}} vendors
- Booked value: {{booked_total}}
- Value at live rates: {{live_total}}
- Movement against booked rates: {{net_delta}} ({{net_delta_pct}}), an overall {{delta_word}}
- Unhedged exposure at live rates: {{unhedged_live}} ({{unhedged_pct}} of total)
- Overdue payments: {{overdue_count}} items worth {{overdue_live}}, with accrued late interest of about {{late_interest_lakh}}

## 3. Exposure by currency
{{TABLE:currency_summary}}

## 4. What is driving the movement
{{COMMENTARY:drivers}}

## 5. When the payments fall due
{{TABLE:aging}}

## 6. Largest open exposures by vendor
{{TABLE:top_vendors}}

## 7. If the rupee weakens further
{{TABLE:sensitivity}}
Open exposure means unhedged payments only. Hedged items are assumed fully covered at the booked rate.

## 8. Recommended actions
{{COMMENTARY:actions}}

## 9. Basis of preparation
- Rates: {{rate_source}}, dated {{rate_date}}. Status: {{rate_status}}. {{rate_status_note}}
- These are market reference rates and not RBI reference rates. Confirm with the treasury rate card before any booking.
- Input file: {{input_file}}. Rows loaded {{n_loaded}}, used {{n_valid}}, excluded {{n_excluded}}.
- Additional cost means payment value at live rates less value at booked rates. A negative figure is a saving.
- Late interest is simple interest on overdue items at the contractual rate, converted at live rates.
{{TABLE:data_issues}}
