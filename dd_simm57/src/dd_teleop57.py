#!/usr/bin/python3
from __future__ import print_function
import threading
import roslib; roslib.load_manifest('teleop_twist_keyboard')
import rospy
from geometry_msgs.msg import Twist
import sys, select, termios, tty

msg = """
------------------------------------------------
            -= KEYBINDINGS =-
        W           --      Move Forward
        A           --      Turn Left
        S           --      Move Backward
        D           --      Turn Right
        ANY         --      Hold
        Ctrl+C      --      Stop Control
------------------------------------------------
"""

keybindings = {
        'w':(1,0),
        's':(-1,0),
        'a':(0,-1),
        'd':(0,1),
        'W':(1,0),
        'S':(-1,0),
        'A':(0,-1),
        'D':(0,1),
}

class PublishThread(threading.Thread):
    def __init__(self, rate):
        super(PublishThread, self).__init__()
        self.publisher = rospy.Publisher('cmd_vel', Twist, queue_size = 1)
        self.x = 0.0
        self.th = 0.0
        self.condition = threading.Condition()
        self.done = False
        if rate != 0.0:
            self.timeout = 1.0 / rate
        else:
            self.timeout = None
        self.start()
        
    def wait_for_subscribers(self):
        i = 0
        while not rospy.is_shutdown() and self.publisher.get_num_connections() == 0:
            if i == 2:
                print("Waiting for subscriber to connect to {}".format(self.publisher.name))
            rospy.sleep(0.5)
            i += 1
            i = i % 3
        if rospy.is_shutdown():
            raise Exception("Got shutdown request before subscribers connected")

    def update(self, x, th):
        self.condition.acquire()
        self.x = x
        self.th = th
        self.condition.notify()
        self.condition.release()

    def stop(self):
        self.done = True
        self.update(0, 0)
        self.join()

    def run(self):
        twist = Twist()
        while not self.done:
            self.condition.acquire()
            self.condition.wait(self.timeout)
            twist.linear.x = self.x * 0.5
            twist.angular.z = self.th * 2
            self.condition.release()
            self.publisher.publish(twist)
        twist.linear.x = 0
        twist.angular.z = 0
        self.publisher.publish(twist)

def getKey(key_timeout):
    tty.setraw(sys.stdin.fileno())
    rlist, _, _ = select.select([sys.stdin], [], [], key_timeout)
    if rlist:
        key = sys.stdin.read(1)
    else:
        key = ''
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key

if __name__=="__main__":
    settings = termios.tcgetattr(sys.stdin)
    rospy.init_node('teleop_twist_keyboard')
    repeat = rospy.get_param("~repeat_rate", 0.0)
    key_timeout = rospy.get_param("~key_timeout", 0.0)
    if key_timeout == 0.0:
        key_timeout = None
    pub_thread = PublishThread(repeat)
    x = 0
    th = 0
    status = 0
    try:
        pub_thread.wait_for_subscribers()
        pub_thread.update(x, th)
        print(msg)
        while(1):
            key = getKey(key_timeout)
            if key in keybindings.keys():
                x = keybindings[key][0]
                th = keybindings[key][1]
            else:
                if key == '' and x == 0 and th == 0:
                    continue
                x = 0
                th = 0
                if (key == '\x03'):
                    break
            pub_thread.update(x, th)
    except Exception as e:
        print(e)
    finally:
        pub_thread.stop()
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)