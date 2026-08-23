# Manual Test Scenarios (Streamlit UI)

30 questions for manually exercising `app.py`: 25 single-turn questions across all 7
categories, plus 5 memory-dependent scenarios that require asking multiple turns **with the
same Customer ID** in the sidebar (Mem0 memory is keyed by customer_id, not by the browser
session, so it survives a "Reset conversation" as long as the Customer ID field is unchanged).

This is a manual companion to `eval/test_queries.json` (the automated 20-query set) — use it to
click through the UI and visually check source badges, category badges, the escalation banner,
and the "How I got this answer" expander.

## Part 1 — Single-turn questions (25)

Use a fresh Customer ID for these (or just leave the auto-generated one), one question at a time.

### Refund

1. What's your policy on refunding an annual plan I just bought yesterday? — *expect: answer*
2. I was double-charged $85 for my Starter plan due to a glitch, can you refund the duplicate? — *expect: answer*
3. I was charged $250 for a plan I cancelled months ago, I want that money back. — *expect: escalate (amount > $100)*
4. I'd like a refund but I'm not 100% sure what I'm even being charged for. — *expect: escalate (ambiguous)*

### Proration

5. If I upgrade from Starter to Business on day 10 of my cycle, how much extra will I be charged? — *expect: answer*
6. My proration credit after downgrading was $95, does that sound right? — *expect: answer*
7. I expected a $420 credit from switching my annual plan to monthly but only got $150 — need this fixed. — *expect: escalate (amount > $100)*
8. The math on my proration doesn't add up but I can't pinpoint the issue. — *expect: escalate (ambiguous)*

### Payment Failure

9. My payment failed and I got an email about it — will it retry automatically? — *expect: answer*
10. My card is expiring next month, should I update it now to avoid a failed payment? — *expect: answer*
11. Payments have been weird lately, not sure what's going on with my account. — *expect: escalate (ambiguous)*

### Cancellation

12. How do I cancel my Business plan before the next renewal date? — *expect: answer*
13. If I cancel now, will I be charged again next month? — *expect: answer*
14. I want to leave but I'm not sure if cancelling or downgrading is the better move for me. — *expect: escalate (needs judgment)*

### Upgrade/Downgrade

15. What's the difference in features between the Pro and Business plans? — *expect: answer*
16. If I switch from Business to Enterprise, do I need to talk to sales? — *expect: answer*
17. Something changed with my plan and I honestly don't know if it was an upgrade or downgrade. — *expect: escalate (ambiguous)*

### Invoice Dispute

18. What does the "priority onboarding" line item on my invoice mean? — *expect: answer*
19. My invoice shows an $18 difference from what I expected, is that normal rounding? — *expect: answer*
20. There's a $175 charge on my invoice I don't recognize at all. — *expect: escalate (amount > $100)*
21. This month's invoice just doesn't look right to me overall. — *expect: escalate (ambiguous)*

### General Policy

22. Do you offer any discount for paying annually instead of monthly? — *expect: answer*
23. How do I add a VAT number to my account? — *expect: answer*
24. Can you explain how dunning emails work if I miss a payment? — *expect: answer*
25. I'm confused about something on my account settings page. — *expect: escalate (ambiguous)*

## Part 2 — Memory-dependent scenarios (5)

For each scenario: set a **specific Customer ID** in the sidebar first (e.g. `mem-test-1`) and
keep it unchanged for every turn in that scenario. Check the sidebar's **Customer context**
panel after each turn — it should fill in as Mem0 records durable info. Memory writes go
through an LLM summarization step, so wording that clearly states something durable (a plan,
a preference, a repeat issue) records more reliably than vague phrasing.

**26. Plan tier recall**
Customer ID: `mem-plan-tier`
- Turn 1: "I'm on the Business plan with 40 seats, just so you know."
- Turn 2: "What happens to my data if I downgrade?"
- *Check: sidebar's Customer context shows "Plan tier: Business..." after turn 1, and stays visible into turn 2.*

**27. Stated preference recall**
Customer ID: `mem-preference`
- Turn 1: "Please always email me a confirmation whenever you process a refund for me."
- Turn 2: "What's your refund policy for monthly plans?"
- *Check: sidebar's Customer context shows this under "Preferences" after turn 1.*

**28. Prior issue recall**
Customer ID: `mem-prior-issue`
- Turn 1: "How is proration calculated when I downgrade mid-cycle?" (answered)
- Turn 2: "Can you remind me what we discussed about proration?"
- *Check: sidebar's Customer context lists the proration question under "Prior issues" after turn 1; turn 2's memory context includes it as background (the answer itself must still be grounded in retrieved sources, not memory — that's the boundary the architecture enforces).*

**29. Escalation-override after repeated escalations (3 turns)**
Customer ID: `mem-repeat-escalation`
- Turn 1: "I was charged $300 for a refund request last week and it still hasn't shown up." — *expect: escalate (amount > $100); recorded as a "refund" escalation.*
- Turn 2: "I was also charged $150 incorrectly on a separate refund case." — *expect: escalate (amount > $100); second "refund" escalation recorded.*
- Turn 3: "What's your refund policy for monthly plans?" — a normally clear-cut, answerable, informational refund question. *Expect: escalate anyway* — the memory-override rule forces escalation once a customer has 2+ prior escalations in the same category, even though this question alone would otherwise be answered. Check the escalation reason in "How I got this answer" mentions prior escalations.

**30. Cross-session persistence check**
Customer ID: `mem-cross-session` (reuse the ID from an earlier scenario, e.g. `mem-plan-tier`)
- Turn 1: Click **Reset conversation** in the sidebar (this clears the chat *window*, not Mem0).
- Turn 2: Without changing the Customer ID, ask any question, e.g. "What payment methods do you accept?"
- *Check: the sidebar's Customer context repopulates with the plan tier / prior data from the earlier scenario as soon as this new question resolves — proving memory is keyed by customer_id in Mem0, not by the browser's chat session.*
