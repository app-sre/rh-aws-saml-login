Output quickstart.gif

Set FontSize 20
Set Width 1600
Set Height 600

Type "# Let's run rh-aws-saml-login in interactive mode"
Sleep 1s
Enter

Type "rh-aws-saml-login"
Sleep 1s
Enter
Sleep 3s
Type@500ms account-2
Sleep 3s
Enter
Sleep 5s

Type "# A new shell has been spawned with several 'AWS_...' env vars set"
Sleep 5s
Enter

Type "env | grep 'AWS_'"
Sleep 1s
Enter
Sleep 5s

Type "# Now you can run the aws cli, e.g., 'aws s3 ls' to list the buckets"
Sleep 1s
Enter
Sleep 5s

Type "# After you're done, type 'exit' or Ctrl+D to close the shell"
Enter
Ctrl+D
Sleep 5s
Enter


# End
Sleep 10s
