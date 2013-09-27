# The script should be sourced by /bin/sh or similar
if [ x"$EC2_HOME" = x ]
then 
  export EC2_HOME="/usr/lib/ec2"
  export JAVA_HOME="/usr"
  export PATH="/usr/lib/ec2/bin:$PATH"
fi

