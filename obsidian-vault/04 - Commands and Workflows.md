# Commands and Workflows

Examples of intended commands (not all implemented yet):
- JARVIS, add a task to call the bank tomorrow.
- Summarize my open tasks.
- Find the note where I documented the car.
- Draft an email to the supplier, but do not send it.
- Read my calendar for tomorrow.
- Create a calendar event after I approve the details.

## Command lifecycle
1. Capture command.
2. Resolve intent and required context.
3. Explain planned action and parameters.
4. Check permission policy.
5. Request approval when required.
6. Execute once.
7. Verify result and write audit record.
