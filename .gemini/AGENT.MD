# Agent environment rules

## Shell and OS

- OS: Windows
- Shell: PowerShell
- NEVER use `&&` to chain commands — PowerShell does not support it
- Run commands on separate lines, or use `;` as the separator
- NEVER assume bash, Linux, or Mac unless told otherwise
- Use `python` not `python3`
- Use backslash `\` for file paths, not forward slash
- Do not use Unix-only commands like `grep`, `cat`, `touch`, `ls` — use PowerShell equivalents (`Select-String`, `Get-Content`, `New-Item`, `Get-ChildItem`)

## Django / Python

- Always `cd` to the backend directory first, then run manage.py on a separate line
- Example:
  ```
  cd backend
  python manage.py shell -c "..."
  ```
- Never combine into one line with `&&`

## Self-learning rule

- When a command fails due to a shell or environment mismatch, output the corrected command immediately AND add a note at the end of your response in this format:
  ```
  [RULE LEARNED] <short description of the rule that prevented this error>
  ```
- This allows the developer to copy new rules back into this file manually

## General

- Always confirm before running destructive commands (`del`, `rmdir`, `DROP`, etc.)
- When in doubt about the environment, ask before generating terminal commands