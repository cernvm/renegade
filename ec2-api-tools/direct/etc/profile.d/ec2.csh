# The script should be sourced by /bin/csh or similar
if ( ! $?EC2_HOME ) then
  setenv EC2_HOME "//usr/lib/ec2"
  setenv JAVA_HOME "//usr"
  setenv PATH "/usr/lib/ec2/bin:$PATH"
endif
