import glob
import os
import sys
try:
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass
import carla

import random
import time
import numpy as np
import math
import csv

VEH_NUM = 5
actor_list = []

def destroy():
    for actor in actor_list:
        actor.destroy()


try:
    # 0. Set the cilent and the world
    client = carla.Client('localhost', 2000) # https://carla.readthedocs.io/en/latest/core_world/#client-creation
    client.set_timeout(5.0)

    world = client.get_world()

    # 1. Choose blueprint
    blueprint_library = world.get_blueprint_library() # https://carla.readthedocs.io/en/latest/core_actors/#blueprints
    vehicle_bp = random.choice(blueprint_library.filter('vehicle.*.*'))

    # 2. Choose spawn point
    spawn_points = world.get_map().get_spawn_points()

    # 3. Spawn the vehicles
    for i in range(VEH_NUM):

        # Choose random blueprint and choose the i-th default spawn points
        vehicle_bp_i = random.choice(blueprint_library.filter('vehicle.*.*'))
        spawn_point_i = spawn_points[i]

        # Spawn the actor
        vehicle_i = world.spawn_actor(vehicle_bp_i, spawn_point_i)

        # Set control mode for v_i. https://carla.readthedocs.io/en/latest/python_api/#carla.Vehicle
        vehicle_i.set_autopilot(True)

        # Append to the actor_list
        actor_list.append(vehicle_i)

    # 4. Print the realtime information of the agents
    world_snapshot = world.get_snapshot()
    start_t = world_snapshot.timestamp.elapsed_seconds
    cur_t = start_t

    with open('actor_info.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Frame', 'Timestamp', 'Vehicle_ID', 'Location_X', 'Location_Y', 'Velocity_X', 'Velocity_Y', 'Acceleration_X', 'Acceleration_Y'])
        while cur_t - start_t < 10:
            # Retrieve a snapshot of the world at current frame.
            world_snapshot = world.get_snapshot()
            frame = world_snapshot.frame
            timestamp = world_snapshot.timestamp.elapsed_seconds # Get the time reference

            INFO = ''
            global_status = 'Frame:{%s}, Timestamp:{%.3f s}. \n' %(frame, timestamp)
            INFO += global_status
            csv_line = ''
            for i in range(len(actor_list)):
                actor_i = actor_list[i]
                loc = actor_i.get_location()
                vel = actor_i.get_velocity()
                acc = actor_i.get_acceleration()

                actor_i_status = 'Vehicle_ID:{%s}, Location_X:{%.3f}, Location_Y:{%.3f}, Velocity_X:{%.3f}, Velocity_Y:{%.3f}, Acceleration_X:{%.3f}, Acceleration_Y:{%.3f}.' %(i, loc.x, loc.y, vel.x, vel.y, acc.x, acc.y)
                actor_csv = '%s, %.3f, %s, %.3f, %.3f, %.3f, %.3f, %.3f, %.3f' %(frame, timestamp, i, loc.x, loc.y, vel.x, vel.y, acc.x, acc.y)
                csv_line += actor_csv + "\n"
                INFO += actor_i_status

            # Set the print interval
            if round(abs(timestamp - cur_t), 1) == 0.1:
                print('-------------------------------------------------------------------------------')
                print(INFO)
                print('-------------------------------------------------------------------------------\n')
                cur_t = timestamp
                csvfile.write(csv_line)

    time.sleep(30)


#except:
    #destroy()


finally:
    print('destroying actors')
    destroy()
    print('done.')