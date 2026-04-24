# VHS tape — prompt injection → DENY
# Generate: vhs docs/demo/injection.tape
Output docs/demo/injection.gif

Set FontSize 14
Set Width 80
Set Height 18
Set Theme "Dracula"
Set Padding 12

Sleep 500ms
Type "python -m safe_mcp_proxy.examples.prompt_injection"
Sleep 300ms
Enter
Sleep 2s
