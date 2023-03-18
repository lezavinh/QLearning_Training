#!/usr/bin/env python2
#################################################################################
# Copyright 2018 ROBOTIS CO., LTD.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#################################################################################

# Authors: Za Vinh Le

import rospy
import numpy as np
import math
from math import pi
from geometry_msgs.msg import Twist, Point, Pose
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry
from std_srvs.srv import Empty
from tf.transformations import euler_from_quaternion, quaternion_from_euler
from respawnGoal import Respawn

# New import
from std_msgs.msg import String
from itertools import product
# New import

# New define
STATE_SPACE_IND_MAX = 144 - 1
STATE_SPACE_IND_MIN = 1 - 1
ACTIONS_IND_MAX = 2
ACTIONS_IND_MIN = 0

ANGLE_MAX = 360 - 1
ANGLE_MIN = 1 - 1
HORIZON_WIDTH = 75

T_MIN = 0.001
#New define

class Env():
    def __init__(self, action_size):
        self.goal_x = 0
        self.goal_y = 0
        self.heading = 0
        self.action_size = action_size
        self.initGoal = True
        self.get_goalbox = False
        self.position = Pose()
        self.pub_cmd_vel = rospy.Publisher('cmd_vel', Twist, queue_size=5)
        self.sub_odom = rospy.Subscriber('odom', Odometry, self.getOdometry)
        self.reset_proxy = rospy.ServiceProxy('gazebo/reset_simulation', Empty)
        self.unpause_proxy = rospy.ServiceProxy('gazebo/unpause_physics', Empty)
        self.pause_proxy = rospy.ServiceProxy('gazebo/pause_physics', Empty)
        self.respawn_goal = Respawn()

    def getGoalDistace(self):
        goal_distance = round(math.hypot(self.goal_x - self.position.x, self.goal_y - self.position.y), 2)

        return goal_distance

    def getOdometry(self, odom):
        self.position = odom.pose.pose.position
        orientation = odom.pose.pose.orientation
        orientation_list = [orientation.x, orientation.y, orientation.z, orientation.w]
        _, _, yaw = euler_from_quaternion(orientation_list)

        goal_angle = math.atan2(self.goal_y - self.position.y, self.goal_x - self.position.x)

        heading = goal_angle - yaw
        if heading > pi:
            heading -= 2 * pi

        elif heading < -pi:
            heading += 2 * pi

        self.heading = round(heading, 2)

    ''' get state
    def getState(self, scan):
        scan_range = []
        heading = self.heading
        min_range = 0.13
        done = False

        for i in range(len(scan.ranges)):
            if scan.ranges[i] == float('Inf'):
                scan_range.append(3.5)
            elif np.isnan(scan.ranges[i]):
                scan_range.append(0)
            else:
                scan_range.append(scan.ranges[i])

        obstacle_min_range = round(min(scan_range), 2)
        obstacle_angle = np.argmin(scan_range)
        if min_range > min(scan_range) > 0:
            done = True

        current_distance = round(math.hypot(self.goal_x - self.position.x, self.goal_y - self.position.y),2)
        if current_distance < 0.2:
            self.get_goalbox = True

        return scan_range + [heading, current_distance, obstacle_min_range, obstacle_angle], done
    '''
    def setReward_to_goal(self, action):
        yaw_reward = []
        #obstacle_min_range = state[-2]
        #current_distance = state[-3]
        current_distance = round(math.hypot(self.goal_x - self.position.x, self.goal_y - self.position.y),2)
        if current_distance < 0.2:
            self.get_goalbox = True
        heading = self.heading

        for i in range(3):
            angle = -pi / 4 + heading + (pi / 8 * i) + pi / 2
            tr = 1 - 4 * math.fabs(0.5 - math.modf(0.25 + 0.5 * angle % (2 * math.pi) / math.pi)[0])
            yaw_reward.append(tr)

        distance_rate = 2 ** (current_distance / self.goal_distance)

        reward = ((round(yaw_reward[action] * 5, 2)) * distance_rate)
        '''
        if done:
            rospy.loginfo("Collision!!")
            reward = -500
            self.pub_cmd_vel.publish(Twist())
        '''
        if self.get_goalbox:
            rospy.loginfo("Goal!!")
            reward = 1000
            self.pub_cmd_vel.publish(Twist())
            self.goal_x, self.goal_y = self.respawn_goal.getPosition(True, delete=True)
            self.goal_distance = self.getGoalDistace()
            self.get_goalbox = False

        return reward

    ''' #step
    def step(self, action):
        max_angular_vel = 1.5
        ang_vel = ((self.action_size - 1)/2 - action) * max_angular_vel * 0.5

        vel_cmd = Twist()
        vel_cmd.linear.x = 0.15
        vel_cmd.angular.z = ang_vel
        self.pub_cmd_vel.publish(vel_cmd)

        data = None
        while data is None:
            try:
                data = rospy.wait_for_message('scan', LaserScan, timeout=5)
            except:
                pass

        state, done = self.getState(data)
        reward = self.setReward(state, done, action)

        return np.asarray(state), reward, done
    '''
    def reset(self):
        rospy.wait_for_service('gazebo/reset_simulation')
        try:
            self.reset_proxy()
        except (rospy.ServiceException) as e:
            print("gazebo/reset_simulation service call failed")

        data = None
        while data is None:
            try:
                data = rospy.wait_for_message('scan', LaserScan, timeout=5)
            except:
                pass

        if self.initGoal:
            self.goal_x, self.goal_y = self.respawn_goal.getPosition()
            self.initGoal = False

        self.goal_distance = self.getGoalDistace()
        state, done = self.getState(data)

        return np.asarray(state)
    #New_function
    def createActions(self):
        actions = np.array([0,1,2])
        return actions    
    def createStateSpace(self):
        x1 = set((0,1,2))
        x2 = set((0,1,2))
        x3 = set((0,1,2,3))
        x4 = set((0,1,2,3))
        state_space = set(product(x1,x2,x3,x4))
        return np.array(list(state_space))
    def createQTable(self, n_states, n_actions):
        #Q_table = np.random.uniform(low = -0.05, high = 0, size = (n_states,n_actions) )
        Q_table = np.zeros((n_states, n_actions))
        return Q_table        
    # Read Q table from path
    def readQTable(self, path):
        Q_table = np.genfromtxt(path, delimiter = ' , ')
        return Q_table

    # Write Q table to path
    def saveQTable(self, path, Q_table):
        np.savetxt(path, Q_table, delimiter = ' , ')
    def getBestAction(self, Q_table, state_ind, actions):
        if STATE_SPACE_IND_MIN <= state_ind <= STATE_SPACE_IND_MAX:
            status = 'getBestAction => OK'
            a_ind = np.argmax(Q_table[state_ind,:])
            a = actions[a_ind]
        else:
            status = 'getBestAction => INVALID STATE INDEX'
            a = self.getRandomAction(actions)

        return ( a, status )
    # Select random action from actions
    def getRandomAction(self, actions):
        n_actions = len(actions)
        a_ind = np.random.randint(n_actions)
        return actions[a_ind]
    def epsiloGreedyExploration(self, Q_table, state_ind, actions, epsilon):
        if np.random.uniform() > epsilon and STATE_SPACE_IND_MIN <= state_ind <= STATE_SPACE_IND_MAX:
            status = 'epsiloGreedyExploration => OK'
            ( a, status_gba ) = self.getBestAction(Q_table, state_ind, actions)
            if status_gba == 'getBestAction => INVALID STATE INDEX':
                status = 'epsiloGreedyExploration => INVALID STATE INDEX'
        else:
            status = 'epsiloGreedyExploration => OK'
            a = self.getRandomAction(actions)

        return ( a, status )
    def softMaxSelection(self, Q_table, state_ind, actions, T):
        if STATE_SPACE_IND_MIN <= state_ind <= STATE_SPACE_IND_MAX:
            status = 'softMaxSelection => OK'
            n_actions = len(actions)
            P = np.zeros(n_actions)

            # Boltzman distribution
            P = np.exp(Q_table[state_ind,:] / T) / np.sum(np.exp(Q_table[state_ind,:] / T))

            if T < T_MIN or np.any(np.isnan(P)):
                ( a, status_gba ) = self.getBestAction(Q_table, state_ind, actions)
                if status_gba == 'getBestAction => INVALID STATE INDEX':
                    status = 'softMaxSelection => INVALID STATE INDEX'
            else:
                rnd = np.random.uniform()
                status = 'softMaxSelection => OK'
                if P[0] > rnd:
                    a = 0
                elif P[0] <= rnd and (P[0] + P[1]) > rnd:
                    a = 1
                elif (P[0] + P[1]) <= rnd:
                    a = 2
                else:
                    status = 'softMaxSelection => Boltzman distribution error => getBestAction '
                    status = status + '\r\nP = (%f , %f , %f) , rnd = %f' % (P[0],P[1],P[2],rnd)
                    status = status + '\r\nQ(%d,:) = ( %f, %f, %f) ' % (state_ind,Q_table[state_ind,0],Q_table[state_ind,1],Q_table[state_ind,2])
                    ( a, status_gba ) = self.getBestAction(Q_table, state_ind, actions)
                    if status_gba == 'getBestAction => INVALID STATE INDEX':
                        status = 'softMaxSelection => INVALID STATE INDEX'
        else:
            status = 'softMaxSelection => INVALID STATE INDEX'
            a = self.getRandomAction(actions)

        return ( a, status )   
    def getReward(self, action, prev_action, lidar, prev_lidar, crash):
        if crash:
            terminal_state = True
            reward = -100
        else:
            lidar_horizon = np.concatenate((lidar[(ANGLE_MIN + HORIZON_WIDTH):(ANGLE_MIN):-1],lidar[(ANGLE_MAX):(ANGLE_MAX - HORIZON_WIDTH):-1]))
            prev_lidar_horizon = np.concatenate((prev_lidar[(ANGLE_MIN + HORIZON_WIDTH):(ANGLE_MIN):-1],prev_lidar[(ANGLE_MAX):(ANGLE_MAX - HORIZON_WIDTH):-1]))
            terminal_state = False
            # Reward from action taken = fowrad -> +0.2 , turn -> -0.1
            if action == 0:
                r_action = +0.2
            else:
                r_action = -0.1
            # Reward from crash distance to obstacle change
            W = np.linspace(0.9, 1.1, len(lidar_horizon) // 2)
            W = np.append(W, np.linspace(1.1, 0.9, len(lidar_horizon) // 2))
            if np.sum( W * ( lidar_horizon - prev_lidar_horizon) ) >= 0:
                r_obstacle = +0.2
            else:
                r_obstacle = -0.2
            # Reward from turn left/right change
            if ( prev_action == 1 and action == 2 ) or ( prev_action == 2 and action == 1 ):
                r_change = -0.8
            else:
                r_change = 0.0
        
            # Cumulative reward
            reward = r_action + r_obstacle + r_change + self.setReward_to_goal

        return ( reward, terminal_state )   
    def updateQTable(self, Q_table, state_ind, action, reward, next_state_ind, alpha, gamma):
        if STATE_SPACE_IND_MIN <= state_ind <= STATE_SPACE_IND_MAX and STATE_SPACE_IND_MIN <= next_state_ind <= STATE_SPACE_IND_MAX:
            status = 'updateQTable => OK'
            Q_table[state_ind,action] = ( 1 - alpha ) * Q_table[state_ind,action] + alpha * ( reward + gamma * max(Q_table[next_state_ind,:]) )
        else:
            status = 'updateQTable => INVALID STATE INDEX'
        return ( Q_table, status )      
