# VHS tape — prompt injection → DENY
# Generate: vhs demos/assets/tapes/injection.tape
Output demos/assets/injection.gif

Set FontSize 14
Set Width 80
Set Height 18
Set Theme "Dracula"
Set Padding 12

Sleep 500ms
Type "python -m demos.core.prompt_injection"
Sleep 300ms
Enter
Sleep 2s
