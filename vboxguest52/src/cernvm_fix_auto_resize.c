#include <assert.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/select.h>
#include <unistd.h>

#include <libudev.h>


int main() {
  struct udev *udev;
  struct udev_device *dev;
  struct udev_monitor *mon;
  int fd_udev;

  udev = udev_new();
  assert(udev);  
  mon = udev_monitor_new_from_netlink(udev, "udev");
  assert(mon);
  udev_monitor_filter_add_match_subsystem_devtype(mon, "drm", "drm_minor");
  udev_monitor_enable_receiving(mon);
  fd_udev = udev_monitor_get_fd(mon);
  assert(fd_udev >= 0);

  daemon(0, 0);
  system("/usr/bin/xrandr --auto");

  while (1) {
    fd_set fds;

    FD_ZERO(&fds);
    FD_SET(fd_udev, &fds);

    int retval = select(fd_udev + 1, &fds, NULL, NULL, NULL);
    if (retval > 0 && FD_ISSET(fd_udev, &fds)) {
      dev = udev_monitor_receive_device(mon);
      sleep(1);
      if (dev) {
        printf("I: ACTION=%s\n", udev_device_get_action(dev));
        printf("I: DEVNAME=%s\n", udev_device_get_sysname(dev));
        printf("I: DEVPATH=%s\n", udev_device_get_devpath(dev));
        printf("---\n");

        udev_device_unref(dev);
        system("/usr/bin/xrandr");
      }
    }
  }
  
  udev_unref(udev);

  return 0;
}

