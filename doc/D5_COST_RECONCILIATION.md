# D5 cost reconciliation

## Account-level check

- OpenRouter key usage before D5 live work: **$0.271794400**
- OpenRouter key usage after all D5 live work: **$0.925763392**
- Account-level D5 increment: **$0.653968992**
- User-approved ceiling: **$2.00**
- Amount below ceiling: **$1.346031008**

## Formal batteries recorded locally

| Battery | Recorded cost (USD) | Note |
|---|---:|---|
| GPT-4o-mini V2 | 0.062400150 | 52/52 usage records measured |
| Qwen 3 30B V2 | 0.076210290 | 52/52 usage records measured |
| Mistral Small 3.2 V2 | 0.101458950 | Includes one provider-error response costing $0.000318450; 52 completed trials cost $0.101140500 |
| Llama 3.3 70B V2 | 0.144273400 | 51/52 usage records measured; one invalid response had no measurable usage |
| Gemini 2.5 Flash V2 | 0.181175300 | 52/52 usage records measured |
| Qwen 3 30B V1 | 0.069688780 | 52/52 usage records measured |
| **Formal local total** | **0.635206870** | 312 completed formal trials, plus the recorded Mistral provider error |

The difference between the account increment and the formal local total is **$0.018762122**. It covers the abandoned five-call Claude Haiku compatibility precheck, the Llama response whose provider usage was not returned, and other small precheck/unattributed provider charges. Therefore:

- use **$0.653968992** when reporting the total amount actually added to the OpenRouter account during D5;
- use each battery's recorded cost for per-model efficiency comparisons;
- do not present the Llama local total as an exact fully measured bill.

The API key is not stored in this package.
