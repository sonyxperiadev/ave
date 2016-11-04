#! /bin/bash

# just a minimal example of an example job. the list of environment variables
# will be almost empty ($PWD, $SHLVL and $_ will be set on Debian, but nothing
# else, unless the user explicitly tells `vcsjob exec` to consume a list of
# environment variables). the for loop will print the names of all files in the
# jobs directory.

printenv
echo `which python`

for f in *; do
	echo $f
	sleep 0.05
done

