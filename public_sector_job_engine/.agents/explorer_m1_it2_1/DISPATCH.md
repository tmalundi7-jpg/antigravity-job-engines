## 2026-09-03T02:25:00Z
You are Explorer M1-Iteration 2-1 for Milestone 1 remediation.
Your working directory is: C:\Users\tmalu\.gemini\antigravity\scratch\job_search_engine\.agents\explorer_m1_it2_1
Read ORIGINAL_REQUEST.md at: C:\Users\tmalu\.gemini\antigravity\scratch\job_search_engine\ORIGINAL_REQUEST.md
Read PROJECT.md at: C:\Users\tmalu\.gemini\antigravity\scratch\job_search_engine\.agents\orchestrator_1\PROJECT.md
Read Challenger M1-2 handoff report at: C:\Users\tmalu\.gemini\antigravity\scratch\job_search_engine\.agents\challenger_m1_2\handoff.md

Your focus: Consumer Lifecycle Management in `core/messaging.py` and `agents/base.py`.
1. Analyze the root cause of competing zombie consumers in `LocalMessageBroker`:
   - Singleton broker accumulates background worker threads for every `consume()` call.
   - When tests or agents re-initialize, older worker threads continue polling queues and swallow messages.
2. Design the exact methods for `LocalMessageBroker`:
   - `clear_consumers(queue_name=None)`
   - `unsubscribe(queue_name, callback)`
   - `reset()` (clears all queues, stops existing consumer threads, resets thread pools)
3. Design `BaseAgent.stop()` method that stops its consumer thread cleanly.
4. Detail line-by-line diffs and provide exact implementation recommendations.
5. Write your findings to C:\Users\tmalu\.gemini\antigravity\scratch\job_search_engine\.agents\explorer_m1_it2_1\remediation_plan.md and handoff.md. Maintain progress.md. Send a message to your parent when done.
