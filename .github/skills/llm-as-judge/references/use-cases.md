# Practical Use Cases

Real-world scenarios for using agent-native LLM-as-Judge evaluation through Copilot/Claude. All evaluation happens within the agent context—no external APIs or scripts.

---

## Use Case 1 — RAG Quality Assurance

**Scenario:** A support bot uses RAG (retrieval-augmented generation) to answer customer questions. You want to verify responses are grounded in retrieved facts and not hallucinating.

**Conversation:**

```
You: "Evaluate this RAG response for hallucinations.

Customer Query: What are the warranty terms?

Retrieved Context (from company docs):
'Warranty covers manufacturer defects for 1 year from purchase date. 
Labor not included. Accidental damage excluded.'

Bot Response:
'We provide a 1-year warranty covering manufacturer defects. 
You'll need to pay for labor. Accidental damage is covered under premium plans.'

Check if the response accurately uses the context or adds unsupported claims."

Agent:
Grounded claims:
- 1-year warranty ✓
- Covers manufacturer defects ✓
- Labor costs ✓

Hallucinated/Unsupported:
- "Premium plans" - NOT in context
- "Accidental damage is covered under premium plans" - Context says accidental damage is EXCLUDED

Issues found: 2
Verdict: FAIL - Contains hallucinated information about premium plans
```

**Result:** You immediately know this response shouldn't be sent to customers without fact-checking.

---

## Use Case 2 — Code Generation Quality Check

**Scenario:** You're choosing between two code generation models and want to know which produces better code.

**Conversation:**

```
You: "Compare these two Python functions solving the same problem.

Task: Find the median of two sorted arrays

Option A (from Sonnet 4.5):
def findMedian(nums1, nums2):
    merged = sorted(nums1 + nums2)
    n = len(merged)
    return (merged[n//2] + merged[(n-1)//2]) / 2

Option B (from Grok-3):
def findMedian(nums1, nums2):
    # Two-pointer merge approach (O(m+n))
    a, b = 0, 0
    merged = []
    while a < len(nums1) and b < len(nums2):
        if nums1[a] < nums2[b]:
            merged.append(nums1[a])
            a += 1
        else:
            merged.append(nums2[b])
            b += 1
    merged.extend(nums1[a:] or nums2[b:])
    n = len(merged)
    return (merged[n//2] + merged[(n-1)//2]) / 2

Rate on: Correctness, Readability, Efficiency, Best Practices (1-5 each)"

Agent:
Option A:
- Correctness: 5/5 - Works correctly
- Readability: 5/5 - Simple and clear
- Efficiency: 2/5 - O(n log n) sorting, inefficient
- Best Practices: 4/5 - Clean but not optimal
Average: 4.0/5

Option B:
- Correctness: 5/5 - Works correctly
- Readability: 3/5 - More complex logic
- Efficiency: 5/5 - O(m+n) two-pointer approach
- Best Practices: 5/5 - Industry standard algorithm
Average: 4.5/5

Winner: Option B by a small margin

Recommendation: Use Grok-3 for production efficiency, but Sonnet for quick prototypes where simplicity matters.
```

---

## Use Case 3 — Evaluate Multiple Response Candidates

**Scenario:** A system generates job descriptions, and you want to rate each one on quality before posting.

**Conversation:**

```
You: "Score this job description 1-5 on each dimension:

Job Description: [full job posting]

Evaluate:
1. Clarity - Is it clear what the role entails?
2. Completeness - Does it include all necessary info?
3. Tone - Is it engaging and professional?
4. Accuracy - Is technical info accurate?
5. Fairness - No discriminatory language?"

Agent:
- Clarity: 4/5 - Generally clear, some jargon could be explained
- Completeness: 3/5 - Missing salary range and team size info
- Tone: 5/5 - Engaging and friendly
- Accuracy: 5/5 - Technical requirements are correct
- Fairness: 5/5 - Inclusive language throughout

Average: 4.4/5 - GOOD

Recommendations for improvement:
1. Add salary range for transparency
2. Clarify "must have 5+ years" vs "nice to have"
3. Add team size/reporting structure
```

---

## Use Case 4 — Customer Response Quality Gate

**Scenario:** A customer support bot generates responses before they're sent. You want to verify they meet quality standards.

**Conversation:**

```
You: "Before we send this to a customer, check if it meets our quality standards.

Customer Question: How do I reset my password?

Bot Response: 'You can reset your password by clicking on the login page. Then click forgot password and follow the steps.'

Standards Check:
1. Relevance - Answers the question
2. Clarity - Easy to understand
3. Helpfulness - Gives enough detail
4. Tone - Professional and friendly
5. Safety - No security issues"

Agent:
- Relevance: 5/5 - Directly answers
- Clarity: 5/5 - Step-by-step
- Helpfulness: 4/5 - Could mention email link requirement
- Tone: 5/5 - Friendly, professional
- Safety: 5/5 - No security concerns

Average: 4.8/5

Verdict: APPROVED
Send to customer without modification.
```

---

## Use Case 5 — Instruction Compliance Check

**Scenario:** A system generates SQL queries to spec. You need to verify they follow requirements.

**Conversation:**

```
You: "Did this SQL query follow the requirements?

Requirements:
- Return only customers from 'Premium' tier
- Sort by signup date (newest first)
- Include: name, email, company
- No more than 10 rows
- Use READONLY role for security

Generated Query:
SELECT name, email, company FROM customers 
WHERE tier = 'Premium' 
ORDER BY signup_date DESC 
LIMIT 10;

Evaluate compliance."

Agent:
Requirement Compliance:
✓ Premium tier only
✓ Sorted by date newest first
✓ Right columns included
✓ LIMIT 10
~ READONLY role: Not specified in query metadata

Issues: 1
- Missing READONLY role enforcement

Verdict: PARTIAL
Fix: Add role specification in query execution context.
```

---

## Tips for Effective Agent-Native Evaluation

1. **Be specific with criteria** — Define exactly what you're evaluating
2. **Provide context** — The more background, the better the evaluation
3. **Use clear scales** — Define what 1-5 means (don't assume)
4. **Ask for reasoning** — Always request "why" not just scores
5. **Be consistent** — Ask the same way for similar evaluations
6. **Provide examples** — Show good vs bad examples for calibration
7. **Iterate** — Refine criteria based on results

---

## Quick Reference: Common Evaluation Templates

| Task | Template |
|------|----------|
| Compare responses | "Which is better? A: ... B: ... Evaluate on [criteria]" |
| Score quality | "Rate 1-5 on [dimensions]" |
| Check hallucinations | "Verify against context: [context]. Response: [response]. Identify unsupported claims." |
| Code review | "Review this code for [criteria]" |
| Fact check | "Is this accurate? Check: [claim]. Facts: [known facts]" |



